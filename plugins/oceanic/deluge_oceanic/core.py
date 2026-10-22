from __future__ import annotations

import contextlib
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, ClassVar

from twisted.internet.utils import getProcessOutputAndValue

import deluge.component as component
from deluge.config import Config
from deluge.configmanager import ConfigManager
from deluge.plugins.pluginbase import CorePluginBase


@dataclass(frozen=True)
class Hearing:
    """
    One row of what the plugin hears: a libtorrent alert, whose handler gets the alert, or a Deluge event, whose
    handler gets the event's arguments, a torrent id first.
    """

    class Kind(Enum):
        ALERT = 'alert'
        EVENT = 'event'

    kind: Hearing.Kind
    source: str
    handler: Callable[..., None]

    def register(self) -> None:
        if self.kind is Hearing.Kind.ALERT:
            component.get('AlertManager').register_handler(self.source, self.handler)
        else:
            component.get('EventManager').register_event_handler(self.source, self.handler)

    def deregister(self) -> None:
        if self.kind is Hearing.Kind.ALERT:
            component.get('AlertManager').deregister_handler(self.handler)
        else:
            component.get('EventManager').deregister_event_handler(self.source, self.handler)


class Core(CorePluginBase):
    """
    Hears libtorrent's removed, deleted and delete-failed alerts, which Deluge's alert manager receives and
    nothing in Deluge handles, writes every one to its own log, and spawns the one configured command for every
    one, the event named after the alert; all policy lives in the hook the command reaches. An alert handler
    has two seconds before the alert manager gives up on it, so nothing here blocks, sleeps or waits: the command
    is spawned and its end is a callback. Deluge's own log is not read on this box, so no handler raises: a
    failure is one line in the plugin's log.
    """

    plugin_version: ClassVar[str] = '0.1'
    DEFAULT_CONFIG: ClassVar[dict[str, Any]] = {
        'command': '/codes/oceanic_plugin/oceanic.sh',
        'events': ['removed', 'deleted', 'delete_failed'],
        'log_file': '/deluge/log/oceanic.log',
    }
    logger: ClassVar[logging.Logger] = logging.getLogger(__name__)
    # a DelugApi prints its password when it is built; the responder's output is filtered as every shell here does
    password_line: ClassVar[re.Pattern[str]] = re.compile(r'^(DelugApi [^,]*,[^,]*,[^,]*),.*$', re.MULTILINE)

    # set by enable, before any handler is registered
    config: Config
    preremoved_cache: dict[str, list[str]]

    @property
    def hearings(self) -> tuple[Hearing, ...]:
        return (
            Hearing(Hearing.Kind.EVENT, 'PreTorrentRemovedEvent', self.on_preremoved),
            Hearing(Hearing.Kind.ALERT, 'torrent_deleted', self.on_torrent_deleted),
            Hearing(Hearing.Kind.ALERT, 'torrent_delete_failed', self.on_torrent_delete_failed),
            Hearing(Hearing.Kind.ALERT, 'torrent_removed', self.on_torrent_removed),
        )

    def enable(self) -> None:
        self.config = ConfigManager('oceanic.conf', self.DEFAULT_CONFIG)
        self.preremoved_cache = {}
        for hearing in self.hearings:
            hearing.register()
        self.log_line(f"enabled Oceanic {self.plugin_version}, command {self.config['command']}, "
                      f"events {self.config['events']}, log {self.config['log_file']}")

    def disable(self) -> None:
        self.config.save()
        for hearing in self.hearings:
            hearing.deregister()
        self.log_line('disabled')

    # --- the handlers

    def on_preremoved(self, torrent_id: str) -> None:
        # the alerts come after the torrent has left the session, so its name and location are kept before
        try:
            torrent = component.get('TorrentManager').torrents[torrent_id]
            status = torrent.get_status(['name', 'download_location'])
            self.preremoved_cache[torrent_id] = [torrent_id, status['name'], status['download_location']]
        except Exception as exc:
            self.log_failure('on_preremoved', exc)

    def on_torrent_deleted(self, alert: Any) -> None:
        try:
            torrent_id = str(alert.info_hash)
            self.log_line(f"{alert.what()} id {torrent_id} name '{alert.torrent_name}'")
            self.run_command('deleted', torrent_id)
        except Exception as exc:
            self.log_failure('on_torrent_deleted', exc)

    def on_torrent_delete_failed(self, alert: Any) -> None:
        try:
            torrent_id = str(alert.info_hash)
            error = alert.error.message()
            self.log_line(f"{alert.what()} id {torrent_id} name '{alert.torrent_name}' "
                          f"error '{error}' ({alert.error.value()})")
            self.run_command('delete_failed', torrent_id, error)
        except Exception as exc:
            self.log_failure('on_torrent_delete_failed', exc)

    def on_torrent_removed(self, alert: Any) -> None:
        try:
            torrent_id = str(alert.info_hash)
            self.log_line(f"{alert.what()} id {torrent_id} name '{alert.torrent_name}'")
            try:
                self.run_command('removed', torrent_id)
            finally:
                # the removed alert is its torrent's last, so its cache entry goes with it
                if self.preremoved_cache.pop(torrent_id, None) is not None:
                    self.log_line(f'popped {torrent_id} from the cache, {len(self.preremoved_cache)} left')
        except Exception as exc:
            self.log_failure('on_torrent_removed', exc)

    # --- the command

    def run_command(self, event: str, torrent_id: str, detail: str | None = None) -> None:
        if event not in self.config['events']:
            self.log_line(f'{event} not in events, nothing run')
            return
        cached = self.preremoved_cache.get(torrent_id)
        if cached is None:
            self.log_line(f'no cached location for {torrent_id}, nothing run')
            return
        _, torrent_name, download_location = cached
        command = os.path.expanduser(os.path.expandvars(self.config['command']))
        if not (os.path.isfile(command) and os.access(command, os.X_OK)):
            self.log_line(f'command {command} not found or not executable, nothing run')
            return
        args = [event, torrent_id, torrent_name, download_location]
        if detail is not None:
            args.append(detail)
        deferred = getProcessOutputAndValue(command, [arg.encode('utf8') for arg in args], env=os.environ)
        # the commands of one remove run side by side, so each end names the event and the torrent it closes
        what_ran = f'{command} {event} {torrent_id}'
        deferred.addCallbacks(self.on_command_ended, self.on_command_died,
                              callbackArgs=(what_ran,), errbackArgs=(what_ran,))

    def on_command_ended(self, result: tuple[bytes, bytes, int], what_ran: str) -> None:
        try:
            stdout, stderr, exit_code = result
            self.log_line(f'ran {what_ran} rc={exit_code}')
            if exit_code:
                self.log_output('stdout', stdout)
                self.log_output('stderr', stderr)
        except Exception as exc:
            self.log_failure('on_command_ended', exc)

    def on_command_died(self, failure: Any, what_ran: str) -> None:
        # getProcessOutputAndValue errbacks with (stdout, stderr, signal) when a signal ends the command
        try:
            value = failure.value
            if isinstance(value, tuple) and len(value) == 3:
                stdout, stderr, signal = value
                self.log_line(f'ran {what_ran} killed by signal {signal}')
                self.log_output('stdout', stdout)
                self.log_output('stderr', stderr)
            else:
                self.log_line(f'ran {what_ran} failed: {failure.getErrorMessage()}')
        except Exception as exc:
            self.log_failure('on_command_died', exc)

    # --- the log

    def log_line(self, text: str) -> None:
        # one line appended, stamped in local time as torrentor.log is; a failure to write is swallowed
        self.logger.debug(text)
        with contextlib.suppress(Exception):
            stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
            with open(self.config['log_file'], 'a', encoding='utf-8') as log_file:
                log_file.write(f'{stamp} | {text}\n')

    def log_output(self, stream: str, data: bytes) -> None:
        text = self.password_line.sub(r'\1, <REDACTED>', data.decode('utf8', errors='replace'))
        for line in text.splitlines():
            self.log_line(f'  {stream} | {line}')

    def log_failure(self, handler_name: str, exc: Exception) -> None:
        # one line, whatever the exception's text spans: Boost.Python's ArgumentError spans four
        text = ' '.join(str(exc).split())
        self.log_line(f'handler {handler_name} failed: {type(exc).__name__}: {text}')
