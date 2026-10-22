#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
import tempfile
from pathlib import Path
import libtorrent as lt  # noqa
from executin.torrentparsor import TorrentParsor


class TorrentInfoStandin:
    # libtorrent roots every file of a multi-file torrent under the torrent's name, so a shape without
    # one root folder cannot be built as a .torrent; the parser reads its paths from this stand-in instead
    def __init__(self, paths: list[str]):
        self.paths: list[str] = paths
        super().__init__()

    def num_files(self) -> int:
        return len(self.paths)

    def total_size(self) -> int:
        return 0

    def files(self) -> 'TorrentInfoStandin':
        return self

    def file_path(self, index: int) -> str:
        return self.paths[index]


class Testor:
    download_base: str = '/deluge/completed'
    # (case, the tree's paths, built by libtorrent, expected structure_type, expected path under download_base)
    cases: list[tuple[str, list[str], bool, str, str]] = [
        ('bare file at the root', ['Bare.Release.2026.mkv'], True,
         'single_file', 'Bare.Release.2026.mkv'),
        ('one file inside a folder', ['Folder.Release.2026/Folder.Release.2026.mkv'], True,
         'single_directory', 'Folder.Release.2026'),
        ('three files inside one folder, one in a subfolder',
         ['Folder.Release.2026/Folder.Release.2026.mkv', 'Folder.Release.2026/Folder.Release.2026.nfo',
          'Folder.Release.2026/Subs/English.srt'], True,
         'single_directory', 'Folder.Release.2026'),
        ('two files at the root', ['One.mkv', 'Two.mkv'], False,
         'root_files', ''),
        ('a root file beside a folder with a file', ['Root.nfo', 'Folder/Inner.mkv'], False,
         'mixed', ''),
        ('two folders each with a file', ['First/First.mkv', 'Second/Second.mkv'], False,
         'multiple_directories', ''),
    ]

    def __init__(self):
        super().__init__()

    def torrentize(self, case_dir: Path, paths: list[str]) -> Path:
        for path in paths:
            file = case_dir / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b'magnetics' * 1000)
        target = case_dir / Path(paths[0]).parts[0]
        file_storage = lt.file_storage()
        lt.add_files(file_storage, str(target))
        creator = lt.create_torrent(file_storage)
        lt.set_piece_hashes(creator, str(case_dir))
        torrent_file = case_dir.with_suffix('.torrent')
        torrent_file.write_bytes(lt.bencode(creator.generate()))
        return torrent_file

    def executize(self):
        print("Testor.executize...")
        all_as_expected = True
        with tempfile.TemporaryDirectory(prefix='test_structure_type_') as temp_dir:
            for index, (case_name, paths, is_built, expected_type, expected_sub) in enumerate(self.cases):
                print(f"--- {case_name}")
                if is_built:
                    torrent_file = self.torrentize(Path(temp_dir) / f'case_{index}', paths)
                    parsor = TorrentParsor(torrent_file)
                    print(f"built: {torrent_file.name}")
                else:
                    parsor = TorrentParsor(Path(temp_dir) / f'case_{index}.torrent')
                    parsor._torrent_info = TorrentInfoStandin(paths)  # noqa
                    print("stand-in: libtorrent builds no torrent of this shape")
                parsed_paths = [parsor.files.file_path(i) for i in range(parsor.num_files)]
                print(f"paths: {parsed_paths}")
                structure_type = parsor.get_structure_type().value
                predicted_path = parsor.predict_execute_path(self.download_base)
                expected_path = str(Path(self.download_base) / expected_sub)
                analysis = parsor.get_structure_analysis()
                folder_keys = {key: analysis[key] for key in ('root_files_count', 'directories_count', 'root_files', 'directories') if key in analysis}
                is_as_expected = structure_type == expected_type and predicted_path == expected_path
                all_as_expected = all_as_expected and is_as_expected
                print(f"structure_type: '{structure_type}'  expected '{expected_type}'")
                print(f"predicted_execute_path: '{predicted_path}'  expected '{expected_path}'  {is_as_expected}")
                print(f"folder analysis: {folder_keys}")
        print(f"all as expected: {all_as_expected}")


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
