#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
import logging
import sys
import tempfile
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
                           'priority': priority.value if priority else None, 'markdown': markdown})
        return f'stub{len(self.cards)}'


class LineRecordor(logging.Handler):
    """Records every line the loggor is given with its level, so a case reads what the hook said."""

    def __init__(self):
        super().__init__()
        self.lines: list[tuple[str, str]] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append((record.levelname, record.getMessage()))


class Testor:
    torrent_id = '0123456789abcdef0123456789abcdef01234567'
    # a hybrid's v1 hash, the magnet's, when the daemon files the torrent under its v2, torrent_id above
    v1_id = 'd1d96f75' * 5
    # the magnet's display name, which a bare magnet's added event carries, and the release's folder, the daemon's name
    # once the metadata is there, which names the copy
    magnet_name = 'The Florist (2026) [1080p] [YTS.GG]'
    release_name = 'The.Florist.2026.1080p.WEBRip.x265-GRP'
    location = '/deluge/downloads'
    execute_args_keys: list[str] = ['torrent_id', 'torrent_name', 'added_base_dir', 'timestamp', 'event', 'torrent_file']

    def __init__(self, torrentor_class: type):
        super().__init__()
        self.torrentor_class = torrentor_class
        self.loggor = TestLoggor()
        self.recordor = LineRecordor()
        self.loggor.addHandler(self.recordor)
        self.base: Path = Path()
        self.all_as_expected = True
        # what the label stand-in saw, the browser-source record it would read among it, and whether it dies
        self.label_calls: list[str] = []
        self.records_read: list[str] = []
        self.is_label_dying = False

    @property
    def torrents_dir(self) -> Path:
        return self.base / 'torrents'

    @property
    def survey_file(self) -> Path:
        return self.base / 'surveys' / f'{self.torrent_id}.yml'

    def label_by_hint(self, torrentor) -> None:
        # stands in for Torrentor.label_by_hint, which talks to the daemon: one call recorded, with the browser-source
        # record its lifted block would read, and its outcome kept
        self.label_calls.append(torrentor.torrent_name)
        self.records_read.append(torrentor.browser_source_file.name)
        if self.is_label_dying:
            raise RuntimeError('daemon refused on purpose')
        torrentor.label_outcome = "set 'movin', read back 'movin'"

    def torrentize(self) -> Path:
        # the daemon's copy of a one-folder release, as test_survey_write.py builds one, named by the release
        import libtorrent as lt

        content_dir = self.base / 'content'
        file = content_dir / self.release_name / f'{self.release_name}.mkv'
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b'magnetics' * 1000)
        file_storage = lt.file_storage()
        lt.add_files(file_storage, str(content_dir / self.release_name))
        creator = lt.create_torrent(file_storage)
        lt.set_piece_hashes(creator, str(content_dir))
        self.torrents_dir.mkdir(parents=True, exist_ok=True)
        torrent_file = self.torrents_dir / f'{self.release_name}.torrent'
        torrent_file.write_bytes(lt.bencode(creator.generate()))
        return torrent_file

    def shown(self, text: str) -> str:
        return text.replace(str(self.base), '<tmp>')

    def judge(self, event_name: str, torrent_name: str, details: tuple[str, ...], *, result: bool, labels: int,
              survey_event: str | None, lines: list[tuple[str, str]], card: dict | None = None,
              is_torrentor_loaded: bool = True, survey_text: str | None = None, record_read: str | None = None,
              stage: dict | None = None):
        """survey_event: the event the survey names once the case ran, None for no survey; survey_text: the survey's
        text as it must stand, for a survey the case laid down itself; record_read: the browser-source record the
        label would read, by default the torrent id's whenever the label runs; stage: the keys stage.yml must hold
        after the case, None for no stage file."""
        hook = OceanicHook(self.torrent_id, torrent_name, self.location, self.loggor)
        self.recordor.lines.clear()
        self.label_calls.clear()
        self.records_read.clear()
        RecordingNtfyAnnouncor.cards.clear()
        got = hook.process_event(event_name, *details)
        is_as_expected = got == result and len(self.label_calls) == labels
        print(f"result: {got}  expected {result}")
        print(f"label calls: {len(self.label_calls)}  expected {labels}")
        expected_records = [record_read or f'{self.torrent_id}.yml'] * labels
        print(f"browser-source records read: {self.records_read}  expected {expected_records}")
        is_as_expected = is_as_expected and self.records_read == expected_records

        got_lines = [(level, self.shown(line)) for level, line in self.recordor.lines]
        expected_lines = [(level, self.shown(line)) for level, line in lines]
        is_said = got_lines == expected_lines
        for level, line in got_lines:
            print(f"line: {level:<8}| {line}")
        if not is_said:
            for level, line in expected_lines:
                print(f"expected: {level:<8}| {line}")
        print(f"lines as expected: {is_said}")
        is_as_expected = is_as_expected and is_said

        if survey_text is not None:
            is_kept = self.survey_file.read_text() == survey_text
            print(f"the survey as laid down: {is_kept}  expected True")
            is_as_expected = is_as_expected and is_kept
        elif survey_event is None:
            is_absent = not self.survey_file.exists()
            print(f"no survey: {is_absent}  expected True")
            is_as_expected = is_as_expected and is_absent
        else:
            is_as_expected = is_as_expected and self.judge_survey(survey_event, torrent_name)

        cards = RecordingNtfyAnnouncor.cards
        if card is None:
            print(f"cards: {len(cards)}  expected 0")
            is_as_expected = is_as_expected and not cards
        else:
            expected_card = {**card, 'markdown': True}
            got_card = cards[0] if len(cards) == 1 else {'cards': len(cards)}
            for key, expected_value in expected_card.items():
                print(f"card {key}: {got_card.get(key)!r}  expected {expected_value!r}")
            is_as_expected = is_as_expected and got_card == expected_card
        stage_file = self.base / 'staging' / self.torrent_id / 'stage.yml'
        if stage is None:
            is_staged = not stage_file.exists()
            print(f"no stage file: {is_staged}  expected True")
        else:
            import yaml

            got_stage = yaml.safe_load(stage_file.read_text()) if stage_file.exists() else {}
            got_keys = {key: got_stage.get(key) for key in stage}
            is_staged = got_keys == stage
            print(f"stage: {got_keys}  expected {stage}")
        is_as_expected = is_as_expected and is_staged
        is_loaded = hook._torrentor is not None
        print(f"the Torrentor loaded: {is_loaded}  expected {is_torrentor_loaded}")
        is_as_expected = is_as_expected and is_loaded == is_torrentor_loaded
        print(f"as expected: {is_as_expected}")
        self.all_as_expected = self.all_as_expected and is_as_expected

    def judge_survey(self, survey_event: str, torrent_name: str) -> bool:
        import yaml

        if not self.survey_file.exists():
            print(f"survey: none  expected one, event {survey_event!r}")
            return False
        survey_data = yaml.safe_load(self.survey_file.read_text())
        execute_args = survey_data['execute_args']
        checks: list[tuple[str, object, object]] = [
            ('execute_args keys', list(execute_args), self.execute_args_keys),
            ('event', execute_args['event'], survey_event),
            ('torrent_name', execute_args['torrent_name'], torrent_name),
            ('added_base_dir', execute_args['added_base_dir'], self.location),
            ('torrent_file', self.shown(execute_args['torrent_file']), f'<tmp>/torrents/{self.release_name}.torrent'),
            ('torrent_data.name', survey_data['torrent_data']['name'], self.release_name),
        ]
        is_as_expected = True
        for check_name, value, expected in checks:
            is_as_expected = is_as_expected and value == expected
            print(f"survey {check_name}: {value!r}  expected {expected!r}")
        return is_as_expected

    def hearing_line(self, event_name: str, torrent_name: str, details: tuple[str, ...] = ()) -> tuple[str, str]:
        return 'INFO', (f"Torrent '{torrent_name}' {event_name}, id '{self.torrent_id}', location '{self.location}', "
                        f"details {list(details)}")

    def survey_line(self, event_name: str, torrent_name: str) -> tuple[str, str]:
        return 'INFO', (f"Survey of '{torrent_name}' written on {event_name}, '{self.survey_file}' "
                        f"from '{self.torrents_dir / f'{self.release_name}.torrent'}'")

    # --- oce_added

    def case_added_copy_there(self):
        # a prefetched magnet, added as a file: the copy written in the daemon's call that emitted the event
        self.torrentize()
        name = self.release_name
        self.judge('oce_added', name, (), result=True, labels=1, survey_event='oce_added',
                   lines=[self.hearing_line('oce_added', name),
                          ('INFO', f"Label of '{name}': set 'movin', read back 'movin'"),
                          self.survey_line('oce_added', name)])

    def case_added_no_copy(self):
        # a bare magnet, added before its prefetch landed: no metadata, no copy, the magnet's name on the event
        name = self.magnet_name
        self.judge('oce_added', name, (), result=True, labels=1, survey_event=None,
                   lines=[self.hearing_line('oce_added', name),
                          ('INFO', f"Label of '{name}': set 'movin', read back 'movin'"),
                          ('INFO', f"No torrent file for '{name}' in '{self.torrents_dir}' yet, "
                                   f"the survey waits for oce_metadata_received")])

    def case_added_label_dies(self):
        # no daemon to talk to: the label's death is one line, and the survey is written all the same
        self.torrentize()
        name = self.release_name
        self.is_label_dying = True
        try:
            self.judge('oce_added', name, (), result=True, labels=1, survey_event='oce_added',
                       lines=[self.hearing_line('oce_added', name),
                              ('ERROR', f"Label of '{name}': died: RuntimeError: daemon refused on purpose"),
                              self.survey_line('oce_added', name)])
        finally:
            self.is_label_dying = False

    def lay_record(self, torrent_id: str) -> None:
        self.browser_source_dir.mkdir(parents=True, exist_ok=True)
        (self.browser_source_dir / f'{torrent_id}.yml').write_text(f'infohash: {torrent_id}\nlabel_hint: movin\n')

    @property
    def browser_source_dir(self) -> Path:
        return self.base / 'browser-source'

    def case_added_hybrid_alternate(self):
        # a hybrid the daemon files under its v2 hash: the plugin passes the v1, which names the click's record
        self.torrentize()
        self.lay_record(self.v1_id)
        name = self.release_name
        details = (self.v1_id,)
        self.judge('oce_added', name, details, result=True, labels=1, survey_event='oce_added',
                   record_read=f'{self.v1_id}.yml', stage={'alternate_ids': [self.v1_id], 'stage': None},
                   lines=[self.hearing_line('oce_added', name, details),
                          ('INFO', f"Browser-source record of '{name}' looked for by '{self.torrent_id}', "
                                   f"then by '{self.v1_id}'"),
                          ('INFO', f"Label of '{name}': set 'movin', read back 'movin'"),
                          self.survey_line('oce_added', name)])

    def case_added_hybrid_own_record_first(self):
        # both records there: the torrent id's own is read, the alternate only after it
        self.torrentize()
        self.lay_record(self.torrent_id)
        self.lay_record(self.v1_id)
        name = self.release_name
        details = (self.v1_id,)
        self.judge('oce_added', name, details, result=True, labels=1, survey_event='oce_added',
                   record_read=f'{self.torrent_id}.yml', stage={'alternate_ids': [self.v1_id], 'stage': None},
                   lines=[self.hearing_line('oce_added', name, details),
                          ('INFO', f"Browser-source record of '{name}' looked for by '{self.torrent_id}', "
                                   f"then by '{self.v1_id}'"),
                          ('INFO', f"Label of '{name}': set 'movin', read back 'movin'"),
                          self.survey_line('oce_added', name)])

    # --- oce_metadata_received

    def case_metadata_copy_there(self):
        # a bare magnet's metadata: Deluge's own handler has written the copy under the daemon's name, which the
        # plugin passes; no label, no daemon call
        self.torrentize()
        name = self.release_name
        self.judge('oce_metadata_received', name, (), result=True, labels=0, survey_event='oce_metadata_received',
                   lines=[self.hearing_line('oce_metadata_received', name),
                          self.survey_line('oce_metadata_received', name)])

    def case_metadata_survey_there(self):
        self.torrentize()
        self.survey_file.parent.mkdir(parents=True)
        laid_down = 'execute_args:\n  event: oce_added\n'
        self.survey_file.write_text(laid_down)
        name = self.release_name
        self.judge('oce_metadata_received', name, (), result=True, labels=0, survey_event=None, survey_text=laid_down,
                   lines=[self.hearing_line('oce_metadata_received', name),
                          ('INFO', f"Survey of '{name}' already there, '{self.survey_file}', nothing written")])

    def case_metadata_no_copy(self):
        name = self.release_name
        self.judge('oce_metadata_received', name, (), result=False, labels=0, survey_event=None,
                   lines=[self.hearing_line('oce_metadata_received', name),
                          ('WARNING', f"No torrent file for '{name}' in '{self.torrents_dir}', "
                                      f"no survey written, left for the completion")])

    def unhandled_card(self) -> dict:
        return {'title': 'UNHANDLED: The Florist 2026 1080p WEBRip x265-GRP',
                'lines': ['hybrid torrent, Deluge cannot track it', 'left in **downloads**',
                          'remove it, or wait for the Deluge patch', f'hash **{self.torrent_id}**'],
                'tags': ['x'], 'priority': 'high'}

    def case_metadata_hybrid(self):
        # a hybrid's metadata, which Deluge's handler missed: the survey from the copy the plugin's repair wrote, one
        # UNHANDLED card, stage unhandled
        self.torrentize()
        name = self.release_name
        details = ('deluge_missed',)
        self.judge('oce_metadata_received', name, details, result=True, labels=0, survey_event='oce_metadata_received',
                   lines=[self.hearing_line('oce_metadata_received', name, details),
                          self.survey_line('oce_metadata_received', name), ('INFO', 'Announced stub1')],
                   card=self.unhandled_card(),
                   stage={'stage': 'unhandled', 'entry': 'metadata_received', 'deluge': 'missed'})

    def case_hybrid_no_second_card(self):
        # the same hybrid again, its metadata at a daemon start, then its raw finish: a log line each, no card
        self.torrentize()
        self.case_metadata_hybrid()
        name = self.release_name
        details = ('deluge_missed',)
        print('... its metadata again')
        self.judge('oce_metadata_received', name, details, result=True, labels=0, survey_event='oce_metadata_received',
                   lines=[self.hearing_line('oce_metadata_received', name, details),
                          ('INFO', f"Survey of '{name}' already there, '{self.survey_file}', nothing written"),
                          ('INFO', f"Chain of '{name}': oce_metadata_received at stage 'unhandled', nothing to do")],
                   stage={'stage': 'unhandled', 'entry': 'metadata_received'})
        print('... its raw finish')
        self.judge('oce_torrent_finished', name, details, result=True, labels=0, survey_event='oce_metadata_received',
                   is_torrentor_loaded=False,
                   lines=[self.hearing_line('oce_torrent_finished', name, details),
                          ('INFO', f"Chain of '{name}': oce_torrent_finished at stage 'unhandled', nothing to do")],
                   stage={'stage': 'unhandled', 'entry': 'metadata_received'})

    # --- oce_metadata_failed

    def case_metadata_failed(self):
        name = self.magnet_name
        details = ('Operation timed out',)
        self.judge('oce_metadata_failed', name, details, result=True, labels=0, survey_event=None,
                   is_torrentor_loaded=False,
                   lines=[self.hearing_line('oce_metadata_failed', name, details), ('INFO', 'Announced stub1')],
                   card={'title': 'FAILED: The Florist (2026)',
                         'lines': ['metadata failed: **Operation timed out**', f'hash **{self.torrent_id}**'],
                         'tags': ['x'], 'priority': 'high'})

    def executize(self):
        print("Testor.executize...")
        cases = [
            ('oce_added, a prefetched magnet: the copy there, the label once, the survey on oce_added',
             self.case_added_copy_there),
            ('oce_added, a bare magnet: no copy yet, the label once, no survey, the wait logged', self.case_added_no_copy),
            ('oce_added, the label dies: one error line, the survey written all the same', self.case_added_label_dies),
            ("oce_added, a hybrid filed under its v2: the click's record found by the v1, the alternate id",
             self.case_added_hybrid_alternate),
            ("oce_added, a hybrid with both records: the torrent id's own read first",
             self.case_added_hybrid_own_record_first),
            ("oce_metadata_received: the copy under the daemon's name, the survey on oce_metadata_received, no label",
             self.case_metadata_copy_there),
            ('oce_metadata_received, the survey already there: nothing written', self.case_metadata_survey_there),
            ('oce_metadata_received, no copy: a warning, nothing written, False', self.case_metadata_no_copy),
            ('oce_metadata_received of a hybrid Deluge missed: the survey, one UNHANDLED card, stage unhandled',
             self.case_metadata_hybrid),
            ('a hybrid already unhandled: its metadata again and its raw finish each a log line, no second card',
             self.case_hybrid_no_second_card),
            ('oce_metadata_failed: one FAILED card, the error and the hash, high, no Torrentor',
             self.case_metadata_failed),
        ]
        klass = self.torrentor_class
        real = {name: getattr(klass, name) for name in ('label_by_hint', 'torrents_dir', 'surveys_dir',
                                                         'browser_source_dir')}
        testor = self
        klass.label_by_hint = lambda torrentor: testor.label_by_hint(torrentor)
        try:
            for case_name, case in cases:
                print(f"--- {case_name}")
                with tempfile.TemporaryDirectory(prefix='test_oceanic_added_') as temp_dir:
                    self.base = Path(temp_dir)
                    klass.torrents_dir = self.base / 'torrents'
                    klass.surveys_dir = self.base / 'surveys'
                    klass.browser_source_dir = self.base / 'browser-source'
                    case()
        finally:
            for name, value in real.items():
                setattr(klass, name, value)
        print('ALL AS EXPECTED' if self.all_as_expected else 'NOT ALL AS EXPECTED')


def main():
    # the hook loads none of the heavies with itself: the Torrentor, twisted and the daemon's client come with oce_added
    heavies = ('executin.torrentor', 'twisted.internet', 'delugapi')
    loaded = [name for name in heavies if name in sys.modules]
    print(f"heavies loaded with the hook: {loaded}  expected []")
    # the card's stand-in goes in before the hook speaks, so nothing is sent; the Torrentor's label_by_hint, the one
    # thing here that talks to the daemon, is stood in for by the Testor
    emitting_module.NtfyAnnouncor = RecordingNtfyAnnouncor
    from executin.torrentor import Torrentor
    from oceanin.stagor import Stagor

    executor = Testor(Torrentor)
    # the hybrid's card and stage are the daemon's hook's, so the testor stands at the daemon
    from executin.commons import Commons

    Commons.singleton.is_at_daemon = True
    # the stage files under the case's own tree, as the Torrentor's dirs are
    Stagor.default_staging_dir = staticmethod(lambda: executor.base / 'staging')
    executor.all_as_expected = not loaded
    executor.executize()


if __name__ == '__main__':
    main()
