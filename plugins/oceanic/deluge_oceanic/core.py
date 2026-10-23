from __future__ import annotations

import contextlib
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, ClassVar, Container

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


@dataclass(frozen=True)
class TorrentIds:
    """
    The id Deluge files a torrent under, of the hashes an alert names it by, and the other hash a hybrid v1/v2 torrent
    has; written as the log lines name a torrent.
    """

    torrent_id: str
    others: tuple[str, ...] = ()

    def __str__(self) -> str:
        return f'id {self.torrent_id}' + (f" also {' '.join(self.others)}" if self.others else '')

    @classmethod
    def resolved(cls, info_hashes: Any, info_hash: Any, known: Container[str]) -> TorrentIds:
        # the v1 first, a magnet's btih, which Deluge files a magnet add under; then the alert's own, which libtorrent
        # 2.0 gives a hybrid as its v2 hash truncated and which Deluge files a .torrent add under; the first known one,
        # else the first, for the miss line. A handle whose torrent has left the session gives forty zeros for both,
        # which no torrent has, or raises RuntimeError
        candidates = [str(info_hashes.v1)] if info_hashes.has_v1() else []
        if str(info_hash) not in candidates:
            candidates.append(str(info_hash))
        torrent_id = next((candidate for candidate in candidates if candidate in known), candidates[0])
        return cls(torrent_id, tuple(candidate for candidate in candidates if candidate != torrent_id))


