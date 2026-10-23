#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

# the plugin's source, beside py/, imported as the daemon imports it from the egg
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'plugins' / 'oceanic'))

import deluge.component as component  # noqa: E402
import deluge.configmanager as configmanager  # noqa: E402
from twisted.internet.defer import Deferred  # noqa: E402
from twisted.python.failure import Failure  # noqa: E402

import deluge_oceanic.core as core_module  # noqa: E402
from deluge_oceanic.core import Core  # noqa: E402


class FakeRPCServer(component.Component):
    def __init__(self):
        super().__init__('RPCServer')
        self.objects: dict[str, object] = {}

    def register_object(self, obj: object, name: str):
        self.objects[name] = obj

    def deregister_object(self, obj: object):
        self.objects = {name: kept for name, kept in self.objects.items() if kept is not obj}


class FakeEventManager(component.Component):
    def __init__(self):
        super().__init__('EventManager')
        self.handlers: list[tuple[str, Callable]] = []

    def register_event_handler(self, event: str, handler: Callable):
        self.handlers.append((event, handler))

    def deregister_event_handler(self, event: str, handler: Callable):
        self.handlers.remove((event, handler))


class FakeAlertManager(component.Component):
    def __init__(self):
        super().__init__('AlertManager')
        self.handlers: list[tuple[str, Callable]] = []

    def register_handler(self, alert_type: str, handler: Callable):
        self.handlers.append((alert_type, handler))

    def deregister_handler(self, handler: Callable):
        self.handlers = [(alert_type, kept) for alert_type, kept in self.handlers if kept != handler]


ZEROS = '0' * 40


class FakeInfoHashes:
    """libtorrent 2.0's info_hash_t: a torrent's v1 hash and its v2, either one zeros when the torrent has none."""

    def __init__(self, v1: str, v2: str):
        self.v1 = v1
        self.v2 = v2

    def has_v1(self) -> bool:
        return self.v1 != ZEROS

    def has_v2(self) -> bool:
        return self.v2 != ZEROS


class FakeHandleStatus:
    def __init__(self, has_metadata: bool):
        self.has_metadata = has_metadata


class FakeTorrent:
    def __init__(self, name: str, download_location: str, handle: 'FakeHandle', has_metadata: bool = True):
        self.name = name
        self.download_location = download_location
        self.handle = handle
        self.has_metadata = has_metadata
        self.metadata_runs = 0
        self.is_repair_raising = False

    def get_status(self, keys: list[str]) -> dict[str, str]:
        status = {'name': self.name, 'download_location': self.download_location}
        return {key: status[key] for key in keys}

    def on_metadata_received(self):
        # Deluge's Torrent.on_metadata_received sets has_metadata, then writes the .torrent; the raising one fails
        # before the flag, so only the plugin's own once-per-torrent set stops a second try
        self.metadata_runs += 1
        if self.is_repair_raising:
            raise OSError(28, 'No space left on device')
        self.has_metadata = True


class FakeTorrentManager(component.Component):
    def __init__(self):
        super().__init__('TorrentManager')
        self.torrents: dict[str, FakeTorrent] = {}


class FakeErrorCode:
    def __init__(self, message: str, value: int):
        self._message = message
        self._value = value

    def message(self) -> str:
        return self._message

    def value(self) -> int:
        return self._value


class FakeAlert:
    """A removal trio's alert, which names its torrent by its own hashes, no handle: info_hash, a hybrid's v2 truncated,
    and info_hashes, its v1 by default the same, as a v1-only torrent's is."""

    def __init__(self, what: str, info_hash: str, torrent_name: str, error: FakeErrorCode | None = None,
                 v1: str | None = None):
        self._what = what
        self._info_hash = info_hash
        self._info_hashes = FakeInfoHashes(info_hash if v1 is None else v1, ZEROS)
        self.torrent_name = torrent_name
        if error is not None:
            self.error = error

    def what(self) -> str:
        return self._what

    @property
    def info_hash(self) -> str:
        return self._info_hash

    @property
    def info_hashes(self) -> FakeInfoHashes:
        return self._info_hashes


class RaisingAlert(FakeAlert):
    # its text spans two lines, as Boost.Python's ArgumentError spans four, for the failed line to fold
    @property
    def info_hash(self) -> str:
        raise RuntimeError('info_hash raised\n    on purpose')

    @property
    def info_hashes(self) -> FakeInfoHashes:
        raise RuntimeError('info_hash raised\n    on purpose')


class FakeHandle:
    """A torrent's handle: info_hash() the hash libtorrent names it by, a hybrid's v2 truncated, its v1 by default the
    same, as a v1-only torrent's is; status() says whether libtorrent has the metadata."""

    def __init__(self, info_hash: str, v1: str | None = None, v2: str = ZEROS, has_metadata: bool = True):
        self._info_hash = info_hash
        self._info_hashes = FakeInfoHashes(info_hash if v1 is None else v1, v2)
        self._status = FakeHandleStatus(has_metadata)

    def info_hash(self) -> str:
        return self._info_hash

    def info_hashes(self) -> FakeInfoHashes:
        return self._info_hashes

    def status(self) -> FakeHandleStatus:
        return self._status


class RaisingHandle(FakeHandle):
    # a handle gone invalid, as Deluge's own handlers guard it
    def info_hash(self) -> str:
        raise RuntimeError('invalid torrent handle used')

    def info_hashes(self) -> FakeInfoHashes:
        raise RuntimeError('invalid torrent handle used')


