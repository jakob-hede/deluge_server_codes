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
    Oceanic's plugin. Hears the daemon's alerts and events and runs one command per hearing: libtorrent's removed,
    deleted and delete-failed alerts, which Deluge's alert manager receives and nothing in Deluge handles; the
    metadata, storage-move and rename-failed alerts, after Deluge's own handlers of them; and Deluge's added,
    finished and renamed events. It writes every one to its own log, oceanic_plugin.log, and spawns the shim, the one
    configured command, for every one, the event named in the daemon's own words; the shim runs the runnor, which
    hands the event to the hook, and the hook is the one gate: all policy lives there. An alert handler has two
    seconds before the alert manager gives up on it, so nothing here blocks, sleeps or waits: the shim is spawned and
    its end is a callback. Deluge's own log is not read on this box, so no handler raises: a failure is one line in
    the plugin's log.
    """

    plugin_version: ClassVar[str] = '0.3'
    # the plugin's log is no setting, since Deluge loads oceanic.conf over the defaults: the log_file key an
    # oceanic.conf written by 0.1 carries is read by nothing
    log_file: ClassVar[str] = '/deluge/log/oceanic_plugin.log'
    # the command alone, the hook being the one gate: the events key an oceanic.conf written by 0.1 carries is read
    # by nothing either, so no list there needs editing by hand at a phase
    DEFAULT_CONFIG: ClassVar[dict[str, Any]] = {
        'command': '/codes/oceanic_plugin/oceanic.sh',
    }
    # the removal trio's torrents have left the session when their alerts come, so their name and location are the
    # pre-removed cache's; every other hearing's torrent is still in the session
    cached_events: ClassVar[tuple[str, ...]] = ('removed', 'deleted', 'delete_failed')
    logger: ClassVar[logging.Logger] = logging.getLogger(__name__)
    # a DelugApi prints its password when it is built; the shim's output is filtered as every shell here does
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
            Hearing(Hearing.Kind.EVENT, 'TorrentAddedEvent', self.on_torrent_added),
            Hearing(Hearing.Kind.EVENT, 'TorrentFinishedEvent', self.on_torrent_finished),
            Hearing(Hearing.Kind.EVENT, 'TorrentFolderRenamedEvent', self.on_torrent_folder_renamed),
            Hearing(Hearing.Kind.EVENT, 'TorrentFileRenamedEvent', self.on_torrent_file_renamed),
            Hearing(Hearing.Kind.ALERT, 'metadata_received', self.on_metadata_received),
            Hearing(Hearing.Kind.ALERT, 'metadata_failed', self.on_metadata_failed),
            Hearing(Hearing.Kind.ALERT, 'storage_moved', self.on_storage_moved),
            Hearing(Hearing.Kind.ALERT, 'storage_moved_failed', self.on_storage_moved_failed),
            Hearing(Hearing.Kind.ALERT, 'file_rename_failed', self.on_file_rename_failed),
        )

    def enable(self) -> None:
        self.config = ConfigManager('oceanic.conf', self.DEFAULT_CONFIG)
        self.preremoved_cache = {}
        for hearing in self.hearings:
            hearing.register()
        self.log_line(f"enabled Oceanic {self.plugin_version}, command {self.config['command']}, log {self.log_file}")

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

    def on_torrent_added(self, torrent_id: str, from_state: bool) -> None:
        try:
            if from_state:
                # every torrent the daemon replays from its state at start; Execute returns at once on it too
                self.log_line(f'TorrentAddedEvent id {torrent_id} from state, nothing run')
                return
            self.log_line(f'TorrentAddedEvent id {torrent_id}')
            self.run_command('added', torrent_id)
        except Exception as exc:
            self.log_failure('on_torrent_added', exc)

    def on_torrent_finished(self, torrent_id: str) -> None:
        try:
            # emitted once Deluge's own move_completed has landed, when there was one to wait on
            self.log_line(f'TorrentFinishedEvent id {torrent_id}')
            self.run_command('finished', torrent_id)
        except Exception as exc:
            self.log_failure('on_torrent_finished', exc)

    def on_torrent_folder_renamed(self, torrent_id: str, old: str, new: str) -> None:
        try:
            # one event for the whole folder, once its last file has landed; Deluge swallows the files' own alerts
            self.log_line(f"TorrentFolderRenamedEvent id {torrent_id} old '{old}' new '{new}'")
            self.run_command('folder_renamed', torrent_id, old, new)
        except Exception as exc:
            self.log_failure('on_torrent_folder_renamed', exc)

    def on_torrent_file_renamed(self, torrent_id: str, index: int, name: str) -> None:
        try:
            # a file renamed on its own, no part of a folder rename
            self.log_line(f"TorrentFileRenamedEvent id {torrent_id} index {index} name '{name}'")
            self.run_command('file_renamed', torrent_id, str(index), name)
        except Exception as exc:
            self.log_failure('on_torrent_file_renamed', exc)

    def on_metadata_received(self, alert: Any) -> None:
        try:
            # after Deluge's own handler, which has written the .torrent; a magnet's prefetch torrent is in no session
            torrent_id = self.handle_id(alert)
            self.log_line(f"{alert.what()} id {torrent_id} name '{alert.torrent_name}'")
            self.run_command('metadata_received', torrent_id)
        except Exception as exc:
            self.log_failure('on_metadata_received', exc)

    def on_metadata_failed(self, alert: Any) -> None:
        try:
            torrent_id = self.handle_id(alert)
            error = alert.error.message()
            self.log_line(f"{alert.what()} id {torrent_id} name '{alert.torrent_name}' "
                          f"error '{error}' ({alert.error.value()})")
            self.run_command('metadata_failed', torrent_id, error)
        except Exception as exc:
            self.log_failure('on_metadata_failed', exc)

    def on_storage_moved(self, alert: Any) -> None:
        try:
            # after Deluge's own handler, which has set the torrent's new download location
            torrent_id = self.handle_id(alert)
            storage_path = alert.storage_path()
            self.log_line(f"{alert.what()} id {torrent_id} name '{alert.torrent_name}' "
                          f"from '{alert.old_path()}' to '{storage_path}'")
            self.run_command('storage_moved', torrent_id, storage_path)
        except Exception as exc:
            self.log_failure('on_storage_moved', exc)

    def on_storage_moved_failed(self, alert: Any) -> None:
        try:
            # Deluge forces the torrent into error state, and still emits TorrentFinishedEvent if it waited on the move
            torrent_id = self.handle_id(alert)
            error = alert.error.message()
            file_path = alert.file_path()
            self.log_line(f"{alert.what()} id {torrent_id} name '{alert.torrent_name}' "
                          f"error '{error}' ({alert.error.value()}) file '{file_path}'")
            detail = (error, file_path) if file_path else (error,)
            self.run_command('storage_moved_failed', torrent_id, *detail)
        except Exception as exc:
            self.log_failure('on_storage_moved_failed', exc)

    def on_file_rename_failed(self, alert: Any) -> None:
        try:
            torrent_id = self.handle_id(alert)
            index = alert.index
            error = alert.error.message()
            self.log_line(f"{alert.what()} id {torrent_id} name '{alert.torrent_name}' index {index} "
                          f"error '{error}' ({alert.error.value()})")
            self.run_command('file_rename_failed', torrent_id, str(index), error)
        except Exception as exc:
            self.log_failure('on_file_rename_failed', exc)

    @staticmethod
    def handle_id(alert: Any) -> str:
        # a handle-based alert's torrent id, read as Deluge's own handlers read it; a handle whose torrent has left the
        # session gives forty zeros, which no torrent has, or raises RuntimeError, which the handler logs
        return str(alert.handle.info_hash())

    # --- the command

    def run_command(self, event: str, torrent_id: str, *detail: str) -> None:
        facts = self.torrent_facts(event, torrent_id)
        if facts is None:
            return
        torrent_name, download_location = facts
        command = os.path.expanduser(os.path.expandvars(self.config['command']))
        if not (os.path.isfile(command) and os.access(command, os.X_OK)):
            self.log_line(f'command {command} not found or not executable, nothing run')
            return
        args = [event, torrent_id, torrent_name, download_location, *detail]
        deferred = getProcessOutputAndValue(command, [arg.encode('utf8') for arg in args], env=os.environ)
        # the commands of one remove run side by side, so each end names the event and the torrent it closes
        what_ran = f'{command} {event} {torrent_id}'
        deferred.addCallbacks(self.on_command_ended, self.on_command_died,
                              callbackArgs=(what_ran,), errbackArgs=(what_ran,))

    def torrent_facts(self, event: str, torrent_id: str) -> tuple[str, str] | None:
        # the name and location the shim is given, from one of two sources, Execute's two; a miss is one line, and
        # nothing is run
        if event in self.cached_events:
            cached = self.preremoved_cache.get(torrent_id)
            if cached is None:
                self.log_line(f'no cached location for {torrent_id}, nothing run')
                return None
            _, torrent_name, download_location = cached
            return torrent_name, download_location
        torrent = component.get('TorrentManager').torrents.get(torrent_id)
        if torrent is None:
            self.log_line(f'no torrent {torrent_id} in the session for {event}, nothing run')
            return None
        status = torrent.get_status(['name', 'download_location'])
        return status['name'], status['download_location']

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
            with open(self.log_file, 'a', encoding='utf-8') as log:
                log.write(f'{stamp} | {text}\n')

    def log_output(self, stream: str, data: bytes) -> None:
        text = self.password_line.sub(r'\1, <REDACTED>', data.decode('utf8', errors='replace'))
        for line in text.splitlines():
            self.log_line(f'  {stream} | {line}')

    def log_failure(self, handler_name: str, exc: Exception) -> None:
        # one line, whatever the exception's text spans: Boost.Python's ArgumentError spans four
        text = ' '.join(str(exc).split())
        self.log_line(f'handler {handler_name} failed: {type(exc).__name__}: {text}')
