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


class FakeTorrent:
    def __init__(self, name: str, download_location: str):
        self.name = name
        self.download_location = download_location

    def get_status(self, keys: list[str]) -> dict[str, str]:
        status = {'name': self.name, 'download_location': self.download_location}
        return {key: status[key] for key in keys}


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
    def __init__(self, what: str, info_hash: str, torrent_name: str, error: FakeErrorCode | None = None):
        self._what = what
        self._info_hash = info_hash
        self.torrent_name = torrent_name
        if error is not None:
            self.error = error

    def what(self) -> str:
        return self._what

    @property
    def info_hash(self) -> str:
        return self._info_hash


class RaisingAlert(FakeAlert):
    # its text spans two lines, as Boost.Python's ArgumentError spans four, for the failed line to fold
    @property
    def info_hash(self) -> str:
        raise RuntimeError('info_hash raised\n    on purpose')


class FakeHandle:
    def __init__(self, info_hash: str):
        self._info_hash = info_hash

    def info_hash(self) -> str:
        return self._info_hash


class RaisingHandle(FakeHandle):
    # a handle gone invalid, as Deluge's own handlers guard it
    def info_hash(self) -> str:
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

    def add_torrent(self, torrent_id: str, name: str, location: str):
        self.torrent_manager.torrents[torrent_id] = FakeTorrent(name, location)

    def case_enable(self):
        self.core.enable()
        events = [(event, handler.__name__) for event, handler in self.event_manager.handlers]
        alerts = [(alert_type, handler.__name__) for alert_type, handler in self.alert_manager.handlers]
        self.judge('enable registers five event handlers and eight alert handlers', self.new_lines(),
                   [f'enabled Oceanic 0.3, command {self.command}, log {self.log_file}'],
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
                                               ('file_rename_failed', 'on_file_rename_failed')]),
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
        self.judge('metadata_received runs the command, no detail', self.new_lines(),
                   [f"metadata_received id {self.cream_id} name '{self.cream_raw}'"],
                   self.new_spawns(), [self.spawned('metadata_received', self.cream_id, self.cream_raw, self.downloads)])

    def case_metadata_received_prefetch(self):
        # a magnet's prefetch torrent, added and removed by Deluge beside the session's torrent list
        self.core.on_metadata_received(FakeHandleAlert('metadata_received', FakeHandle(self.stranger_id),
                                                       'the.stranger.2026'))
        self.judge('a torrent not in the session is one line more and runs nothing', self.new_lines(),
                   [f"metadata_received id {self.stranger_id} name 'the.stranger.2026'",
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
                    f"metadata_received id {zeros} name '{self.cream_raw}'",
                    f'no torrent {zeros} in the session for metadata_received, nothing run'],
                   self.new_spawns(), [],
                   ('raised out', raised, None))
        self.torrent_manager.torrents.pop(self.cream_id, None)

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
        self.judge('disable deregisters all thirteen', self.new_lines(), ['disabled'], self.new_spawns(), [],
                   ('event handlers', self.event_manager.handlers, []),
                   ('alert handlers', self.alert_manager.handlers, []))

    florist_id = '0123456789abcdef0123456789abcdef01234567'
    stranger_id = 'fedcba9876543210fedcba9876543210fedcba98'
    killer_id = '89abcdef0123456789abcdef0123456789abcdef'
    cream_id = 'c0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ff'
    cream_raw = 'Ice.Cream.Man.2026.1080p.WEBRip.x265'
    cream_folder = 'ice.cream.man.2026'
    movin = '/ocean/video/movies/movin'
    downloads = '/deluge/downloads'

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
        self.case_storage_moved()
        self.case_storage_moved_failed()
        self.case_folder_renamed()
        self.case_file_renamed()
        self.case_file_rename_failed()
        self.case_handle_gone()
        self.case_command_ends()
        self.case_disable()
        print('ALL AS EXPECTED' if self.all_as_expected else 'NOT ALL AS EXPECTED')
        return 0 if self.all_as_expected else 1


def main():
    testor = Testor()
    raise SystemExit(testor.executize())


if __name__ == '__main__':
    main()
