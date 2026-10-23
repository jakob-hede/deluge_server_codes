#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
import copy
import logging
import tempfile
from collections.abc import Callable
from pathlib import Path

import ntfying.libs.emitting as emitting_module
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
                           'priority': priority.value if priority else None})
        return f'stub{len(self.cards)}'


class LineRecordor(logging.Handler):
    """Records every line the loggor is given with its level, so a step reads what the hook said."""

    def __init__(self):
        super().__init__()
        self.lines: list[tuple[str, str]] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append((record.levelname, record.getMessage()))


class FakeDaemon:
    """Stands in for deluged: one torrent's status as the daemon reports it, and every act asked of it recorded. What
    an act does to the torrent the testor does by hand, as Deluge and libtorrent would, before it fires the event."""

    def __init__(self, torrent_id: str, name: str, files: list[dict], location: str, label: str, total_wanted: int):
        super().__init__()
        self.torrent_id = torrent_id
        self.name = name
        self.files = files
        self.orig_files = copy.deepcopy(files)
        self.location = location
        self.label = label
        self.total_wanted = total_wanted
        self.is_present = True
        self.acts: list[tuple] = []
        self.failing_act: str | None = None  # the transaction class whose dispatch the daemon refuses

    def answer(self, transaction) -> object:
        kind = type(transaction).__name__
        if kind == 'DelugApiStatusTransaction':
            status = {'hash': self.torrent_id, 'name': self.name, 'files': copy.deepcopy(self.files),
                      'orig_files': copy.deepcopy(self.orig_files), 'download_location': self.location,
                      'save_path': self.location, 'move_completed_path': '/deluge/completed/', 'label': self.label,
                      'total_wanted': self.total_wanted}
            transaction.response.result = {self.torrent_id: status} if self.is_present else {}
            return transaction.response.result
        if kind == 'DelugApiMoveTransaction':
            act = ('move', transaction.destination)
        elif kind == 'DelugApiRenameFolderTransaction':
            act = ('rename_folder', transaction.folder, transaction.new_folder)
        else:
            act = ('rename_files', list(transaction.filenames))
        self.acts.append(act)
        if kind == self.failing_act:
            transaction.response.error = 'refused on purpose'
        return None

    # --- what Deluge and libtorrent do with the acts, by hand

    def moved(self, destination: Path) -> None:
        # Deluge's own storage_moved handler sets the location; move_storage made the folder
        destination.mkdir(parents=True, exist_ok=True)
        self.location = str(destination)

    def folder_renamed(self, folder: str, new_folder: str) -> None:
        for file in self.files:
            if file['path'].startswith(folder):
                file['path'] = new_folder + file['path'][len(folder):]
        self.renamed()

    def file_renamed(self, index: int, path: str) -> None:
        next(file for file in self.files if file['index'] == index)['path'] = path
        self.renamed()

    def renamed(self) -> None:
        # Deluge names a torrent by its first file's top folder, so a wrap or a folder rename renames the torrent
        first = self.files[0]['path']
        if '/' in first:
            self.name = first.split('/', 1)[0]


