#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
import subprocess
import tempfile
from pathlib import Path

import yaml

from delugapi.torrent import DelugapiTorrent
from executin.torrenthandlor import TorrentHandlorMovin


class Testor:
    def __init__(self):
        super().__init__()

    def executize(self):
        print("Testor.executize...")
        yts_folder = 'The Florist (2026) [NORDICSUBS] [1080p] [WEBRip] [5.1] [YTS.GG - YTS.BZ]'
        yts_files = [
            {'index': 0, 'path': f'{yts_folder}/The.Florist.2026.NORDICSUBS.1080p.WEBRip.x264.AAC5.1-[YTS.GG].mp4', 'size': 1943466000},
            {'index': 1, 'path': f'{yts_folder}/www.YTS.GG.jpg', 'size': 53812},
        ]
        florist_record = {'imdb_id': 'tt33214716', 'tmdb_id': 1476746, 'media_title': 'The Florist', 'media_year': 2026,
                          'media_type': 'movie', 'media_via': 'tmdb'}
        delugapi_torrent = DelugapiTorrent(
            tid='00d1efbc6ebd63daabdfe9cbf50bfda49f0e942c',
            name=yts_folder,
            files=yts_files,
            orig_files=yts_files,
            download_location='/deluge/completed',
            label='movin',
        )
        label_handler = TorrentHandlorMovin.factory(
            'movin',
            delugapi_torrent=delugapi_torrent,
            survey_data={'torrent_data': {'structure': {'structure_type': 'single_directory'}}},
            browser_source_data=florist_record,
        )
        all_as_expected = True
        with tempfile.TemporaryDirectory(prefix='sidecar_write_') as scratch_sdir:
            scratch_dir = Path(scratch_sdir)
            sidecar_dir = scratch_dir / 'movin' / 'the.florist.2026'

            print("--- first call, the folder does not exist yet")
            first_paths = label_handler.write_sidecars(sidecar_dir)
            subprocess.run(['ls', '-la', str(sidecar_dir)])
            subprocess.run(['ls', '-la', str(sidecar_dir / '.oceanmeta')])
            first_inodes = {path.name: path.stat().st_ino for path in first_paths}
            leftovers = list(sidecar_dir.rglob('.*.tmp'))
            record_name = '00d1efbc6ebd63daabdfe9cbf50bfda49f0e942c.yml'
            modes = {path.name: oct(path.stat().st_mode & 0o777) for path in [*first_paths, sidecar_dir / '.oceanmeta']}
            is_first_as_expected = ([path.name for path in first_paths] == [record_name, 'movie.nfo']
                                    and modes == {record_name: '0o666', 'movie.nfo': '0o666', '.oceanmeta': '0o777'}
                                    and not leftovers)
            print(f"written: {[path.name for path in first_paths]}  modes {modes}  .tmp left: {leftovers}  "
                  f"{is_first_as_expected}")

            print("--- second call, overwrites both")
            label_handler._browser_source_data = {**florist_record, 'media_title': 'The Florist, rewritten'}
            second_paths = label_handler.write_sidecars(sidecar_dir)
            subprocess.run(['ls', '-la', str(sidecar_dir)])
            second_inodes = {path.name: path.stat().st_ino for path in second_paths}
            leftovers = list(sidecar_dir.rglob('.*.tmp'))
            nfo_text = (sidecar_dir / 'movie.nfo').read_text(encoding='utf-8')
            record = yaml.safe_load((sidecar_dir / '.oceanmeta' / record_name).read_text(encoding='utf-8'))
            is_replaced = all(second_inodes[name] != first_inodes[name] for name in first_inodes)
            is_rewritten = ('<title>The Florist, rewritten</title>' in nfo_text
                            and record['click']['media_title'] == 'The Florist, rewritten')
            is_second_as_expected = is_replaced and is_rewritten and not leftovers
            print(f"inodes {first_inodes} -> {second_inodes}  replaced: {is_replaced}")
            print(f"new title in movie.nfo and the record: {is_rewritten}  .tmp left: {leftovers}  {is_second_as_expected}")

            print("--- an unwritable folder, mode 500")
            locked_dir = scratch_dir / 'locked'
            locked_dir.mkdir()
            locked_dir.chmod(0o500)
            subprocess.run(['ls', '-ld', str(locked_dir)])
            locked_paths = label_handler.write_sidecars(locked_dir)
            print(f"written: {locked_paths}  {locked_paths == []}")

            print("--- a folder that cannot be made, under the mode 500 one")
            unmade_paths = label_handler.write_sidecars(locked_dir / 'the.florist.2026')
            print(f"written: {unmade_paths}  {unmade_paths == []}")
            locked_dir.chmod(0o700)
            is_locked_as_expected = locked_paths == [] and unmade_paths == [] and not list(locked_dir.iterdir())

            all_as_expected = is_first_as_expected and is_second_as_expected and is_locked_as_expected
        print(f"scratch removed: {not scratch_dir.exists()}")
        print(f"all as expected: {all_as_expected}")


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