class FakeHandleAlert:
    """A handle-based alert, metadata_received, metadata_failed and the storage and rename ones: its torrent id is its
    handle's; each carries only the fields its alert has, so a handler reaching for another fails."""

    def __init__(self, what: str, handle: FakeHandle, torrent_name: str, **fields: object):
        self._what = what
        self.handle = handle
        self.torrent_name = torrent_name
        self._fields = fields
        for name in ('error', 'index'):
            if name in fields:
                setattr(self, name, fields[name])

    def what(self) -> str:
        return self._what

    def storage_path(self) -> object:
        return self._fields['storage_path']

    def old_path(self) -> object:
        return self._fields['old_path']

    def file_path(self) -> object:
        return self._fields['file_path']


class SpawnRecordor:
    # stands in for getProcessOutputAndValue: records the call and hands back a Deferred the case fires
    def __init__(self):
        self.calls: list[tuple[str, list[bytes]]] = []
        self.deferreds: list[Deferred] = []

    def spawn(self, command: str, args: list[bytes], env: Any = None) -> Deferred:
        self.calls.append((command, list(args)))
        deferred = Deferred()
        self.deferreds.append(deferred)
        return deferred


class Testor:
    def __init__(self):
        super().__init__()
        self.base = Path(tempfile.mkdtemp(prefix='oceanic_testor_'))
        self.log_file = self.base / 'oceanic_plugin.log'
        self.command = self.base / 'oceanic.sh'
        self.command.write_text('#!/bin/sh\nexit 0\n')
        self.command.chmod(0o755)
        configmanager.set_config_dir(str(self.base / 'config'))
        # the config the plugin's enable will get, ConfigManager handing back one object per file name
        config = configmanager.ConfigManager('oceanic.conf', Core.DEFAULT_CONFIG)
        config['command'] = str(self.command)
        # the two keys an oceanic.conf written by 0.1 carries, as the box's does, which 0.3 must not read: the log is
        # the class's, and the hook is the one gate
        self.old_log_file = self.base / 'oceanic.log'
        config['log_file'] = str(self.old_log_file)
        config['events'] = ['removed', 'deleted', 'delete_failed']
        Core.log_file = str(self.log_file)
        self.rpc_server = FakeRPCServer()
        self.event_manager = FakeEventManager()
        self.alert_manager = FakeAlertManager()
        self.torrent_manager = FakeTorrentManager()
        self.recordor = SpawnRecordor()
        core_module.getProcessOutputAndValue = self.recordor.spawn
        self.core = Core('Oceanic')
        self.lines_read = 0
        self.all_as_expected = True

    def new_lines(self) -> list[str]:
        # the log's lines since the last call, the stamps cut off
        lines = self.log_file.read_text().splitlines() if self.log_file.exists() else []
        fresh = lines[self.lines_read:]
        self.lines_read = len(lines)
        return [line.split(' | ', 1)[1] for line in fresh]

    def judge(self, case: str, lines: list[str], expected_lines: list[str], spawns: list[tuple[str, list[bytes]]],
              expected_spawns: list[tuple[str, list[bytes]]], *checks: tuple[str, object, object]):
        print(f'--- {case}')
        is_as_expected = lines == expected_lines and spawns == expected_spawns
        print(f'lines:    {lines}')
        print(f'expected: {expected_lines}')
        print(f'spawns:   {spawns}')
        print(f'expected: {expected_spawns}')
        for label, value, expected in checks:
            print(f'{label}: {value!r}  expected {expected!r}')
            is_as_expected = is_as_expected and value == expected
        print(f'as expected: {is_as_expected}')
        self.all_as_expected = self.all_as_expected and is_as_expected

    def new_spawns(self) -> list[tuple[str, list[bytes]]]:
        spawns = self.recordor.calls
        self.recordor.calls = []
        return spawns

    def spawned(self, *args: str) -> tuple[str, list[bytes]]:
        return str(self.command), [arg.encode('utf8') for arg in args]

    def add_torrent(self, torrent_id: str, name: str, location: str, handle: FakeHandle | None = None,
                    has_metadata: bool = True) -> FakeTorrent:
        torrent = FakeTorrent(name, location, handle or FakeHandle(torrent_id), has_metadata)
        self.torrent_manager.torrents[torrent_id] = torrent
        return torrent

    def case_enable(self):
        self.core.enable()
        events = [(event, handler.__name__) for event, handler in self.event_manager.handlers]
        alerts = [(alert_type, handler.__name__) for alert_type, handler in self.alert_manager.handlers]
        self.judge('enable registers five event handlers and nine alert handlers', self.new_lines(),
                   [f'enabled Oceanic 0.5, command {self.command}, log {self.log_file}'],
                   self.new_spawns(), [],
                   ('event handlers', events, [('PreTorrentRemovedEvent', 'on_preremoved'),
                                               ('TorrentAddedEvent', 'on_torrent_added'),
                                               ('TorrentFinishedEvent', 'on_torrent_finished'),
                                               ('TorrentFolderRenamedEvent', 'on_torrent_folder_renamed'),
                                               ('TorrentFileRenamedEvent', 'on_torrent_file_renamed')]),
                   ('alert handlers', alerts, [('torrent_deleted', 'on_torrent_deleted'),
                                               ('torrent_delete_failed', 'on_torrent_delete_failed'),
                                               ('torrent_removed', 'on_torrent_removed'),
                                               ('metadata_received', 'on_metadata_received'),
                                               ('metadata_failed', 'on_metadata_failed'),
                                               ('storage_moved', 'on_storage_moved'),
                                               ('storage_moved_failed', 'on_storage_moved_failed'),
                                               ('file_rename_failed', 'on_file_rename_failed'),
                                               ('torrent_finished', 'on_torrent_finished_alert')]),
                   ('rpc objects', list(self.rpc_server.objects), ['oceanic']),
                   ('the defaults', Core.DEFAULT_CONFIG, {'command': '/codes/oceanic_plugin/oceanic.sh'}),
                   ("the 0.1 conf's log_file written to", self.old_log_file.exists(), False))

    def case_preremoved_caches(self):
        self.add_torrent(self.florist_id, 'the.florist.2026', self.movin)
        self.core.on_preremoved(self.florist_id)
        self.judge('on_preremoved caches the id, name and location', self.new_lines(), [], self.new_spawns(), [],
                   ('cache', self.core.preremoved_cache.get(self.florist_id),
                    [self.florist_id, 'the.florist.2026', self.movin]))

    def case_deleted(self):
        self.core.on_torrent_deleted(FakeAlert('torrent_deleted', self.florist_id, 'the.florist.2026'))
        self.judge('on_torrent_deleted spawns four arguments, deleted first', self.new_lines(),
                   [f"torrent_deleted id {self.florist_id} name 'the.florist.2026'"],
                   self.new_spawns(), [self.spawned('deleted', self.florist_id, 'the.florist.2026', self.movin)],
                   ('cache kept', self.florist_id in self.core.preremoved_cache, True))

    def case_delete_failed(self):
        error = FakeErrorCode('Directory not empty', 39)
        self.core.on_torrent_delete_failed(FakeAlert('torrent_delete_failed', self.florist_id, 'the.florist.2026', error))
        self.judge('on_torrent_delete_failed spawns five arguments, the error last', self.new_lines(),
                   [f"torrent_delete_failed id {self.florist_id} name 'the.florist.2026' "
                    f"error 'Directory not empty' (39)"],
                   self.new_spawns(), [self.spawned('delete_failed', self.florist_id, 'the.florist.2026', self.movin,
                                                    'Directory not empty')],
                   ('cache kept', self.florist_id in self.core.preremoved_cache, True))

    def case_removed(self):
        self.core.on_torrent_removed(FakeAlert('torrent_removed', self.florist_id, 'the.florist.2026'))
        self.judge('on_torrent_removed spawns four arguments, removed first, and empties the cache', self.new_lines(),
                   [f"torrent_removed id {self.florist_id} name 'the.florist.2026'",
                    f'popped {self.florist_id} from the cache, 0 left'],
                   self.new_spawns(), [self.spawned('removed', self.florist_id, 'the.florist.2026', self.movin)],
                   ('cache', self.core.preremoved_cache, {}))

    def case_uncached(self):
        self.core.on_torrent_deleted(FakeAlert('torrent_deleted', self.stranger_id, 'the.stranger.2026'))
        self.judge('an alert for an uncached id spawns nothing and logs the miss', self.new_lines(),
                   [f"torrent_deleted id {self.stranger_id} name 'the.stranger.2026'",
                    f'no cached location for {self.stranger_id}, nothing run'],
                   self.new_spawns(), [])

    def case_stale_events_key(self):
        # the gate left the conf: an events list struck to nothing there still lets every hearing through
        self.add_torrent(self.killer_id, 'the.killer.2023', self.movin)
        self.core.on_preremoved(self.killer_id)
        self.core.config['events'] = []
        error = FakeErrorCode('Directory not empty', 39)
        self.core.on_torrent_delete_failed(FakeAlert('torrent_delete_failed', self.killer_id, 'the.killer.2023', error))
        self.core.on_torrent_finished(self.killer_id)
        self.core.config['events'] = ['removed', 'deleted', 'delete_failed']
        self.judge("a stale events key in the conf gates nothing", self.new_lines(),
                   [f"torrent_delete_failed id {self.killer_id} name 'the.killer.2023' error 'Directory not empty' (39)",
                    f'TorrentFinishedEvent id {self.killer_id}'],
                   self.new_spawns(), [self.spawned('delete_failed', self.killer_id, 'the.killer.2023', self.movin,
                                                    'Directory not empty'),
                                       self.spawned('finished', self.killer_id, 'the.killer.2023', self.movin)])
        self.core.preremoved_cache.pop(self.killer_id, None)
        self.torrent_manager.torrents.pop(self.killer_id, None)

    # --- the hearings of phases 3 and 4, their torrents live in the session

    def case_added_from_state(self):
        self.add_torrent(self.cream_id, self.cream_raw, self.downloads)
        self.core.on_torrent_added(self.cream_id, True)
        self.judge('added from state, at daemon start, is one line and runs nothing', self.new_lines(),
                   [f'TorrentAddedEvent id {self.cream_id} from state, nothing run'], self.new_spawns(), [])

    def case_added(self):
        self.core.on_torrent_added(self.cream_id, False)
        self.judge("added runs the command with the live torrent's name and location", self.new_lines(),
                   [f'TorrentAddedEvent id {self.cream_id}'],
                   self.new_spawns(), [self.spawned('added', self.cream_id, self.cream_raw, self.downloads)],
                   ('the cache untouched', self.core.preremoved_cache, {}))

    def case_metadata_received(self):
        self.core.on_metadata_received(FakeHandleAlert('metadata_received', FakeHandle(self.cream_id), self.cream_raw))
        self.judge('metadata_received of a torrent Deluge handled runs the command, deluge_handled, no repair',
                   self.new_lines(), [f"metadata_received id {self.cream_id} name '{self.cream_raw}' deluge_handled"],
                   self.new_spawns(), [self.spawned('metadata_received', self.cream_id, self.cream_raw, self.downloads,
                                                    'deluge_handled')],
                   ('metadata runs', self.torrent_manager.torrents[self.cream_id].metadata_runs, 0))

    def case_metadata_received_prefetch(self):
        # a magnet's prefetch torrent, added and removed by Deluge beside the session's torrent list
        self.core.on_metadata_received(FakeHandleAlert('metadata_received', FakeHandle(self.stranger_id),
                                                       'the.stranger.2026'))
        self.judge('a torrent not in the session is one line more and runs nothing', self.new_lines(),
                   [f"metadata_received id {self.stranger_id} name 'the.stranger.2026' deluge_missed",
                    f'no torrent {self.stranger_id} in the session for metadata_received, nothing run'],
                   self.new_spawns(), [])

    def case_metadata_failed(self):
        error = FakeErrorCode('Operation timed out', 110)
        self.core.on_metadata_failed(FakeHandleAlert('metadata_failed', FakeHandle(self.cream_id), self.cream_raw,
                                                     error=error))
        self.judge("metadata_failed runs the command, the error's text last", self.new_lines(),
                   [f"metadata_failed id {self.cream_id} name '{self.cream_raw}' error 'Operation timed out' (110)"],
                   self.new_spawns(), [self.spawned('metadata_failed', self.cream_id, self.cream_raw, self.downloads,
                                                    'Operation timed out')])

    def case_finished(self):
        self.core.on_torrent_finished(self.cream_id)
        self.judge('finished runs the command, no detail', self.new_lines(), [f'TorrentFinishedEvent id {self.cream_id}'],
                   self.new_spawns(), [self.spawned('finished', self.cream_id, self.cream_raw, self.downloads)])

    def case_torrent_finished_handled(self):
        # a v1 torrent's raw finish: Deluge's own handler finds it by the alert's hash, and does the move and the event
        self.core.on_torrent_finished_alert(FakeHandleAlert('torrent_finished', FakeHandle(self.cream_id), self.cream_raw))
        self.judge('torrent_finished of a torrent Deluge handles passes deluge_handled', self.new_lines(),
                   [f"torrent_finished id {self.cream_id} name '{self.cream_raw}' deluge_handled"],
                   self.new_spawns(), [self.spawned('torrent_finished', self.cream_id, self.cream_raw, self.downloads,
                                                    'deluge_handled')])

    def case_storage_moved(self):
        # Deluge's own handler ran first and set the new location, which the live torrent now gives
        self.torrent_manager.torrents[self.cream_id].download_location = self.movin
        self.core.on_storage_moved(FakeHandleAlert('storage_moved', FakeHandle(self.cream_id), self.cream_raw,
                                                   storage_path=self.movin, old_path=self.downloads))
        self.judge('storage_moved runs the command, the new path last, the location read live', self.new_lines(),
                   [f"storage_moved id {self.cream_id} name '{self.cream_raw}' from '{self.downloads}' to '{self.movin}'"],
                   self.new_spawns(), [self.spawned('storage_moved', self.cream_id, self.cream_raw, self.movin,
                                                    self.movin)])

    def case_storage_moved_failed(self):
        error = FakeErrorCode('Permission denied', 13)
        self.core.on_storage_moved_failed(FakeHandleAlert('storage_moved_failed', FakeHandle(self.cream_id),
                                                          self.cream_raw, error=error, file_path=f'{self.movin}/x.mkv'))
        self.core.on_storage_moved_failed(FakeHandleAlert('storage_moved_failed', FakeHandle(self.cream_id),
                                                          self.cream_raw, error=error, file_path=''))
        self.judge("storage_moved_failed runs the command, the error's text, then the file's path when it has one",
                   self.new_lines(),
                   [f"storage_moved_failed id {self.cream_id} name '{self.cream_raw}' error 'Permission denied' (13) "
                    f"file '{self.movin}/x.mkv'",
                    f"storage_moved_failed id {self.cream_id} name '{self.cream_raw}' error 'Permission denied' (13) "
                    f"file ''"],
                   self.new_spawns(), [self.spawned('storage_moved_failed', self.cream_id, self.cream_raw, self.movin,
                                                    'Permission denied', f'{self.movin}/x.mkv'),
                                       self.spawned('storage_moved_failed', self.cream_id, self.cream_raw, self.movin,
                                                    'Permission denied')])

    def case_folder_renamed(self):
        # two details, in order; the live torrent already goes by the folder's new name
        self.torrent_manager.torrents[self.cream_id].name = self.cream_folder
        self.core.on_torrent_folder_renamed(self.cream_id, f'{self.cream_raw}/', f'{self.cream_folder}/')
        self.judge("folder_renamed runs the command, the old name then the new, the name read live", self.new_lines(),
                   [f"TorrentFolderRenamedEvent id {self.cream_id} old '{self.cream_raw}/' new '{self.cream_folder}/'"],
                   self.new_spawns(), [self.spawned('folder_renamed', self.cream_id, self.cream_folder, self.movin,
                                                    f'{self.cream_raw}/', f'{self.cream_folder}/')])

    def case_file_renamed(self):
        self.core.on_torrent_file_renamed(self.cream_id, 0, f'{self.cream_folder}/ice.cream.man.2026.mkv')
        self.judge('file_renamed runs the command, the index then the new name', self.new_lines(),
                   [f"TorrentFileRenamedEvent id {self.cream_id} index 0 name '{self.cream_folder}/ice.cream.man.2026.mkv'"],
                   self.new_spawns(), [self.spawned('file_renamed', self.cream_id, self.cream_folder, self.movin, '0',
                                                    f'{self.cream_folder}/ice.cream.man.2026.mkv')])

    def case_file_rename_failed(self):
        error = FakeErrorCode('File exists', 17)
        self.core.on_file_rename_failed(FakeHandleAlert('file_rename_failed', FakeHandle(self.cream_id),
                                                        self.cream_raw, error=error, index=1))
        self.judge("file_rename_failed runs the command, the index then the error's text", self.new_lines(),
                   [f"file_rename_failed id {self.cream_id} name '{self.cream_raw}' index 1 error 'File exists' (17)"],
                   self.new_spawns(), [self.spawned('file_rename_failed', self.cream_id, self.cream_folder, self.movin,
                                                    '1', 'File exists')])

    def case_handle_gone(self):
        # a handle gone invalid raises, as Deluge's handlers guard, or gives forty zeros, as libtorrent 2.0.11 did
        # offline: a failed line, or the miss, and nothing run either way
        zeros = '0' * 40
        try:
            self.core.on_storage_moved(FakeHandleAlert('storage_moved', RaisingHandle(self.cream_id), self.cream_raw,
                                                       storage_path=self.movin, old_path=self.downloads))
            self.core.on_metadata_received(FakeHandleAlert('metadata_received', FakeHandle(zeros), self.cream_raw))
            raised = None
        except Exception as exc:
            raised = exc
        self.judge('a handle gone invalid logs one line, its failure or the miss, and runs nothing', self.new_lines(),
                   ['handler on_storage_moved failed: RuntimeError: invalid torrent handle used',
                    f"metadata_received id {zeros} name '{self.cream_raw}' deluge_missed",
                    f'no torrent {zeros} in the session for metadata_received, nothing run'],
                   self.new_spawns(), [],
                   ('raised out', raised, None))
        self.torrent_manager.torrents.pop(self.cream_id, None)

    # --- a hybrid v1/v2 torrent: libtorrent names its alerts by the v2 hash truncated, Deluge files a magnet add by v1

    def hybrid_handle(self, has_metadata: bool = True) -> FakeHandle:
        return FakeHandle(self.morris_v2t, v1=self.morris_v1, v2=self.morris_v2, has_metadata=has_metadata)

    def case_hybrid_ids(self):
        torrents = self.torrent_manager.torrents
        hybrid = self.hybrid_handle()
        found: list[tuple[str, object, object]] = []
        self.add_torrent(self.morris_v1, self.morris_name, self.downloads, hybrid)
        found.append(('a hybrid filed under its v1', self.core.torrent_id_for(hybrid), self.morris_v1))
        torrents[self.morris_v2t] = torrents.pop(self.morris_v1)
        found.append(('a hybrid filed under its v2', self.core.torrent_id_for(hybrid), self.morris_v2t))
        torrents.pop(self.morris_v2t)
        found.append(('a hybrid filed under neither', self.core.torrent_id_for(hybrid), self.morris_v1))
        v2_only = FakeHandle(self.morris_v2t, v1=ZEROS, v2=self.morris_v2)
        found.append(('a v2-only torrent, filed under neither', self.core.torrent_id_for(v2_only), self.morris_v2t))
        found.append(('a dead handle giving zeros', self.core.torrent_id_for(FakeHandle(ZEROS)), ZEROS))
        try:
            self.core.torrent_id_for(RaisingHandle(self.morris_v2t))
            raised = None
        except RuntimeError as exc:
            raised = str(exc)
        found.append(('a dead handle raising', raised, 'invalid torrent handle used'))
        self.judge("torrent_id_for: Deluge's id by either hash, the v1 first, else the first for the miss",
                   self.new_lines(), [], self.new_spawns(), [], *found)

    def case_hybrid_prefetch(self):
        # deluge-gtk's prefetch of a hybrid magnet: in no session, under either hash, both named
        self.core.on_metadata_received(FakeHandleAlert('metadata_received', self.hybrid_handle(), self.morris_name))
        self.judge('a hybrid not in the session names both hashes, one line more, and runs nothing', self.new_lines(),
                   [f"metadata_received id {self.morris_v1} also {self.morris_v2t} name '{self.morris_name}' deluge_missed",
                    f'no torrent {self.morris_v1} in the session for metadata_received, nothing run'],
                   self.new_spawns(), [])

    def case_hybrid_added_bare(self):
        # a hybrid magnet added bare: before the metadata libtorrent knows the v1 alone, and Deluge files it so
        self.add_torrent(self.morris_v1, self.morris_dn, self.downloads, FakeHandle(self.morris_v1, has_metadata=False),
                         has_metadata=False)
        self.core.on_torrent_added(self.morris_v1, False)
        self.judge('a hybrid added bare is filed under its v1, the hook given no detail', self.new_lines(),
                   [f'TorrentAddedEvent id {self.morris_v1}'],
                   self.new_spawns(), [self.spawned('added', self.morris_v1, self.morris_dn, self.downloads)])

    def case_hybrid_metadata_repaired(self):
        # the metadata comes and libtorrent names the torrent by its v2 from now on: Deluge's handler missed it
        torrent = self.torrent_manager.torrents[self.morris_v1]
        torrent.handle = self.hybrid_handle()
        torrent.name = self.morris_name
        self.core.on_metadata_received(FakeHandleAlert('metadata_received', torrent.handle, self.morris_name))
        self.core.on_torrent_finished_alert(FakeHandleAlert('torrent_finished', torrent.handle, self.morris_name))
        is_held = self.morris_v1 in self.core.metadata_repaired
        self.remove_torrent(self.morris_v1)
        self.judge("metadata_received of a hybrid: found by its v1, Deluge's missed metadata repaired once, then "
                   "torrent_finished heard and spawned, no second repair; the id let go at the removal", self.new_lines(),
                   [f"metadata_received id {self.morris_v1} also {self.morris_v2t} name '{self.morris_name}' deluge_missed",
                    f"repaired metadata for {self.morris_v1}, Deluge's handler missed it",
                    f"torrent_finished id {self.morris_v1} also {self.morris_v2t} name '{self.morris_name}' "
                    f"deluge_missed"],
                   self.new_spawns(), [self.spawned('metadata_received', self.morris_v1, self.morris_name, self.downloads,
                                                    'deluge_missed'),
                                       self.spawned('torrent_finished', self.morris_v1, self.morris_name,
                                                    self.downloads, 'deluge_missed')],
                   ('metadata runs', torrent.metadata_runs, 1), ('has metadata', torrent.has_metadata, True),
                   ('the id held while the torrent is in the session', is_held, True),
                   ('the id held after its removal', self.morris_v1 in self.core.metadata_repaired, False))

    def remove_torrent(self, torrent_id: str):
        # as Deluge removes one: PreTorrentRemovedEvent first, then the torrent gone from the session; the cache entry
        # its removed alert would pop, popped here
        self.core.on_preremoved(torrent_id)
        self.torrent_manager.torrents.pop(torrent_id, None)
        self.core.preremoved_cache.pop(torrent_id, None)

    def case_hybrid_added_from_file(self):
        # a hybrid added from its .torrent: Deluge files it under the v2, so the hook is given the v1 for the record
        self.add_torrent(self.morris_v2t, self.morris_name, self.downloads, self.hybrid_handle())
        self.core.on_torrent_added(self.morris_v2t, False)
        self.judge("a hybrid filed under its v2 is added with its v1 as the one detail", self.new_lines(),
                   [f'TorrentAddedEvent id {self.morris_v2t} v1 {self.morris_v1}'],
                   self.new_spawns(), [self.spawned('added', self.morris_v2t, self.morris_name, self.downloads,
                                                    self.morris_v1)])
        self.torrent_manager.torrents.pop(self.morris_v2t)

    def case_repair_on_another_alert(self):
        # the amendment: a torrent already perturbed, Phillip Morris's state since its missed metadata, heals at the
        # first handle-based alert of any kind; the same magnet added again after its removal, as the live verify
        # does, is a new Torrent and is repaired again
        torrent = self.add_torrent(self.morris_v1, self.morris_name, self.downloads, self.hybrid_handle(),
                                   has_metadata=False)
        self.core.on_storage_moved(FakeHandleAlert('storage_moved', torrent.handle, self.morris_name,
                                                   storage_path=self.completed, old_path=self.downloads))
        self.judge('added again and perturbed, the torrent is repaired at a storage_moved alert, the command run after',
                   self.new_lines(),
                   [f"storage_moved id {self.morris_v1} also {self.morris_v2t} name '{self.morris_name}' "
                    f"from '{self.downloads}' to '{self.completed}'",
                    f"repaired metadata for {self.morris_v1}, Deluge's handler missed it"],
                   self.new_spawns(), [self.spawned('storage_moved', self.morris_v1, self.morris_name, self.downloads,
                                                    self.completed)],
                   ('metadata runs', torrent.metadata_runs, 1))
        self.remove_torrent(self.morris_v1)

    def case_repair_fails_once(self):
        # a repair that raises is one line, the command still runs, and it is not tried again while the plugin runs
        torrent = self.add_torrent(self.morris_v1, self.morris_name, self.downloads, self.hybrid_handle(),
                                   has_metadata=False)
        torrent.is_repair_raising = True
        error = FakeErrorCode('File exists', 17)
        for index in (0, 1):
            self.core.on_file_rename_failed(FakeHandleAlert('file_rename_failed', torrent.handle, self.morris_name,
                                                            error=error, index=index))
        self.judge('a failed repair is one line and no second try, both commands run', self.new_lines(),
                   [f"file_rename_failed id {self.morris_v1} also {self.morris_v2t} name '{self.morris_name}' "
                    f"index 0 error 'File exists' (17)",
                    'handler repair_metadata failed: OSError: [Errno 28] No space left on device',
                    f"file_rename_failed id {self.morris_v1} also {self.morris_v2t} name '{self.morris_name}' "
                    f"index 1 error 'File exists' (17)"],
                   self.new_spawns(), [self.spawned('file_rename_failed', self.morris_v1, self.morris_name, self.downloads,
                                                    str(index), 'File exists') for index in (0, 1)],
                   ('metadata runs', torrent.metadata_runs, 1), ('has metadata', torrent.has_metadata, False))
        self.remove_torrent(self.morris_v1)

    def case_no_repair_before_metadata(self):
        # a bare magnet whose metadata never came: libtorrent has none either, so nothing to repair
        torrent = self.add_torrent(self.morris_v1, self.morris_dn, self.downloads,
                                   FakeHandle(self.morris_v1, has_metadata=False), has_metadata=False)
        error = FakeErrorCode('Operation timed out', 110)
        self.core.on_metadata_failed(FakeHandleAlert('metadata_failed', torrent.handle, self.morris_dn, error=error))
        self.judge('metadata_failed of a torrent libtorrent has no metadata for repairs nothing', self.new_lines(),
                   [f"metadata_failed id {self.morris_v1} name '{self.morris_dn}' error 'Operation timed out' (110)"],
                   self.new_spawns(), [self.spawned('metadata_failed', self.morris_v1, self.morris_dn, self.downloads,
                                                    'Operation timed out')],
                   ('metadata runs', torrent.metadata_runs, 0))
        self.remove_torrent(self.morris_v1)

    # --- the removal trio of a hybrid: Deluge caches it under its id, the alerts name it by the v2 hash truncated

    def case_hybrid_removed_by_v1(self):
        # a hybrid added bare, filed under its v1, deleted ticked
        self.add_torrent(self.morris_v1, self.morris_name, self.movin, self.hybrid_handle())
        self.core.on_preremoved(self.morris_v1)
        self.torrent_manager.torrents.pop(self.morris_v1)
        self.core.on_torrent_deleted(FakeAlert('torrent_deleted', self.morris_v2t, self.morris_name, v1=self.morris_v1))
        self.core.on_torrent_removed(FakeAlert('torrent_removed', self.morris_v2t, self.morris_name, v1=self.morris_v1))
        self.judge("a hybrid's removal trio, cached under its v1: found by the v1, the v1 spawned and popped",
                   self.new_lines(),
                   [f"torrent_deleted id {self.morris_v1} also {self.morris_v2t} name '{self.morris_name}'",
                    f"torrent_removed id {self.morris_v1} also {self.morris_v2t} name '{self.morris_name}'",
                    f'popped {self.morris_v1} from the cache, 0 left'],
                   self.new_spawns(), [self.spawned('deleted', self.morris_v1, self.morris_name, self.movin),
                                       self.spawned('removed', self.morris_v1, self.morris_name, self.movin)],
                   ('cache', self.core.preremoved_cache, {}))

    def case_hybrid_removed_by_v2(self):
        # a hybrid added from its .torrent, filed under its v2 truncated, its ticked delete failing on the leftovers
        self.add_torrent(self.morris_v2t, self.morris_name, self.movin, self.hybrid_handle())
        self.core.on_preremoved(self.morris_v2t)
        self.torrent_manager.torrents.pop(self.morris_v2t)
        error = FakeErrorCode('Directory not empty', 39)
        self.core.on_torrent_delete_failed(FakeAlert('torrent_delete_failed', self.morris_v2t, self.morris_name, error,
                                                     v1=self.morris_v1))
        self.core.on_torrent_removed(FakeAlert('torrent_removed', self.morris_v2t, self.morris_name, v1=self.morris_v1))
        self.judge("a hybrid's removal trio, cached under its v2: found by the v2, the v2 spawned and popped",
                   self.new_lines(),
                   [f"torrent_delete_failed id {self.morris_v2t} also {self.morris_v1} name '{self.morris_name}' "
                    f"error 'Directory not empty' (39)",
                    f"torrent_removed id {self.morris_v2t} also {self.morris_v1} name '{self.morris_name}'",
                    f'popped {self.morris_v2t} from the cache, 0 left'],
                   self.new_spawns(), [self.spawned('delete_failed', self.morris_v2t, self.morris_name, self.movin,
                                                    'Directory not empty'),
                                       self.spawned('removed', self.morris_v2t, self.morris_name, self.movin)],
                   ('cache', self.core.preremoved_cache, {}))

    def case_hybrid_removed_uncached(self):
        # deluge-gtk's prefetch of a hybrid, removed beside the session: cached under neither hash
        self.core.on_torrent_deleted(FakeAlert('torrent_deleted', self.morris_v2t, self.morris_name, v1=self.morris_v1))
        self.judge("a hybrid's removal alert cached under neither hash names both and runs nothing", self.new_lines(),
                   [f"torrent_deleted id {self.morris_v1} also {self.morris_v2t} name '{self.morris_name}'",
                    f'no cached location for {self.morris_v1}, nothing run'],
                   self.new_spawns(), [])

    def case_handler_raises(self):
        try:
            self.core.on_torrent_removed(RaisingAlert('torrent_removed', self.killer_id, 'the.killer.2023'))
            raised = None
        except Exception as exc:
            raised = exc
        self.judge('a handler whose body raises logs one failed line, its text folded, and raises nothing',
                   self.new_lines(),
                   ['handler on_torrent_removed failed: RuntimeError: info_hash raised on purpose'],
                   self.new_spawns(), [],
                   ('raised out', raised, None))
        self.core.preremoved_cache.pop(self.killer_id, None)

    def case_command_ends(self):
        # mine, beyond the brief: the spawn's three ends, a clean exit, a failed one whose output carries a
        # DelugApi line, and a signal; the Deferreds are the recordor's, fired by hand
        self.add_torrent(self.florist_id, 'the.florist.2026', self.movin)
        self.add_torrent(self.killer_id, 'the.killer.2023', self.movin)
        self.core.on_preremoved(self.florist_id)
        self.core.on_preremoved(self.killer_id)
        self.core.on_torrent_deleted(FakeAlert('torrent_deleted', self.florist_id, 'the.florist.2026'))
        self.core.on_torrent_deleted(FakeAlert('torrent_deleted', self.killer_id, 'the.killer.2023'))
        self.core.on_torrent_removed(FakeAlert('torrent_removed', self.killer_id, 'the.killer.2023'))
        self.new_lines()
        clean, failed, killed = self.recordor.deferreds[-3:]
        clean.callback((b'fine\n', b'', 0))
        failed.callback((b'DelugApi 10.0.0.1, 58846, someone, not-this-password\nTraceback, the last line\n',
                         b'boom\n', 1))
        killed.errback(Failure((b'half\n', b'', 9)))
        lines = self.new_lines()
        self.judge("the command's ends are logged, a non-zero exit with its output, the password redacted", lines,
                   [f'ran {self.command} deleted {self.florist_id} rc=0',
                    f'ran {self.command} deleted {self.killer_id} rc=1',
                    '  stdout | DelugApi 10.0.0.1, 58846, someone, <REDACTED>',
                    '  stdout | Traceback, the last line',
                    '  stderr | boom',
                    f'ran {self.command} removed {self.killer_id} killed by signal 9',
                    '  stdout | half'],
                   self.new_spawns(), [self.spawned('deleted', self.florist_id, 'the.florist.2026', self.movin),
                                       self.spawned('deleted', self.killer_id, 'the.killer.2023', self.movin),
                                       self.spawned('removed', self.killer_id, 'the.killer.2023', self.movin)],
                   ('a password in the log', any('not-this-password' in line for line in lines), False))
        self.core.preremoved_cache.pop(self.florist_id, None)

    def case_disable(self):
        self.core.disable()
        self.judge('disable deregisters all fourteen', self.new_lines(), ['disabled'], self.new_spawns(), [],
                   ('event handlers', self.event_manager.handlers, []),
                   ('alert handlers', self.alert_manager.handlers, []))

    florist_id = '0123456789abcdef0123456789abcdef01234567'
    stranger_id = 'fedcba9876543210fedcba9876543210fedcba98'
    killer_id = '89abcdef0123456789abcdef0123456789abcdef'
    cream_id = 'c0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ff'
    cream_raw = 'Ice.Cream.Man.2026.1080p.WEBRip.x265'
    cream_folder = 'ice.cream.man.2026'
    # Phillip Morris's two hashes as the operator's click showed them, the v1 the magnet's btih, padded to length
    morris_v1 = 'd1d96f75' * 5
    morris_v2t = 'cc0d690a' * 5
    morris_v2 = 'cc0d690a' * 8
    morris_dn = 'Phillip Morris (2025) 1080p WEB h264'
    morris_name = 'Phillip.Morris.2025.1080p.WEB.h264-GRP'
    movin = '/ocean/video/movies/movin'
    downloads = '/deluge/downloads'
    completed = '/deluge/completed/'

    def executize(self):
        print(f'base: {self.base}')
        self.case_enable()
        self.case_preremoved_caches()
        self.case_deleted()
        self.case_delete_failed()
        self.case_removed()
        self.case_uncached()
        self.case_stale_events_key()
        self.case_handler_raises()
        # one torrent through every hearing of phases 3 and 4, its fake renamed and moved as Deluge would
        self.case_added_from_state()
        self.case_added()
        self.case_metadata_received()
        self.case_metadata_received_prefetch()
        self.case_metadata_failed()
        self.case_finished()
        self.case_torrent_finished_handled()
        self.case_storage_moved()
        self.case_storage_moved_failed()
        self.case_folder_renamed()
        self.case_file_renamed()
        self.case_file_rename_failed()
        self.case_handle_gone()
        # one hybrid torrent added bare through its missed metadata and its finish, then the other shapes and edges
        self.case_hybrid_ids()
        self.case_hybrid_prefetch()
        self.case_hybrid_added_bare()
        self.case_hybrid_metadata_repaired()
        self.case_hybrid_added_from_file()
        self.case_repair_on_another_alert()
        self.case_repair_fails_once()
        self.case_no_repair_before_metadata()
        self.case_hybrid_removed_by_v1()
        self.case_hybrid_removed_by_v2()
        self.case_hybrid_removed_uncached()
        self.case_command_ends()
        self.case_disable()
        print('ALL AS EXPECTED' if self.all_as_expected else 'NOT ALL AS EXPECTED')
        return 0 if self.all_as_expected else 1


def main():
    testor = Testor()
    raise SystemExit(testor.executize())


if __name__ == '__main__':
    main()