class Testor:
    torrent_id = 'f10215f10215f10215f10215f10215f10215f102'
    completed = '/deluge/completed/'
    yts_folder = 'The Florist (2026) [1080p] [YTS.GG]'
    record = {'infohash': torrent_id, 'media_title': 'The Florist', 'media_year': 2026, 'media_type': 'movie',
              'imdb_id': 'tt0000001', 'site': 'yts', 'label_hint': 'movin'}

    def __init__(self, classes: dict[str, type]):
        super().__init__()
        self.classes = classes
        self.loggor = TestLoggor()
        self.recordor = LineRecordor()
        self.loggor.addHandler(self.recordor)
        self.base: Path = Path()
        self.daemon: FakeDaemon | None = None
        self.refreshes: list[tuple[str, str]] = []
        self.is_refresh_raising = False
        self.all_as_expected = True
        self.steps = 0

    # --- the case's tree, under the temporary directory, where the box's paths would be

    @property
    def video(self) -> Path:
        return self.base / 'ocean' / 'video'

    @property
    def movin(self) -> Path:
        return self.video / 'movies' / 'movin'

    @property
    def staging(self) -> Path:
        return self.video / '.staging' / self.torrent_id

    @property
    def stage_file(self) -> Path:
        return self.base / 'deluge' / 'staging' / self.torrent_id / 'stage.yml'

    def lay_out(self, base: Path) -> None:
        self.base = base
        torrentor_class = self.classes['Torrentor']
        torrentor_class.torrents_dir = base / 'deluge' / 'torrents'
        torrentor_class.surveys_dir = base / 'deluge' / 'surveys'
        torrentor_class.browser_source_dir = base / 'deluge' / 'browser-source'
        self.classes['TorrentHandlorMovin']._destin_dir = self.movin
        self.classes['TorrentHandlorTvin']._destin_dir = self.video / 'tv' / '_tvin'
        OceanicHook.staging_root = self.video / '.staging'
        RecordingNtfyAnnouncor.cards.clear()
        self.refreshes.clear()
        self.is_refresh_raising = False

    def torrentize(self, release: str, paths: list[str]) -> None:
        # the daemon's copy of the release, its files as the paths name them, so the survey has the shape
        import libtorrent as lt

        content = self.base / 'content'
        for path in paths:
            file = content / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b'magnetics' * 1000)
        file_storage = lt.file_storage()
        # a bare file is a one-file torrent, its survey single_file; anything under a folder a folder torrent
        lt.add_files(file_storage, str(content / paths[0].split('/', 1)[0]))
        creator = lt.create_torrent(file_storage)
        lt.set_piece_hashes(creator, str(content))
        torrents_dir = self.base / 'deluge' / 'torrents'
        torrents_dir.mkdir(parents=True, exist_ok=True)
        (torrents_dir / f'{release}.torrent').write_bytes(lt.bencode(creator.generate()))

    def lay_record(self, record: dict, record_id: str | None = None) -> None:
        import yaml

        record_dir = self.base / 'deluge' / 'browser-source'
        record_dir.mkdir(parents=True, exist_ok=True)
        (record_dir / f'{record_id or self.torrent_id}.yml').write_text(yaml.safe_dump(record))

    def yts_daemon(self, label: str = 'movin', is_recorded: bool = True) -> FakeDaemon:
        # a yts folder release, as Deluge's move_completed left it in completed/, by default with its click's record
        files = [{'index': 0, 'path': f'{self.yts_folder}/The.Florist.2026.1080p.WEBRip.x264.AAC-[YTS.GG].mp4',
                  'size': 1_900_000_000},
                 {'index': 1, 'path': f'{self.yts_folder}/Subs/English.srt', 'size': 80_000},
                 {'index': 2, 'path': f'{self.yts_folder}/www.YTS.GG.jpg', 'size': 50_000}]
        self.torrentize(self.yts_folder, [file['path'] for file in files])
        if is_recorded:
            self.lay_record(self.record)
        return FakeDaemon(self.torrent_id, self.yts_folder, files, self.completed, label, 1_900_000_000)

    # --- a step: one event fired as the runnor fires it, the stage, the acts, the cards and the lines judged

    def shown(self, text: object) -> str:
        return str(text).replace(str(self.base), '<tmp>')

    def step(self, title: str, event: str, *details: str, stage: str | None, acts: list[tuple] = (),
             card: dict | None = None, lines: list[str] | None = None, raises: str | None = None) -> None:
        """card: the one card the step sends, title, lines, tags and priority, None for none; lines: lines the hook's
        log must hold, in order, among its others; raises: the exception's type when the step must raise on."""
        self.steps += 1
        print(f'... {title}')
        daemon = self.daemon
        hook = OceanicHook(self.torrent_id, daemon.name, daemon.location, self.loggor)
        self.recordor.lines.clear()
        acts_before = len(daemon.acts)
        cards_before = len(RecordingNtfyAnnouncor.cards)
        raised = None
        try:
            hook.process_event(event, *details)
        except Exception as exc:
            raised = type(exc).__name__
        got_acts = [tuple(self.shown(part) for part in act) for act in daemon.acts[acts_before:]]
        expected_acts = [tuple(self.shown(part) for part in act) for act in acts]
        got_cards = RecordingNtfyAnnouncor.cards[cards_before:]
        got_stage = self.read_stage().get('stage')
        is_as_expected = got_stage == stage and got_acts == expected_acts and raised == raises
        print(f'stage: {got_stage}  expected {stage}')
        print(f'acts: {got_acts}  expected {expected_acts}')
        print(f'raised: {raised}  expected {raises}')
        if card is None:
            print(f'cards: {len(got_cards)}  expected 0')
            is_as_expected = is_as_expected and not got_cards
        else:
            got_card = ({key: [self.shown(line) for line in value] if key == 'lines' else value
                         for key, value in got_cards[0].items()} if len(got_cards) == 1 else {'cards': len(got_cards)})
            expected_card = {key: [self.shown(line) for line in value] if key == 'lines' else value
                             for key, value in card.items()}
            for key, expected_value in expected_card.items():
                print(f'card {key}: {got_card.get(key)!r}  expected {expected_value!r}')
            is_as_expected = is_as_expected and got_card == expected_card
        said = [self.shown(line) for _, line in self.recordor.lines]
        for line in lines or []:
            is_said = self.shown(line) in said
            print(f'said: {self.shown(line)!r}  {is_said}')
            is_as_expected = is_as_expected and is_said
        if self.stage_file.exists():
            print('stage.yml:')
            for line in self.shown(self.stage_file.read_text()).splitlines():
                print(f'  | {line}')
        print(f'as expected: {is_as_expected}')
        self.all_as_expected = self.all_as_expected and is_as_expected

    def read_stage(self) -> dict:
        import yaml

        return yaml.safe_load(self.stage_file.read_text()) if self.stage_file.exists() else {}

    def check(self, label: str, value: object, expected: object) -> None:
        is_as_expected = value == expected
        print(f'{label}: {self.shown(value)}  expected {self.shown(expected)}  {is_as_expected}')
        self.all_as_expected = self.all_as_expected and is_as_expected

    def completed_card(self, folder_line: str, *, destination: Path, refreshed: bool = True, diversions: tuple = (),
                       label: str = 'movin', size: str = '1.9 GB') -> dict:
        tags = ['white_check_mark', label] + (['warning', 'diverted'] if diversions else [])
        lines = [f'in **{destination}**', 'jellyfin refreshed' if refreshed else 'jellyfin not refreshed',
                 *(f'! {diversion}' for diversion in diversions), folder_line, 'staged via .staging', size,
                 f'hash **{self.torrent_id}**']
        return {'title': 'COMPLETED: The Florist (2026)' if label == 'movin' else None, 'lines': lines, 'tags': tags,
                'priority': 'high' if diversions else None}

    # --- the cases

    def case_yts_folder(self):
        # the common case, a yts folder: every link from its event, each re-fired once to show it a no-op
        daemon = self.daemon = self.yts_daemon()
        self.step('link 1, entered on the move into completed/: the survey written, the staging move',
                  'oce_storage_moved', self.completed, stage='staging', acts=[('move', self.staging)],
                  lines=["Survey of 'The Florist (2026) [1080p] [YTS.GG]' written on oce_storage_moved, "
                         f"'{self.base}/deluge/surveys/{self.torrent_id}.yml' from "
                         f"'{self.base}/deluge/torrents/{self.yts_folder}.torrent'"])
        self.step('link 1 re-fired: nothing', 'oce_storage_moved', self.completed, stage='staging')
        daemon.moved(self.staging)
        self.step('link 2, in staging: the folder rename', 'oce_storage_moved', str(self.staging), stage='renaming',
                  acts=[('rename_folder', f'{self.yts_folder}/', 'the.florist.2026/')])
        self.step('link 2 re-fired: nothing', 'oce_storage_moved', str(self.staging), stage='renaming')
        daemon.folder_renamed(f'{self.yts_folder}/', 'the.florist.2026/')
        file_plan = [(0, 'the.florist.2026/the.florist.2026.mp4'), (1, 'the.florist.2026/the.florist.2026.en.srt')]
        self.step('link 3, the folder renamed: the file renames', 'oce_folder_renamed', f'{self.yts_folder}/',
                  'the.florist.2026/', stage='renaming_files', acts=[('rename_files', file_plan)])
        self.step('link 3 re-fired: nothing', 'oce_folder_renamed', f'{self.yts_folder}/', 'the.florist.2026/',
                  stage='renaming_files')
        daemon.file_renamed(*file_plan[0])
        self.step('link 3, the first file renamed of two: counted, nothing more', 'oce_file_renamed', '0',
                  file_plan[0][1], stage='renaming_files',
                  lines=["Chain of 'the.florist.2026': file renames 1/2 done, the next event looks again"])
        daemon.file_renamed(*file_plan[1])
        self.step('link 3, the second: link 4, the sidecars and the move into movin', 'oce_file_renamed', '1',
                  file_plan[1][1], stage='moving', acts=[('move', self.movin)])
        folder = self.movin / 'the.florist.2026'
        self.check('sidecars in the destination before the media, movie.nfo at the root, no provenance.yml',
                   sorted(path.name for path in folder.iterdir()), ['.oceanmeta', 'movie.nfo'])
        self.check_oceanmeta(folder, hashes=[self.torrent_id])
        self.step('link 3 re-fired after the move: nothing', 'oce_file_renamed', '1', file_plan[1][1], stage='moving')
        daemon.moved(self.movin)
        self.step('link 5, in movin: the refresh, the staging folder removed, the card', 'oce_storage_moved',
                  str(self.movin), stage='done',
                  card=self.completed_card('renamed to **the.florist.2026/**', destination=self.movin))
        self.check('refreshes', self.refreshes, [('movin', str(self.movin))])
        self.check('the staging folder still there', self.staging.exists(), False)
        self.step('link 5 re-fired: nothing, no second card', 'oce_storage_moved', str(self.movin), stage='done')

    def case_unlabelled_then_the_hand(self):
        daemon = self.daemon = self.yts_daemon(label='')
        self.step('no label: stage unlabelled, one card naming where it is', 'oce_storage_moved', self.completed,
                  stage='unlabelled',
                  card={'title': 'COMPLETED: The Florist (2026)',
                        'lines': ['not moved: no label, in **/deluge/completed/**', 'jellyfin not refreshed',
                                  'as released: **The Florist (2026)/**', '1.9 GB', f'hash **{self.torrent_id}**'],
                        'tags': ['white_check_mark'], 'priority': None})
        daemon.label = 'movin'
        self.step("the hand's trigger, labelled and moved into completed/ again: entered", 'oce_storage_moved',
                  self.completed, stage='staging', acts=[('move', self.staging)])

    def case_label_without_handlor(self):
        self.daemon = self.yts_daemon(label='p')
        self.step('a label no handlor knows: stage unlabelled, one card naming it', 'oce_storage_moved',
                  self.completed, stage='unlabelled',
                  card={'title': 'COMPLETED: The Florist (2026)',
                        'lines': ['not moved: no handler for label **p**, in **/deluge/completed/**',
                                  'jellyfin not refreshed', 'as released: **The Florist (2026)/**', '1.9 GB',
                                  f'hash **{self.torrent_id}**'],
                        'tags': ['white_check_mark', 'p'], 'priority': None})

    # --- amendment 4: no card for a torrent that is not the chain's; failures on a chain torrent are cards

    def case_unlabelled_no_record(self):
        daemon = self.daemon = self.yts_daemon(label='', is_recorded=False)
        self.step('no label and no click record: not the chain\'s, one log line, stage unlabelled, no card',
                  'oce_storage_moved', self.completed, stage='unlabelled',
                  lines=[f"Chain of '{self.yts_folder}': no label, in '/deluge/completed/', no browser-source record, "
                         f"not the chain's, no card"])
        daemon.label = 'movin'
        self.step("the hand's trigger all the same: labelled and moved into completed/ again, entered",
                  'oce_storage_moved', self.completed, stage='staging', acts=[('move', self.staging)])

    def case_label_without_handlor_no_record(self):
        self.daemon = self.yts_daemon(label='p', is_recorded=False)
        self.step('a label no handlor knows and no click record: one log line, no card', 'oce_storage_moved',
                  self.completed, stage='unlabelled',
                  lines=[f"Chain of '{self.yts_folder}': no handler for label **p**, in '/deluge/completed/', no "
                         f"browser-source record, not the chain's, no card"])

    def case_unlabelled_by_alternate(self):
        # a hybrid the daemon filed under its v2: oce_added kept its v1, which names the click's record
        alternate = 'd1d96f75' * 5
        self.daemon = self.yts_daemon(label='', is_recorded=False)
        self.lay_record(self.record, alternate)
        self.classes['Stagor'](self.torrent_id).write(alternate_ids=[alternate])
        self.step("no label, the click's record found by the kept alternate: the card", 'oce_storage_moved',
                  self.completed, stage='unlabelled',
                  card={'title': 'COMPLETED: The Florist (2026)',
                        'lines': ['not moved: no label, in **/deluge/completed/**', 'jellyfin not refreshed',
                                  'as released: **The Florist (2026)/**', '1.9 GB', f'hash **{self.torrent_id}**'],
                        'tags': ['white_check_mark'], 'priority': None})

    def case_failures_on_a_chain_torrent(self):
        # a chain torrent in its library, done; a later storage move or rename the daemon fails is a card, the stage
        # kept as it stood
        self.daemon = self.yts_daemon()
        self.daemon.location = str(self.movin)
        self.classes['Stagor'](self.torrent_id).write(stage='done', entry='storage_moved', label='movin')
        self.step('a storage move failing for a torrent done: one FAILED card, high, the stage kept',
                  'oce_storage_moved_failed', 'Permission denied', stage='done',
                  card={'title': 'FAILED: The Florist (2026)',
                        'lines': ['at **done**: storage move failed: **Permission denied**', f'hash **{self.torrent_id}**'],
                        'tags': ['x', 'movin'], 'priority': 'high'})
        self.step('a rename failing for it: one FAILED card, the stage kept', 'oce_file_rename_failed', '0',
                  'File exists', stage='done',
                  card={'title': 'FAILED: The Florist (2026)',
                        'lines': ['at **done**: rename failed: **File exists**', f'hash **{self.torrent_id}**'],
                        'tags': ['x', 'movin'], 'priority': 'high'})

    def case_failures_not_the_chains(self):
        # no stage, or a hybrid left unhandled: a failure is a log line, no card
        self.daemon = self.yts_daemon()
        self.step('a storage move failing for a torrent with no stage: a log line', 'oce_storage_moved_failed',
                  'Permission denied', stage=None,
                  lines=[f"Chain of '{self.yts_folder}': oce_storage_moved_failed at stage 'none', nothing to do"])
        self.step('a rename failing for it: a log line', 'oce_file_rename_failed', '0', 'File exists', stage=None,
                  lines=[f"Chain of '{self.yts_folder}': oce_file_rename_failed at stage 'none', nothing to do"])
        self.classes['Stagor'](self.torrent_id).write(stage='unhandled', entry='metadata_received', deluge='missed')
        self.step('a failure for a hybrid left unhandled: a log line, it is left alone', 'oce_storage_moved_failed',
                  'Permission denied', stage='unhandled',
                  lines=[f"Chain of '{self.yts_folder}': oce_storage_moved_failed at stage 'unhandled', nothing to do"])

    def case_already_named(self):
        files = [{'index': 0, 'path': 'the.florist.2026/the.florist.2026.mp4', 'size': 1_900_000_000},
                 {'index': 1, 'path': 'the.florist.2026/the.florist.2026.en.srt', 'size': 80_000}]
        self.torrentize('the.florist.2026', [file['path'] for file in files])
        self.lay_record(self.record)
        daemon = self.daemon = FakeDaemon(self.torrent_id, 'the.florist.2026', files, self.completed, 'movin',
                                          1_900_000_000)
        self.step('entered', 'oce_storage_moved', self.completed, stage='staging', acts=[('move', self.staging)])
        daemon.moved(self.staging)
        self.step('arrived in its pattern folder, its files named: no rename, the move', 'oce_storage_moved',
                  str(self.staging), stage='moving', acts=[('move', self.movin)])
        daemon.moved(self.movin)
        self.step('in movin: the card says already', 'oce_storage_moved', str(self.movin), stage='done',
                  card=self.completed_card('already **the.florist.2026/**', destination=self.movin))

    def case_tv_no_rename(self):
        name = 'Tulsa.King.S04E01.1080p.x265-ELiTE'
        files = [{'index': 0, 'path': f'{name}.mkv', 'size': 900_000_000}]
        self.torrentize(name, [f'{name}/{name}.mkv'])
        daemon = self.daemon = FakeDaemon(self.torrent_id, name, files, self.completed, 'tv-in', 900_000_000)
        self.is_refresh_raising = True
        season = self.video / 'tv' / 'tulsa.king' / 's04'
        self.step('entered, a TV episode', 'oce_storage_moved', self.completed, stage='staging',
                  acts=[('move', self.staging)])
        daemon.moved(self.staging)
        self.step('in staging: no rename planned for TV, the move into its season, no sidecars', 'oce_storage_moved',
                  str(self.staging), stage='moving', acts=[('move', season)])
        daemon.moved(season)
        self.step('in its season: the refresh raises, noted; the card', 'oce_storage_moved', str(season),
                  stage='done',
                  card={'title': 'COMPLETED: Tulsa King S04E01 1080p x265-ELiTE',
                        'lines': [f'in **{season}**', 'jellyfin not refreshed',
                                  '! jellyfin refresh failed: **ConnectionError: refused on purpose**',
                                  'as released: **Tulsa King S04E01 1080p x265-ELiTE**', 'staged via .staging',
                                  '0.9 GB', f'hash **{self.torrent_id}**'],
                        'tags': ['white_check_mark', 'tv-in', 'warning', 'diverted'], 'priority': 'high'})
        self.check('the season folder holds the record and the survey, no movie.nfo',
                   sorted(path.name for path in season.iterdir()), ['.oceanmeta'])
        self.check_oceanmeta(season, hashes=[self.torrent_id], label='tv-in',
                             release_name='Tulsa.King.S04E01.1080p.x265-ELiTE')

    def case_bare_movie_wrapped(self):
        name = 'The.Florist.2026.1080p.WEB-DL.mkv'
        files = [{'index': 0, 'path': name, 'size': 1_900_000_000}]
        self.torrentize(name, [name])
        self.lay_record(self.record)
        daemon = self.daemon = FakeDaemon(self.torrent_id, name, files, self.completed, 'movin', 1_900_000_000)
        # a hybrid the daemon filed under its v2, its v1 kept from oce_added, which the record names beside the id
        alternate = 'd1d96f75' * 5
        self.classes['Stagor'](self.torrent_id).write(alternate_ids=[alternate])
        wrap = [(0, 'the.florist.2026/the.florist.2026.mkv')]
        self.step('entered, a bare movie file', 'oce_storage_moved', self.completed, stage='staging',
                  acts=[('move', self.staging)])
        self.check("the entry's destination, a bare file not yet wrapped nesting under its pattern folder",
                   self.read_stage().get('destination'), str(self.movin / 'the.florist.2026'))
        self.check("the survey's shape", self.survey_shape(), 'single_file')
        daemon.moved(self.staging)
        self.step('in staging: the wrap, a files plan', 'oce_storage_moved', str(self.staging), stage='renaming',
                  acts=[('rename_files', wrap)])
        daemon.file_renamed(*wrap[0])
        self.step('wrapped, 1/1: no file renames left, the move into movin, its destination given again',
                  'oce_file_renamed', '0', wrap[0][1], stage='moving', acts=[('move', self.movin)])
        self.check('the destination at the move, flat, the wrap done', self.read_stage().get('destination'),
                   str(self.movin))
        self.check_oceanmeta(self.movin / 'the.florist.2026', hashes=[self.torrent_id, alternate], release_name=name)
        daemon.moved(self.movin)
        self.step('in movin: the card says wrapped', 'oce_storage_moved', str(self.movin), stage='done',
                  card=self.completed_card('wrapped into **the.florist.2026/**', destination=self.movin))

    def case_file_rename_failed(self):
        daemon = self.daemon = self.yts_daemon()
        self.step('entered', 'oce_storage_moved', self.completed, stage='staging', acts=[('move', self.staging)])
        daemon.moved(self.staging)
        self.step('the folder rename', 'oce_storage_moved', str(self.staging), stage='renaming',
                  acts=[('rename_folder', f'{self.yts_folder}/', 'the.florist.2026/')])
        daemon.folder_renamed(f'{self.yts_folder}/', 'the.florist.2026/')
        file_plan = [(0, 'the.florist.2026/the.florist.2026.mp4'), (1, 'the.florist.2026/the.florist.2026.en.srt')]
        self.step('the file renames', 'oce_folder_renamed', f'{self.yts_folder}/', 'the.florist.2026/',
                  stage='renaming_files', acts=[('rename_files', file_plan)])
        daemon.file_renamed(*file_plan[0])
        self.step('one refused: noted, the move as the files stand', 'oce_file_rename_failed', '1', 'File exists',
                  stage='moving', acts=[('move', self.movin)])
        daemon.moved(self.movin)
        self.step('in movin: the card with the diversion, high', 'oce_storage_moved', str(self.movin), stage='done',
                  card=self.completed_card('renamed to **the.florist.2026/**', destination=self.movin,
                                           diversions=('rename failed: **File exists**',)))

    def case_rename_refused(self):
        daemon = self.daemon = self.yts_daemon()
        daemon.failing_act = 'DelugApiRenameFolderTransaction'
        self.step('entered', 'oce_storage_moved', self.completed, stage='staging', acts=[('move', self.staging)])
        daemon.moved(self.staging)
        self.step('the folder rename refused: noted, the move as released', 'oce_storage_moved', str(self.staging),
                  stage='moving',
                  acts=[('rename_folder', f'{self.yts_folder}/', 'the.florist.2026/'), ('move', self.movin)])
        daemon.moved(self.movin)
        self.step('in movin: the card with the diversion', 'oce_storage_moved', str(self.movin), stage='done',
                  card=self.completed_card('as released: **The Florist (2026)/**', destination=self.movin,
                                           diversions=('folder rename failed, moved as not renamed',)))

    def case_storage_moved_failed(self):
        daemon = self.daemon = self.yts_daemon()
        files = [{'index': 0, 'path': f'{self.yts_folder}/The.Florist.2026.1080p.WEBRip.x264.AAC-[YTS.GG].mp4',
                  'size': 1_900_000_000}]
        daemon.files = files
        daemon.orig_files = copy.deepcopy(files)
        self.step('entered', 'oce_storage_moved', self.completed, stage='staging', acts=[('move', self.staging)])
        daemon.moved(self.staging)
        self.step('the folder rename', 'oce_storage_moved', str(self.staging), stage='renaming',
                  acts=[('rename_folder', f'{self.yts_folder}/', 'the.florist.2026/')])
        daemon.folder_renamed(f'{self.yts_folder}/', 'the.florist.2026/')
        movie = (0, 'the.florist.2026/the.florist.2026.mp4')
        self.step('renamed: the movie file renamed', 'oce_folder_renamed', f'{self.yts_folder}/', 'the.florist.2026/',
                  stage='renaming_files', acts=[('rename_files', [movie])])
        daemon.file_renamed(*movie)
        self.step('1/1: the move', 'oce_file_renamed', '0', movie[1], stage='moving', acts=[('move', self.movin)])
        self.step('the move fails: stage failed, one FAILED card, high', 'oce_storage_moved_failed', 'Permission denied',
                  stage='failed',
                  card={'title': 'FAILED: The Florist (2026)',
                        'lines': ['at **moving**: storage move failed: **Permission denied**',
                                  f'hash **{self.torrent_id}**'],
                        'tags': ['x', 'movin'], 'priority': 'high'})
        self.step('a later event for a failed chain: nothing', 'oce_storage_moved', str(self.movin), stage='failed')

    def case_link_raises(self):
        daemon = self.daemon = self.yts_daemon()
        daemon.is_present = False
        self.step('no status from the daemon: the FAILED card at the stage, raised on', 'oce_storage_moved',
                  self.completed, stage=None, raises='RuntimeError',
                  card={'title': 'FAILED: The Florist (2026)',
                        'lines': [f'at **entered**: **RuntimeError: no status for {self.torrent_id} from the daemon: '
                                  f'None**'],
                        'tags': ['x'], 'priority': 'high'})

    def case_raw_finish(self):
        self.daemon = self.yts_daemon()
        self.daemon.location = '/deluge/downloads'
        self.step("the raw finish of a torrent Deluge handles: a log line, Deluge's own move enters",
                  'oce_torrent_finished', 'deluge_handled', stage=None)
        self.step('the raw finish of a hybrid, its metadata before 0.5: one high card, stage unhandled',
                  'oce_torrent_finished', 'deluge_missed', stage='unhandled',
                  card={'title': 'COMPLETED: The Florist (2026)',
                        'lines': ['not handled: hybrid torrent, left in **/deluge/downloads** until Deluge is patched',
                                  f'hash **{self.torrent_id}**'],
                        'tags': ['white_check_mark', 'warning', 'diverted'], 'priority': 'high'})
        self.step('its raw finish at the next daemon start: a log line, no second card', 'oce_torrent_finished',
                  'deluge_missed', stage='unhandled')
        self.step('a move into completed/ for an unhandled torrent: nothing', 'oce_storage_moved', self.completed,
                  stage='unhandled')

    def case_off_daemon(self):
        # on dev the chain is left to the daemon's hook: a warning, no stage, no act, no card
        from executin.commons import Commons

        self.daemon = self.yts_daemon()
        Commons.singleton.is_at_daemon = False
        try:
            self.step('off the daemon: one warning, nothing staged, nothing asked', 'oce_storage_moved', self.completed,
                      stage=None, lines=["Not at daemon, the chain of 'The Florist (2026) [1080p] [YTS.GG]' is left to "
                                         "the daemon's hook"])
        finally:
            Commons.singleton.is_at_daemon = True

    def case_stagor(self):
        # the stage file's lock taken and released, its plans in and out of yaml, a key or a stage it does not know
        import fcntl

        stagor = self.classes['Stagor'](self.torrent_id)
        with stagor.held():
            with open(stagor.lock_file) as other:
                try:
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    is_taken = False
                except BlockingIOError:
                    is_taken = True
        self.check('the lock held inside held()', is_taken, True)
        with open(stagor.lock_file) as other:
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(other, fcntl.LOCK_UN)
        self.check('the lock released after it', True, True)
        stagor.write(stage='renaming', rename_plan=('a/', 'b/'), file_plan=[(0, 'b/b.mkv'), (2, 'b/b.en.srt')])
        stage = stagor.read()
        self.check('a folder plan back as the tuple', stage['rename_plan'], ('a/', 'b/'))
        self.check('a files plan back as pairs', stage['file_plan'], [(0, 'b/b.mkv'), (2, 'b/b.en.srt')])
        self.check('started and updated stamped', bool(stage.get('started') and stage.get('updated')), True)
        for changes in ({'stage_name': 'x'}, {'stage': 'lost'}):
            try:
                stagor.write(**changes)
                refused = None
            except ValueError as exc:
                refused = 'refused'
            self.check(f'{changes} refused', refused, 'refused')

    def executize(self):
        print('Testor.executize...')
        cases: list[tuple[str, Callable[[], None]]] = [
            ('the stage file: its lock, its plans, its keys', self.case_stagor),
            ('a yts folder through the whole chain, each link re-fired', self.case_yts_folder),
            ("no label: one card, then the hand's trigger enters", self.case_unlabelled_then_the_hand),
            ('a label no handlor knows: one card', self.case_label_without_handlor),
            ("no label and no click record: a log line, the hand's trigger still enters", self.case_unlabelled_no_record),
            ('a label no handlor knows and no click record: a log line', self.case_label_without_handlor_no_record),
            ("no label, the click's record by the kept alternate: the card", self.case_unlabelled_by_alternate),
            ('failures on a chain torrent after it is done: FAILED cards', self.case_failures_on_a_chain_torrent),
            ("failures with no stage, or for a hybrid left unhandled: log lines", self.case_failures_not_the_chains),
            ('arrived in its pattern folder: already named', self.case_already_named),
            ('a TV episode: no rename, no sidecars, a refresh that raises', self.case_tv_no_rename),
            ('a bare movie file: wrapped by a files plan', self.case_bare_movie_wrapped),
            ('a file rename refused by libtorrent: noted, moved', self.case_file_rename_failed),
            ('the folder rename refused by the daemon: noted, moved as released', self.case_rename_refused),
            ('the move into the library fails: FAILED', self.case_storage_moved_failed),
            ('a link that raises: FAILED, raised on', self.case_link_raises),
            ('the raw finish: Deluge handles it, or a hybrid is carded once', self.case_raw_finish),
            ('off the daemon: the chain left alone', self.case_off_daemon),
        ]
        for case_name, case in cases:
            print(f'--- {case_name}')
            with tempfile.TemporaryDirectory(prefix='test_oceanic_chain_') as temp_dir:
                self.lay_out(Path(temp_dir))
                case()
        print(f'{self.steps} steps')
        print('ALL AS EXPECTED' if self.all_as_expected else 'NOT ALL AS EXPECTED')

    def survey_shape(self) -> str | None:
        import yaml

        survey = yaml.safe_load((self.base / 'deluge' / 'surveys' / f'{self.torrent_id}.yml').read_text())
        return survey['torrent_data']['structure']['structure_type']

    def check_oceanmeta(self, folder: Path, *, hashes: list[str], label: str = 'movin',
                        release_name: str | None = None) -> None:
        # the record and the survey as it came under .oceanmeta/, each named by the hash, the record's hashes and entry
        import yaml

        oceanmeta = folder / '.oceanmeta'
        self.check(f"{self.shown(oceanmeta)} holds the record and the survey",
                   sorted(path.name for path in oceanmeta.iterdir()),
                   [f'{self.torrent_id}.survey.yml', f'{self.torrent_id}.yml'])
        record_text = (oceanmeta / f'{self.torrent_id}.yml').read_text()
        record = yaml.safe_load(record_text)
        print('the record:')
        for line in self.shown(record_text).splitlines():
            print(f'  | {line}')
        survey_text = (self.base / 'deluge' / 'surveys' / f'{self.torrent_id}.yml').read_text()
        survey_copy = oceanmeta / f'{self.torrent_id}.survey.yml'
        self.check("the record's hashes", record.get('hashes'), hashes)
        self.check("the record's entry", record.get('entry'), 'storage_moved')
        self.check("the record's label", record.get('label'), label)
        self.check("the record's release name, as it came", record.get('release_name'), release_name or self.yts_folder)
        self.check('the survey copied verbatim', survey_copy.exists() and survey_copy.read_text() == survey_text, True)
        self.check('modes, the dot-directory and its files', sorted({oct(path.stat().st_mode & 0o777)
                                                                     for path in [oceanmeta, *oceanmeta.iterdir()]}),
                   ['0o666', '0o777'])


