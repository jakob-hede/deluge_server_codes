#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
import logging
import shutil
import sys
import tempfile
import time
import types
from collections.abc import Callable
from pathlib import Path

import ntfying.libs.emitting as emitting_module
import oceanin.oceanic_hook as oceanic_hook_module
from executin.logge import TestLoggor
from oceanin.oceanic_hook import OceanicHook


class RecordingNtfyAnnouncor:
    """Stands in for ntfying's announcor under the hook's real HookAnnouncor: each card is recorded, none is sent."""

    cards: list[dict] = []

    def __init__(self):
        super().__init__()
        self.failure = None

    def announce(self, message, *, title=None, tags=(), priority=None, markdown=False, **kwargs):
        self.cards.append({'title': title, 'lines': message.split('\n'), 'tags': list(tags),
                           'priority': priority.value if priority else None, 'markdown': markdown})
        return f'stub{len(self.cards)}'


class RecordingJellyfinCommunicator:
    """Stands in for the Jellyfin communicator, so neither requests nor the secrets load: each path told is recorded."""

    told: list[str] = []
    is_refusing: bool = False

    def report_media_deleted(self, path: str) -> None:
        if self.is_refusing:
            raise ConnectionError('refused on purpose')
        self.told.append(path)


class LineRecordor(logging.Handler):
    """Records every line the loggor is given, so a case reads what the hook said."""

    def __init__(self):
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


