#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
import tempfile
from pathlib import Path
import libtorrent as lt  # noqa
import yaml
from executin.torrentor import Torrentor
from executin.torrentparsor import TorrentParsor


class Testor:
    torrent_id: str = '0123456789abcdef0123456789abcdef01234567'
    # the magnet's display name, which the added event carries, and the release's folder, which names the copy
    event_name: str = 'Magnet.Display.Name'
    folder_name: str = 'Folder.Release.2026'
    execute_args_keys: list[str] = ['torrent_id', 'torrent_name', 'added_base_dir', 'timestamp', 'event', 'torrent_file']

    def __init__(self):
        super().__init__()

    def torrentize(self, content_dir: Path, torrents_dir: Path) -> Path:
        file = content_dir / self.folder_name / f'{self.folder_name}.mkv'
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b'magnetics' * 1000)
        file_storage = lt.file_storage()
        lt.add_files(file_storage, str(content_dir / self.folder_name))
        creator = lt.create_torrent(file_storage)
        lt.set_piece_hashes(creator, str(content_dir))
        torrents_dir.mkdir(parents=True, exist_ok=True)
        torrent_file = torrents_dir / f'{self.folder_name}.torrent'
        torrent_file.write_bytes(lt.bencode(creator.generate()))
        return torrent_file

    def executize(self):
        print("Testor.executize...")
        all_as_expected = True
        with tempfile.TemporaryDirectory(prefix='test_survey_write_') as temp_dir:
            torrent_file = self.torrentize(Path(temp_dir) / 'content', Path(temp_dir) / 'torrents')
            torrentor = Torrentor(self.torrent_id, self.event_name, '/deluge/downloads')
            torrentor.torrents_dir = Path(temp_dir) / 'torrents'
            torrentor.surveys_dir = Path(temp_dir) / 'surveys'
            print(f"torrent file: {torrent_file.relative_to(temp_dir)}")

            finder_cases: list[tuple[str, tuple[str, ...], Path | None]] = [
                ('the right name', (self.folder_name,), torrent_file),
                ('a wrong name, then the right one', (self.event_name, self.folder_name), torrent_file),
                ('the wrong name alone', (self.event_name,), None),
                ('an empty name and a repeat, then the right one', ('', self.event_name, self.event_name, self.folder_name), torrent_file),
                ('empty names only', ('', ''), None),
            ]
            for case_name, names, expected in finder_cases:
                found = torrentor.torrent_file_for(*names)
                is_as_expected = found == expected
                all_as_expected = all_as_expected and is_as_expected
                found_text = found.relative_to(temp_dir) if found else None
                expected_text = expected.relative_to(temp_dir) if expected else None
                print(f"torrent_file_for, {case_name}: {names} -> {found_text}  expected {expected_text}  {is_as_expected}")

            parsed_text = yaml.dump({'torrent_data': TorrentParsor(torrent_file).parse()}, sort_keys=False)
            for event_name in ('exe_added', 'exe_completed'):
                print(f"--- survey_write, '{event_name}'")
                written = torrentor.survey_write(torrent_file, event_name)
                survey_text = torrentor.survey_file.read_text()
                survey_data = yaml.safe_load(survey_text)
                execute_args = survey_data['execute_args']
                torrent_data = survey_data['torrent_data']
                checks: list[tuple[str, object, object]] = [
                    ('survey file', torrentor.survey_file.relative_to(temp_dir), Path('surveys') / f'{self.torrent_id}.yml'),
                    ('execute_args keys', list(execute_args), self.execute_args_keys),
                    ('event', execute_args['event'], event_name),
                    ('torrent_file', execute_args['torrent_file'], str(torrent_file)),
                    ('torrent_name', execute_args['torrent_name'], self.event_name),
                    ('added_base_dir', execute_args['added_base_dir'], '/deluge/downloads'),
                    ('structure_type', torrent_data['structure']['structure_type'], 'single_directory'),
                    ('torrent_data.name', torrent_data['name'], self.folder_name),
                    ('torrent_data as parsed, byte for byte', survey_text[survey_text.index('torrent_data:'):] == parsed_text, True),
                    ('returned dict as read back', written == survey_data, True),
                ]
                for check_name, value, expected in checks:
                    is_as_expected = value == expected
                    all_as_expected = all_as_expected and is_as_expected
                    print(f"{check_name}: {value!r}  expected {expected!r}  {is_as_expected}")
        print(f"all as expected: {all_as_expected}")


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