def main():
    # the card's stand-in goes in before the hook speaks, so nothing is sent; the daemon is the FakeDaemon, the
    # reactor none, the chain's generators run by inlineCallbacks alone over answers already there
    emitting_module.NtfyAnnouncor = RecordingNtfyAnnouncor
    from executin.commons import Commons
    from executin.torrenthandlor import TorrentHandlorMovin, TorrentHandlorTvin
    from executin.torrentor import Torrentor
    from oceanin.stagor import Stagor

    executor = Testor({'Torrentor': Torrentor, 'TorrentHandlorMovin': TorrentHandlorMovin,
                       'TorrentHandlorTvin': TorrentHandlorTvin, 'Stagor': Stagor})
    Commons.singleton.is_at_daemon = True
    Stagor.default_staging_dir = staticmethod(lambda: executor.base / 'deluge' / 'staging')
    OceanicHook.react = lambda hook, reactize: reactize()
    OceanicHook.transact = lambda hook, transaction: executor.daemon.answer(transaction)

    def jellyfin_refresh(torrentor, label_handler, destination):
        if executor.is_refresh_raising:
            raise ConnectionError('refused on purpose')
        executor.refreshes.append((label_handler.jelly_library_name, destination))

    Torrentor.jellyfin_refresh = jellyfin_refresh
    executor.executize()
    raise SystemExit(0 if executor.all_as_expected else 1)


if __name__ == '__main__':
    main()