class Testor:
    # what Jellyfin, the sidecars and a ticked delete leave behind in a movie folder
    leftovers: list[str] = ['backdrop.jpg', 'folder.jpg', 'landscape.jpg', 'logo.png', 'movie.nfo', 'provenance.yml',
                            'Subs/English.srt']
    torrent_id = '0123456789abcdef0123456789abcdef01234567'

    def __init__(self):
        super().__init__()
        self.loggor = TestLoggor()
        self.recordor = LineRecordor()
        self.loggor.addHandler(self.recordor)
        self.base: Path = Path()
        self.movies: Path = Path()
        self.libraries: tuple[Path, ...] = ()
        self.all_as_expected = True
        # what the stand-ins saw in the case at hand
        self.scanned: list[Path] = []
        self.slept: list[float] = []
        self.rglob_raises_for: Path | None = None

    @property
    def movin(self) -> Path:
        return self.libraries[0]

    def lay_out(self, folder: Path, paths: list[str], click: dict | None = None) -> Path:
        for path in paths:
            file = folder / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b'magnetics')
        if click is not None:
            lines = [f'  {key}: {value}' for key, value in click.items()]
            (folder / 'provenance.yml').write_text('\n'.join(['click:', *lines, '']))
        return folder

    def hook(self, torrent_name: str, location: Path) -> OceanicHook:
        return OceanicHook(self.torrent_id, torrent_name, str(location), self.loggor)

    def shown(self, path: Path | None) -> str:
        return 'None' if path is None else str(path.relative_to(self.base)) if path.is_relative_to(self.base) else str(path)

    def judge(self, hook: OceanicHook, event: str, error: str | None, *, branch: str, result: bool,
              exists: dict[Path, bool], outcome: str | None, leftovers: int | None = None,
              diversions: tuple[str, ...] = (), told: tuple[Path, ...] = (), card: dict | None = None,
              scans: int = 0, drive: Callable[[], bool | None] | None = None):
        """card: the expected title, first line, tags and priority, None for no card; a card ends with the hash unless
        the case names its last line."""
        location = Path(hook.base_sdir)
        candidate = location / hook.torrent_name
        was_dir = candidate.is_dir()
        folders: list[Path | None] = []
        real_payload_folder = hook.payload_folder

        def payload_folder(libraries=None):
            folder = real_payload_folder(libraries)
            folders.append(folder)
            return folder

        hook.payload_folder = payload_folder
        RecordingNtfyAnnouncor.cards.clear()
        RecordingJellyfinCommunicator.told.clear()
        self.scanned.clear()
        self.slept.clear()

        drive = drive or (lambda: hook.clean_payload(event, error, libraries=self.libraries))
        got = drive()

        # the branch step 1 took: the folder torrent, its folder gone from a library, or none
        found = folders[0] if folders else None
        if not folders:
            got_branch = 'not asked'
        elif found is None:
            got_branch = 'no folder'
        elif was_dir:
            got_branch = 'folder torrent'
        else:
            got_branch = 'gone in a library'
        is_as_expected = got == result and got_branch == branch
        print(f"result: {got}  expected {result}")
        print(f"branch: {got_branch}  expected {branch}  (folder {self.shown(found)})")
        for path, expected_exists in exists.items():
            is_there = path.exists() or path.is_symlink()
            is_as_expected = is_as_expected and is_there == expected_exists
            print(f"exists '{self.shown(path)}': {is_there}  expected {expected_exists}")
        got_diversions = hook._announcor.diversions if hook._announcor is not None else []
        print(f"outcome: {hook.remove_outcome!r}  expected {outcome!r}")
        print(f"leftovers: {hook.remove_leftovers}  expected {leftovers}")
        print(f"diversions: {got_diversions}  expected {list(diversions)}")
        got_told = list(RecordingJellyfinCommunicator.told)
        expected_told = [str(path) for path in told]
        print(f"jellyfin told: {[self.shown(Path(path)) for path in got_told]}  expected {[self.shown(path) for path in told]}")
        folder_scans = sum(1 for path in self.scanned if found is not None and path == found)
        print(f"scans of the folder: {folder_scans}  expected {scans}; sleeps: {len(self.slept)}  expected 0")
        is_as_expected = (is_as_expected
                          and hook.remove_outcome == outcome
                          and hook.remove_leftovers == leftovers
                          and got_diversions == list(diversions)
                          and got_told == expected_told
                          and folder_scans == scans
                          and not self.slept)
        cards = RecordingNtfyAnnouncor.cards
        if card is None:
            print(f"cards: {len(cards)}  expected 0")
            is_as_expected = is_as_expected and not cards
        else:
            expected_card = {'last line': f'hash **{self.torrent_id}**', **card, 'markdown': True}
            got_card = ({'title': cards[0]['title'], 'first line': cards[0]['lines'][0], 'tags': cards[0]['tags'],
                         'priority': cards[0]['priority'], 'last line': cards[0]['lines'][-1],
                         'markdown': cards[0]['markdown']} if len(cards) == 1 else {'cards': len(cards)})
            for key, expected_value in expected_card.items():
                print(f"card {key}: {got_card.get(key)!r}  expected {expected_value!r}")
            is_as_expected = is_as_expected and got_card == expected_card
        print(f"as expected: {is_as_expected}")
        self.all_as_expected = self.all_as_expected and is_as_expected

    # --- the folder torrent, which a rename-wrapped bare file is too

    def case_leftovers_only(self):
        folder = self.lay_out(self.movin / 'the.florist.2026', self.leftovers,
                              click={'media_title': 'The Florist', 'media_year': 2026, 'media_type': 'movie'})
        self.judge(self.hook('the.florist.2026', self.movin), 'oce_delete_failed', 'Directory not empty',
                   branch='folder torrent', result=True, exists={folder: False, self.movin: True},
                   outcome='deleted with 7 files', leftovers=7, told=(folder,), scans=1,
                   card={'title': 'DELETED: The Florist (2026)', 'first line': 'deleted with 7 files, jellyfin told',
                         'tags': ['wastebasket'], 'priority': None})

    def case_video_at_root(self):
        folder = self.lay_out(self.movin / 'the.florist.2026', self.leftovers + ['the.florist.2026.mkv'])
        self.judge(self.hook('the.florist.2026', self.movin), 'oce_delete_failed', 'Directory not empty',
                   branch='folder torrent', result=False, exists={folder / 'the.florist.2026.mkv': True},
                   outcome='kept: video still present, **the.florist.2026.mkv**', scans=1,
                   card={'title': 'DELETED: the florist 2026',
                         'first line': 'kept: video still present, **the.florist.2026.mkv**',
                         'tags': ['wastebasket', 'warning', 'diverted'], 'priority': 'high'})

    def case_video_in_subs(self):
        folder = self.lay_out(self.movin / 'the.florist.2026', self.leftovers + ['Subs/clip.MKV'])
        self.judge(self.hook('the.florist.2026', self.movin), 'oce_delete_failed', 'Directory not empty',
                   branch='folder torrent', result=False, exists={folder: True},
                   outcome='kept: video still present, **Subs/clip.MKV**', scans=1,
                   card={'title': 'DELETED: the florist 2026', 'first line': 'kept: video still present, **Subs/clip.MKV**',
                         'tags': ['wastebasket', 'warning', 'diverted'], 'priority': 'high'})

    def case_rename_wrapped_bare_file(self):
        # the rename step made the bare file wrapper/file inside the torrent, so the daemon names it by the wrapper
        folder = self.lay_out(self.movin / 'the.kings.warden.2026', self.leftovers,
                              click={'media_title': 'The Kings Warden', 'media_year': 2026, 'media_type': 'movie'})
        self.judge(self.hook('the.kings.warden.2026', self.movin), 'oce_delete_failed', 'Directory not empty',
                   branch='folder torrent', result=True, exists={folder: False},
                   outcome='deleted with 7 files', leftovers=7, told=(folder,), scans=1,
                   card={'title': 'DELETED: The Kings Warden (2026)',
                         'first line': 'deleted with 7 files, jellyfin told', 'tags': ['wastebasket'], 'priority': None})

    def case_folder_gone_with_the_delete(self):
        folder = self.movin / 'the.florist.2026'
        self.judge(self.hook('the.florist.2026', self.movin), 'oce_deleted', None,
                   branch='gone in a library', result=True, exists={folder: False, self.movin: True},
                   outcome='gone with the delete', told=(folder,), scans=0,
                   card={'title': 'DELETED: the florist 2026', 'first line': 'gone with the delete, jellyfin told',
                         'tags': ['wastebasket'], 'priority': None})

    def case_double_wrapped(self):
        parent = self.movin / 'moonrise.kingdom.2012'
        folder = self.lay_out(parent / 'Moonrise Kingdom (2012) Criterion (2160p)', self.leftovers)
        self.judge(self.hook('Moonrise Kingdom (2012) Criterion (2160p)', parent), 'oce_delete_failed',
                   'Directory not empty', branch='folder torrent', result=True, exists={folder: False, parent: True},
                   outcome='deleted with 7 files', leftovers=7, told=(folder,), scans=1,
                   diversions=("parent **moonrise.kingdom.2012/** holds no video, left for the operator's hand",),
                   card={'title': 'DELETED: Moonrise Kingdom (2012) Criterion (2160p)',
                         'first line': 'deleted with 7 files, jellyfin told',
                         'tags': ['wastebasket', 'warning', 'diverted'], 'priority': 'high'})

    def case_inner_symlink_to_outside_video(self):
        outside = self.lay_out(self.base / 'outside', ['other.mkv'])
        folder = self.lay_out(self.movin / 'the.florist.2026', self.leftovers)
        (folder / 'linked').symlink_to(outside, target_is_directory=True)
        self.judge(self.hook('the.florist.2026', self.movin), 'oce_delete_failed', 'Directory not empty',
                   branch='folder torrent', result=True, exists={folder: False, outside / 'other.mkv': True},
                   outcome='deleted with 8 files', leftovers=8, told=(folder,), scans=1,
                   card={'title': 'DELETED: the florist 2026', 'first line': 'deleted with 8 files, jellyfin told',
                         'tags': ['wastebasket'], 'priority': None})

    def case_another_library(self):
        # kidstuff is a Jellyfin movie library the hook leaves to other avenues of deletion
        kidstuff = self.movies / 'kidstuff'
        folder = self.lay_out(kidstuff / 'the.gruffalo.2009', self.leftovers)
        self.judge(self.hook('the.gruffalo.2009', kidstuff), 'oce_delete_failed', 'Directory not empty',
                   branch='folder torrent', result=False, exists={folder: True, folder / 'movie.nfo': True},
                   outcome='refused: its download location is outside the library movin')

    def case_permission_denied_video_present(self):
        folder = self.lay_out(self.movin / 'the.florist.2026', self.leftovers + ['the.florist.2026.mkv'])
        self.judge(self.hook('the.florist.2026', self.movin), 'oce_delete_failed', 'Permission denied',
                   branch='folder torrent', result=False, exists={folder / 'the.florist.2026.mkv': True},
                   outcome='kept: video still present, **the.florist.2026.mkv**', scans=1,
                   diversions=('the delete failed: **Permission denied**',),
                   card={'title': 'DELETED: the florist 2026',
                         'first line': 'kept: video still present, **the.florist.2026.mkv**',
                         'tags': ['wastebasket', 'warning', 'diverted'], 'priority': 'high'})

    def case_jellyfin_refuses(self):
        folder = self.lay_out(self.movin / 'the.florist.2026', self.leftovers)
        RecordingJellyfinCommunicator.is_refusing = True
        try:
            self.judge(self.hook('the.florist.2026', self.movin), 'oce_delete_failed', 'Directory not empty',
                       branch='folder torrent', result=True, exists={folder: False},
                       outcome='deleted with 7 files', leftovers=7, scans=1,
                       diversions=('jellyfin not told: **ConnectionError: refused on purpose**',),
                       card={'title': 'DELETED: the florist 2026',
                             'first line': 'deleted with 7 files, jellyfin not told: call failed',
                             'tags': ['wastebasket', 'warning', 'diverted'], 'priority': 'high'})
        finally:
            RecordingJellyfinCommunicator.is_refusing = False

    def case_deletion_fails(self):
        folder = self.lay_out(self.movin / 'the.florist.2026', self.leftovers)

        # stands in for a deletion the filesystem refuses half way, whoever runs the testor
        def failing_rmtree(path, *args, **kwargs):
            raise PermissionError(13, 'Permission denied', str(Path(path) / 'Subs'))

        # the hook imports shutil when it removes, so the stand-in goes on the module it will find
        real_rmtree = shutil.rmtree
        shutil.rmtree = failing_rmtree
        try:
            error = f"error: **[Errno 13] Permission denied: '{folder / 'Subs'}'**"
            self.judge(self.hook('the.florist.2026', self.movin), 'oce_delete_failed', 'Directory not empty',
                       branch='folder torrent', result=False, exists={folder: True}, outcome=error, scans=1,
                       diversions=("deletion failed, **the.florist.2026/** left for the operator's hand",),
                       card={'title': 'DELETED: the florist 2026', 'first line': error,
                             'tags': ['wastebasket', 'warning', 'diverted'], 'priority': 'high'})
        finally:
            shutil.rmtree = real_rmtree

    # --- the refusals: a log line, no card, nothing told

    def case_library_itself(self):
        self.lay_out(self.movin, self.leftovers)
        self.judge(self.hook('movin', self.movies), 'oce_delete_failed', 'Directory not empty',
                   branch='folder torrent', result=False, exists={self.movin / 'movie.nfo': True},
                   outcome='refused: it is the library itself')

    def case_outside_libraries(self):
        folder = self.lay_out(self.base / 'elsewhere' / 'the.florist.2026', self.leftovers)
        self.judge(self.hook('the.florist.2026', folder.parent), 'oce_delete_failed', 'Directory not empty',
                   branch='folder torrent', result=False, exists={folder: True},
                   outcome='refused: its download location is outside the library movin')

    def case_tv_episode_outside(self):
        season = self.base / 'tv' / 'tulsa.king' / 's04'
        folder = self.lay_out(season / 'Tulsa.King.S04E01.1080p.x265-ELiTE',
                              ['Tulsa.King.S04E01.1080p.x265-ELiTE-thumb.jpg', 'Tulsa.King.S04E01.1080p.x265-ELiTE.nfo',
                               'Tulsa.King.S04E01.1080p.x265-ELiTE.en.srt'])
        hook = self.hook('Tulsa.King.S04E01.1080p.x265-ELiTE', season)
        self.judge(hook, 'oce_delete_failed', 'Directory not empty', branch='folder torrent', result=False,
                   exists={folder: True}, outcome='refused: its download location is outside the library movin')
        is_quiet = hook._announcor is None
        print(f"the voice never loaded: {is_quiet}  expected True")
        self.all_as_expected = self.all_as_expected and is_quiet

    def case_no_folder_outside(self):
        season = self.base / 'tv' / 'tulsa.king' / 's04'
        season.mkdir(parents=True)
        self.judge(self.hook('Tulsa.King.S04E02.1080p.x265-ELiTE', season), 'oce_deleted', None,
                   branch='no folder', result=False, exists={season: True},
                   outcome=f'refused: it is gone, and its location **{season}** is not the library movin')

    def case_year_folder_gone(self):
        # instream nests its movies in year folders, so a folder torrent there is located in the year folder
        year = self.movies / 'instream' / '2020'
        other = self.lay_out(year / 'tenet.2020', self.leftovers + ['tenet.2020.mkv'])
        self.judge(self.hook('the.florist.2020', year), 'oce_deleted', None,
                   branch='no folder', result=False, exists={year: True, other / 'tenet.2020.mkv': True,
                                                             other / 'movie.nfo': True},
                   outcome=f'refused: it is gone, and its location **{year}** is not the library movin')

    def case_collection_folder_gone(self):
        # structured_movies nests its movies in collection folders; the collection holds another movie's video
        collection = self.movies / 'structured_movies' / 'godfather'
        other = self.lay_out(collection / 'the.godfather.1972', self.leftovers + ['the.godfather.1972.mkv'])
        self.judge(self.hook('the.godfather.part.ii.1974', collection), 'oce_deleted', None,
                   branch='no folder', result=False, exists={collection: True, other / 'the.godfather.1972.mkv': True,
                                                             other / 'movie.nfo': True},
                   outcome=f'refused: it is gone, and its location **{collection}** is not the library movin')

    def case_double_wrapped_inner_gone(self):
        # the inner folder went with the delete, so the outer is the location: refused, left for the operator's hand
        parent = self.lay_out(self.movin / 'moonrise.kingdom.2012', ['folder.jpg', 'movie.nfo'])
        self.judge(self.hook('Moonrise Kingdom (2012) Criterion (2160p)', parent), 'oce_deleted', None,
                   branch='no folder', result=False, exists={parent: True, parent / 'movie.nfo': True},
                   outcome=f'refused: it is gone, and its location **{parent}** is not the library movin')

    def case_file_in_library_itself(self):
        file = self.lay_out(self.movin, ['the.florist.2026.mkv']) / 'the.florist.2026.mkv'
        self.judge(self.hook('the.florist.2026.mkv', self.movin), 'oce_delete_failed', 'Permission denied',
                   branch='no folder', result=False, exists={file: True}, outcome='refused: it is not a folder')

    def case_symlink_to_outside(self):
        outside = self.lay_out(self.base / 'outside' / 'the.florist.2026', self.leftovers)
        folder = self.movin / 'the.florist.2026'
        folder.symlink_to(outside, target_is_directory=True)
        self.judge(self.hook('the.florist.2026', self.movin), 'oce_delete_failed', 'Directory not empty',
                   branch='folder torrent', result=False, exists={folder: True, outside / 'movie.nfo': True},
                   outcome='refused: it is a symlink')

    def case_climbing_path(self):
        self.lay_out(self.movin / 'the.florist.2026', self.leftovers)
        (self.base / 'downloads').mkdir()
        location = self.base / 'downloads' / '..' / 'movies' / 'movin'
        self.judge(self.hook('the.florist.2026', location), 'oce_delete_failed', 'Directory not empty',
                   branch='folder torrent', result=False, exists={self.movin / 'the.florist.2026': True},
                   outcome='refused: its path climbs with **..**')

    # --- the plain remove, and a death

    def case_removed(self):
        folder = self.lay_out(self.movin / 'the.florist.2026', self.leftovers + ['the.florist.2026.mkv'])
        hook = self.hook('the.florist.2026', self.movin)
        self.judge(hook, 'oce_removed', None, branch='not asked', result=True, exists={folder: True}, outcome=None,
                   drive=lambda: hook.process_event('oce_removed'))
        is_quiet = hook._announcor is None
        print(f"the voice never loaded: {is_quiet}  expected True")
        self.all_as_expected = self.all_as_expected and is_quiet

    def case_logging(self, event_name: str, *details: str):
        # a hearing that only logs, the completion chain's material: one line with every detail, True, the disk
        # untouched, no voice and no Torrentor
        folder = self.lay_out(self.movin / 'the.florist.2026', self.leftovers + ['the.florist.2026.mkv'])
        hook = self.hook('the.florist.2026', self.movin)
        self.recordor.lines.clear()
        self.judge(hook, event_name, None, branch='not asked', result=True, exists={folder: True}, outcome=None,
                   drive=lambda: hook.process_event(event_name, *details))
        expected_lines = [f"Torrent 'the.florist.2026' {event_name}, id '{self.torrent_id}', location '{self.movin}', "
                          f"details {list(details)}"]
        is_said = self.recordor.lines == expected_lines
        print(f"lines: {self.recordor.lines}")
        print(f"expected: {expected_lines}")
        print(f"lines as expected: {is_said}")
        is_quiet = hook._announcor is None
        print(f"the voice never loaded: {is_quiet}  expected True")
        is_light = hook._torrentor is None
        print(f"the Torrentor never loaded: {is_light}  expected True")
        self.all_as_expected = self.all_as_expected and is_said and is_quiet and is_light

    def case_scan_raises(self):
        folder = self.lay_out(self.movin / 'the.florist.2026', self.leftovers)
        hook = self.hook('the.florist.2026', self.movin)
        self.rglob_raises_for = folder
        raised: list[BaseException] = []

        def drive():
            try:
                return hook.clean_payload('oce_delete_failed', 'Directory not empty', libraries=self.libraries)
            except PermissionError as exc:
                raised.append(exc)
                return None

        failed_line = 'at **scan**: **PermissionError: [Errno 13] scan refused on purpose**'
        try:
            self.judge(hook, 'oce_delete_failed', 'Directory not empty', branch='folder torrent', result=None,
                       exists={folder: True}, outcome=None, scans=1, drive=drive,
                       card={'title': 'FAILED: the florist 2026', 'first line': failed_line, 'last line': failed_line,
                             'tags': ['x'], 'priority': 'high'})
        finally:
            self.rglob_raises_for = None
        print(f"raised on: {[type(exc).__name__ for exc in raised]}  expected ['PermissionError']")
        self.all_as_expected = self.all_as_expected and len(raised) == 1

    def executize(self):
        print("Testor.executize...")
        # nothing in the hook waits, and shutil's compression modules load only when a folder is removed
        for name in ('sleep', 'shutil'):
            is_imported = hasattr(oceanic_hook_module, name)
            print(f"the hook module imports {name} at load: {is_imported}  expected False")
            self.all_as_expected = self.all_as_expected and not is_imported
        cases = [
            ('the folder torrent: leftovers only, one scan, no wait, deleted', self.case_leftovers_only),
            ('the folder torrent: a video at the root, one scan, no wait, kept', self.case_video_at_root),
            ('the folder torrent: a video only inside Subs/, kept', self.case_video_in_subs),
            ('the folder torrent: a rename-wrapped bare file, the file gone, the leftovers there',
             self.case_rename_wrapped_bare_file),
            ('the folder torrent: the folder gone with the delete, oce_deleted', self.case_folder_gone_with_the_delete),
            ('the folder torrent: the double-wrapped shape, the inner folder emptied', self.case_double_wrapped),
            ('the folder torrent: leftovers and a symlink to a folder outside holding a video',
             self.case_inner_symlink_to_outside_video),
            ("refused: a folder torrent in kidstuff, a Jellyfin library not the hook's", self.case_another_library),
            ('the folder torrent: Permission denied on oce_delete_failed, the video there',
             self.case_permission_denied_video_present),
            ('the folder torrent: the Jellyfin call raises', self.case_jellyfin_refuses),
            ('the folder torrent: the deletion fails', self.case_deletion_fails),
            ('refused: the library itself', self.case_library_itself),
            ('refused: a folder outside the library', self.case_outside_libraries),
            ('refused: a TV episode folder, outside the library', self.case_tv_episode_outside),
            ('refused: no folder, and a location outside the library', self.case_no_folder_outside),
            ('refused: a folder torrent in an instream year folder, its folder gone', self.case_year_folder_gone),
            ('refused: a folder torrent in a structured_movies collection holding another movie, its folder gone',
             self.case_collection_folder_gone),
            ('refused: the double-wrapped shape, the inner folder gone with the delete', self.case_double_wrapped_inner_gone),
            ('refused: a file under a location that is the library itself', self.case_file_in_library_itself),
            ('refused: a symlink in the library to a folder outside', self.case_symlink_to_outside),
            ('refused: a path climbing into the library with ..', self.case_climbing_path),
            ('oce_removed: one log line, nothing read, no voice', self.case_removed),
            ('a death: the scan raises, the FAILED card at its stage, raised on', self.case_scan_raises),
            ('logs only: oce_finished, no detail', lambda: self.case_logging('oce_finished')),
            ("logs only: oce_torrent_finished, libtorrent's raw finish, no detail",
             lambda: self.case_logging('oce_torrent_finished')),
            ('logs only: oce_folder_renamed, the old name and the new',
             lambda: self.case_logging('oce_folder_renamed', 'The.Florist.2026.1080p/', 'the.florist.2026/')),
            ('logs only: oce_file_renamed, the index and the new name',
             lambda: self.case_logging('oce_file_renamed', '0', 'the.florist.2026/the.florist.2026.mkv')),
            ('logs only: oce_storage_moved, the new path',
             lambda: self.case_logging('oce_storage_moved', str(self.movin))),
            ("logs only: oce_storage_moved_failed, the error's text and the file's path",
             lambda: self.case_logging('oce_storage_moved_failed', 'Permission denied',
                                       str(self.movin / 'the.florist.2026' / 'the.florist.2026.mkv'))),
            ("logs only: oce_file_rename_failed, the index and the error's text",
             lambda: self.case_logging('oce_file_rename_failed', '1', 'File exists')),
        ]
        real_rglob = Path.rglob
        real_sleep = time.sleep

        def rglob(path, pattern, *args, **kwargs):
            self.scanned.append(path)
            if path == self.rglob_raises_for:
                raise PermissionError(13, 'scan refused on purpose')
            return real_rglob(path, pattern, *args, **kwargs)

        Path.rglob = rglob
        time.sleep = self.slept.append
        try:
            for case_name, case in cases:
                print(f"--- {case_name}")
                with tempfile.TemporaryDirectory(prefix='test_oceanic_delete_') as temp_dir:
                    self.base = Path(temp_dir)
                    self.movies = self.base / 'movies'
                    # the four movie folders Jellyfin lists, of which the hook's library is movin alone
                    for name in ('movin', 'instream', 'kidstuff', 'structured_movies'):
                        (self.movies / name).mkdir(parents=True)
                    self.libraries = (self.movies / 'movin',)
                    case()
        finally:
            Path.rglob = real_rglob
            time.sleep = real_sleep
        print('ALL AS EXPECTED' if self.all_as_expected else 'NOT ALL AS EXPECTED')


def main():
    # the stand-ins go in before the hook imports either, so nothing is sent and no secret is loaded
    emitting_module.NtfyAnnouncor = RecordingNtfyAnnouncor
    communicator_module = types.ModuleType('executin.jellyfin_communicator')
    communicator_module.JellyfinCommunicator = RecordingJellyfinCommunicator
    sys.modules['executin.jellyfin_communicator'] = communicator_module
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