class Core(CorePluginBase):
    """
    Oceanic's plugin. Hears the daemon's alerts and events and runs one command per hearing: libtorrent's removed,
    deleted and delete-failed alerts, which Deluge's alert manager receives and nothing in Deluge handles; the
    metadata, storage-move, rename-failed and finished alerts, after Deluge's own handlers of them; and Deluge's
    added, finished and renamed events. It writes every one to its own log, oceanic_plugin.log, and spawns the shim,
    the one configured command, for every one, the event named in the daemon's own words; the shim runs the runnor,
    which hands the event to the hook, and the hook is the one gate: all policy lives there. A hybrid v1/v2 torrent
    has two hashes, and libtorrent 2.0 names its alerts by the v2 one truncated while Deluge files a magnet add under
    the v1, so a handle-based alert is resolved to Deluge's id by either hash, and the metadata Deluge's own handler
    then missed is repaired here, the one line of Deluge's work the plugin does; the raw finish says whether
    Deluge's own handler found the torrent. An alert handler has two seconds
    before the alert manager gives up on it, so nothing here blocks, sleeps or waits: the shim is spawned and its end
    is a callback. Deluge's own log is not read on this box, so no handler raises: a failure is one line in the
    plugin's log.
    """

    plugin_version: ClassVar[str] = '0.5'
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
    metadata_repaired: set[str]

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
            Hearing(Hearing.Kind.ALERT, 'torrent_finished', self.on_torrent_finished_alert),
        )

    def enable(self) -> None:
        self.config = ConfigManager('oceanic.conf', self.DEFAULT_CONFIG)
        self.preremoved_cache = {}
        self.metadata_repaired = set()
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
        # the alerts come after the torrent has left the session, so its name and location are kept before; a torrent
        # added again is a new Torrent, whose missed metadata is repaired again
        try:
            self.metadata_repaired.discard(torrent_id)
            torrent = component.get('TorrentManager').torrents[torrent_id]
            status = torrent.get_status(['name', 'download_location'])
            self.preremoved_cache[torrent_id] = [torrent_id, status['name'], status['download_location']]
        except Exception as exc:
            self.log_failure('on_preremoved', exc)

    def on_torrent_deleted(self, alert: Any) -> None:
        try:
            ids = self.cached_ids(alert)
            torrent_id = ids.torrent_id
            self.log_line(f"{alert.what()} {ids} name '{alert.torrent_name}'")
            self.run_command('deleted', torrent_id)
        except Exception as exc:
            self.log_failure('on_torrent_deleted', exc)

    def on_torrent_delete_failed(self, alert: Any) -> None:
        try:
            ids = self.cached_ids(alert)
            torrent_id = ids.torrent_id
            error = alert.error.message()
            self.log_line(f"{alert.what()} {ids} name '{alert.torrent_name}' error '{error}' ({alert.error.value()})")
            self.run_command('delete_failed', torrent_id, error)
        except Exception as exc:
            self.log_failure('on_torrent_delete_failed', exc)

    def on_torrent_removed(self, alert: Any) -> None:
        try:
            ids = self.cached_ids(alert)
            torrent_id = ids.torrent_id
            self.log_line(f"{alert.what()} {ids} name '{alert.torrent_name}'")
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
            # a hybrid added from a .torrent file is filed under its v2 hash truncated, while the click's record is
            # named by the magnet's v1: the hook is given the v1 to find it by, a hybrid magnet added bare needing none
            torrent = component.get('TorrentManager').torrents.get(torrent_id)
            info_hashes = torrent.handle.info_hashes() if torrent is not None else None
            v1 = str(info_hashes.v1) if info_hashes is not None and info_hashes.has_v1() else ''
            detail = (v1,) if v1 and v1 != torrent_id else ()
            self.log_line(f'TorrentAddedEvent id {torrent_id}' + (f' v1 {v1}' if detail else ''))
            self.run_command('added', torrent_id, *detail)
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
            # after Deluge's own handler, which has written the .torrent unless it missed a hybrid, which the one detail
            # says, as on the raw finish; a magnet's prefetch torrent is in no session
            ids = self.live_ids(alert.handle)
            deluge = self.deluge_word(alert.handle)
            self.log_line(f"{alert.what()} {ids} name '{alert.torrent_name}' {deluge}")
            self.run_handle_command('metadata_received', ids.torrent_id, alert.handle, deluge)
        except Exception as exc:
            self.log_failure('on_metadata_received', exc)

    def on_metadata_failed(self, alert: Any) -> None:
        try:
            ids = self.live_ids(alert.handle)
            error = alert.error.message()
            self.log_line(f"{alert.what()} {ids} name '{alert.torrent_name}' "
                          f"error '{error}' ({alert.error.value()})")
            self.run_handle_command('metadata_failed', ids.torrent_id, alert.handle, error)
        except Exception as exc:
            self.log_failure('on_metadata_failed', exc)

    def on_storage_moved(self, alert: Any) -> None:
        try:
            # after Deluge's own handler, which has set the torrent's new download location unless it missed a hybrid
            ids = self.live_ids(alert.handle)
            storage_path = alert.storage_path()
            self.log_line(f"{alert.what()} {ids} name '{alert.torrent_name}' "
                          f"from '{alert.old_path()}' to '{storage_path}'")
            self.run_handle_command('storage_moved', ids.torrent_id, alert.handle, storage_path)
        except Exception as exc:
            self.log_failure('on_storage_moved', exc)

    def on_storage_moved_failed(self, alert: Any) -> None:
        try:
            # Deluge forces the torrent into error state, and still emits TorrentFinishedEvent if it waited on the move
            ids = self.live_ids(alert.handle)
            error = alert.error.message()
            file_path = alert.file_path()
            self.log_line(f"{alert.what()} {ids} name '{alert.torrent_name}' "
                          f"error '{error}' ({alert.error.value()}) file '{file_path}'")
            detail = (error, file_path) if file_path else (error,)
            self.run_handle_command('storage_moved_failed', ids.torrent_id, alert.handle, *detail)
        except Exception as exc:
            self.log_failure('on_storage_moved_failed', exc)

    def on_file_rename_failed(self, alert: Any) -> None:
        try:
            ids = self.live_ids(alert.handle)
            index = alert.index
            error = alert.error.message()
            self.log_line(f"{alert.what()} {ids} name '{alert.torrent_name}' "
                          f"index {index} error '{error}' ({alert.error.value()})")
            self.run_handle_command('file_rename_failed', ids.torrent_id, alert.handle, str(index), error)
        except Exception as exc:
            self.log_failure('on_file_rename_failed', exc)

    def on_torrent_finished_alert(self, alert: Any) -> None:
        try:
            # libtorrent's own finish, which Deluge's handler misses for a hybrid added bare, so no move_completed and
            # no TorrentFinishedEvent follow for it; posted too for a torrent added complete or rechecked complete. The
            # one detail says which, Deluge's handler looking the torrent up by the alert's own hash
            ids = self.live_ids(alert.handle)
            deluge = self.deluge_word(alert.handle)
            self.log_line(f"{alert.what()} {ids} name '{alert.torrent_name}' {deluge}")
            self.run_handle_command('torrent_finished', ids.torrent_id, alert.handle, deluge)
        except Exception as exc:
            self.log_failure('on_torrent_finished_alert', exc)

    # --- the two hashes of a hybrid

    def live_ids(self, handle: Any) -> TorrentIds:
        # a torrent still in the session, by its handle
        return TorrentIds.resolved(handle.info_hashes(), handle.info_hash(), component.get('TorrentManager').torrents)

    def cached_ids(self, alert: Any) -> TorrentIds:
        # a removal trio's torrent, gone from the session, by the alert's own hashes against the pre-removed cache
        return TorrentIds.resolved(alert.info_hashes, alert.info_hash, self.preremoved_cache)

    def torrent_id_for(self, handle: Any) -> str:
        return self.live_ids(handle).torrent_id

    @staticmethod
    def deluge_word(handle: Any) -> str:
        # whether Deluge's own handler of the alert found the torrent: the lookup it makes, by the handle's own hash
        is_handled = str(handle.info_hash()) in component.get('TorrentManager').torrents
        return 'deluge_handled' if is_handled else 'deluge_missed'

    def run_handle_command(self, event: str, torrent_id: str, handle: Any, *detail: str) -> None:
        # a handle-based hearing's command, its torrent's missed metadata repaired first
        self.repair_metadata(torrent_id, handle)
        self.run_command(event, torrent_id, *detail)

    # --- the metadata Deluge misses for a hybrid added bare

    def repair_metadata(self, torrent_id: str, handle: Any) -> None:
        # Deluge's Torrent of a hybrid added bare never ran on_metadata_received, its own handler having missed the
        # alert: no .torrent written, no files listed, though libtorrent has the metadata. Run here, once per Torrent,
        # the id let go at its removal, from whichever handle-based alert comes first; a failure is a line, the
        # command goes on. The one line of Deluge's work the plugin does
        torrent = component.get('TorrentManager').torrents.get(torrent_id)
        if torrent is None or torrent.has_metadata or torrent_id in self.metadata_repaired:
            return
        try:
            if not handle.status().has_metadata:
                return
            self.metadata_repaired.add(torrent_id)
            torrent.on_metadata_received()
            self.log_line(f"repaired metadata for {torrent_id}, Deluge's handler missed it")
        except Exception as exc:
            self.log_failure('repair_metadata', exc)

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
