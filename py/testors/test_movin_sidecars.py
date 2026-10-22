#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
import tempfile
from pathlib import Path

import yaml

from delugapi.torrent import DelugapiTorrent
from executin.torrenthandlor import TorrentHandlorMovin, TorrentHandlorTvin


class Testor:
    def __init__(self):
        super().__init__()

    def executize(self):
        print("Testor.executize...")
        yts_folder = 'The Florist (2026) [NORDICSUBS] [1080p] [WEBRip] [5.1] [YTS.GG - YTS.BZ]'
        yts_files = [
            {'index': 0, 'path': f'{yts_folder}/The.Florist.2026.NORDICSUBS.1080p.WEBRip.x264.AAC5.1-[YTS.GG].mp4', 'size': 1943466000},
            {'index': 1, 'path': f'{yts_folder}/www.YTS.GG.jpg', 'size': 53812},
            {'index': 2, 'path': f'{yts_folder}/YTSProxies.com.txt', 'size': 2568},
        ]
        renamed_files = [{**file, 'path': file['path'].replace(yts_folder, 'the.florist.2026', 1)} for file in yts_files]
        name_rule_renamed_files = [{**file, 'path': file['path'].replace(yts_folder, 'the.florist', 1)} for file in yts_files]
        own_nfo_files = yts_files + [{'index': 3, 'path': f'{yts_folder}/movie.nfo', 'size': 4096}]
        own_nfo_renamed_files = [{**file, 'path': file['path'].replace(yts_folder, 'the.florist.2026', 1)} for file in own_nfo_files]
        nested_nfo_files = yts_files + [{'index': 3, 'path': f'{yts_folder}/Extras/movie.nfo', 'size': 4096}]
        nested_nfo_renamed_files = [{**file, 'path': file['path'].replace(yts_folder, 'the.florist.2026', 1)} for file in nested_nfo_files]
        moonrise_folder = 'Moonrise Kingdom (2012) Criterion (...)'
        moonrise_files = [
            {'index': 0, 'path': f'{moonrise_folder}/Moonrise.Kingdom.en.srt', 'size': 98304},
            {'index': 1, 'path': f'{moonrise_folder}/Moonrise Kingdom (...).mkv', 'size': 8589934592},
        ]
        bare_name = 'The Florist 2026 1080p WEB-DL HEVC x265 5.1 BONE.mkv'
        bare_files = [{'index': 0, 'path': bare_name, 'size': 1500000000}]
        tie_files = [
            {'index': 0, 'path': f'{yts_folder}/cd1/part.mkv', 'size': 700},
            {'index': 1, 'path': f'{yts_folder}/cd2/part.mkv', 'size': 700},
        ]

        def survey(structure_type: str) -> dict:
            return {'torrent_data': {'structure': {'structure_type': structure_type}}}

        florist_record = {
            'ts': '20261022_012014',
            'infohash': '00d1efbc6ebd63daabdfe9cbf50bfda49f0e942c',
            'dn': 'The Florist (2026) [1080p] [YTS.GG]',
            'source': 'https://yts.gg/movies/the-florist-2026',
            'category': 'movie',
            'site': 'yts',
            'tracker_count': 6,
            'extras': {'x.source': 'https://yts.gg/movies/the-florist-2026', 'x.imdb': 'https://www.imdb.com/title/tt33214716/'},
            'subtitles': [{'lang': 'en', 'url': 'https://example.invalid/sub/1'}],
            'magnet': 'magnet:?xt=urn:btih:00D1EFBC6EBD63DAABDFE9CBF50BFDA49F0E942C&dn=The+Florist',
            'label_hint': 'movin',
            'label_hint_via': 'category',
            'imdb_id': 'tt33214716',
            'tmdb_id': 1476746,
            'media_title': 'The Florist',
            'media_year': 2026,
            'media_type': 'movie',
            'media_via': 'tmdb',
        }
        florist_nfo = (
            '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
            '<movie>\n'
            '  <title>The Florist</title>\n'
            '  <year>2026</year>\n'
            '  <imdbid>tt33214716</imdbid>\n'
            '  <tmdbid>1476746</tmdbid>\n'
            '  <uniqueid type="imdb" default="true">tt33214716</uniqueid>\n'
            '  <uniqueid type="tmdb">1476746</uniqueid>\n'
            '</movie>\n'
        )
        fast_nfo = florist_nfo.replace('<title>The Florist</title>', '<title>Fast &amp; Furious &lt;Test&gt;</title>')
        imdb_only_nfo = (
            '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
            '<movie>\n'
            '  <title>The Florist</title>\n'
            '  <imdbid>tt33214716</imdbid>\n'
            '  <uniqueid type="imdb" default="true">tt33214716</uniqueid>\n'
            '</movie>\n'
        )
        provenance_keys = ['written', 'infohash', 'label', 'release_name', 'folder', 'renamed', 'destination',
                           'orig_files', 'files', 'click']
        movin_dir = '/ocean/video/movies/movin'
        # (case, name, files, orig_files, current_files, is_renamed, survey, record, expected sidecar_dir, expected nfo)
        cases = [
            ('florist shape, renamed', yts_folder, yts_files, yts_files, renamed_files, True,
             survey('single_directory'), florist_record, f'{movin_dir}/the.florist.2026', florist_nfo),
            ('moonrise shape, not renamed, survey missing, no record', moonrise_folder, moonrise_files, moonrise_files,
             None, False, {}, {}, f'{movin_dir}/moonrise.kingdom/{moonrise_folder}', None),
            ('bare file, not renamed, no record', bare_name, bare_files, bare_files, None, False,
             survey('single_file'), {}, f'{movin_dir}/the.florist', None),
            ('series record', yts_folder, yts_files, yts_files, name_rule_renamed_files, True,
             survey('single_directory'), {**florist_record, 'media_type': 'series'}, f'{movin_dir}/the.florist', None),
            ('movie record, imdb_id and tmdb_id null', yts_folder, yts_files, yts_files, renamed_files, True,
             survey('single_directory'), {**florist_record, 'imdb_id': None, 'tmdb_id': None},
             f'{movin_dir}/the.florist.2026', None),
            ('movie record, title Fast & Furious <Test>', yts_folder, yts_files, yts_files, None, False,
             survey('single_directory'), {**florist_record, 'media_title': 'Fast & Furious <Test>'},
             f'{movin_dir}/{yts_folder}', fast_nfo),
            ('movie record, year and tmdb_id null', yts_folder, yts_files, yts_files, name_rule_renamed_files, True,
             survey('single_directory'), {**florist_record, 'media_year': None, 'tmdb_id': None},
             f'{movin_dir}/the.florist', imdb_only_nfo),
            ('two files of one size, the first wins', yts_folder, tie_files, tie_files, None, False,
             survey('multiple_directories'), florist_record, f'{movin_dir}/the.florist.2026/{yts_folder}/cd1', florist_nfo),
            ('no files', yts_folder, [], [], None, False,
             survey('single_directory'), florist_record, None, florist_nfo),
            ('the torrent ships its own movie.nfo at the root, the nfo written anyway', yts_folder, own_nfo_files,
             own_nfo_files, own_nfo_renamed_files, True,
             survey('single_directory'), florist_record, f'{movin_dir}/the.florist.2026', florist_nfo),
            ('the torrent ships a movie.nfo in a subfolder, the nfo written', yts_folder, nested_nfo_files,
             nested_nfo_files, nested_nfo_renamed_files, True,
             survey('single_directory'), florist_record, f'{movin_dir}/the.florist.2026', florist_nfo),
        ]
        all_as_expected = True
        for (case_name, name, files, orig_files, current_files, is_renamed, survey_data, browser_source_data,
             expected_dir, expected_nfo) in cases:
            print(f"--- {case_name}")
            delugapi_torrent = DelugapiTorrent(
                tid='00d1efbc6ebd63daabdfe9cbf50bfda49f0e942c',
                name=name,
                files=files,
                orig_files=orig_files,
                download_location='/deluge/completed',
                label='movin',
                total_wanted=sum(file['size'] for file in files),
            )
            label_handler = TorrentHandlorMovin.factory(
                'movin',
                delugapi_torrent=delugapi_torrent,
                survey_data=survey_data,
                browser_source_data=browser_source_data,
            )
            label_handler.is_renamed = is_renamed
            label_handler.current_files = current_files
            sidecar_dir = label_handler.sidecar_dir
            is_dir_as_expected = (str(sidecar_dir) if sidecar_dir is not None else None) == expected_dir
            print(f"sidecar_dir: '{sidecar_dir}'  expected '{expected_dir}'  {is_dir_as_expected}")
            sidecar_files = label_handler.sidecar_files
            nfo = sidecar_files.get('movie.nfo')
            is_nfo_as_expected = nfo == expected_nfo
            print(f"sidecar files: {list(sidecar_files)}  movie.nfo as expected: {is_nfo_as_expected}")
            if nfo is not None:
                print(nfo, end='')
            provenance = yaml.safe_load(sidecar_files['provenance.yml'])
            expected_click = {key: value for key, value in browser_source_data.items()
                              if key not in ('magnet', 'subtitles', 'extras')} if browser_source_data else None
            is_provenance_as_expected = (
                list(provenance) == provenance_keys
                and provenance['infohash'] == delugapi_torrent.tid
                and provenance['label'] == 'movin'
                and provenance['release_name'] == name
                and provenance['folder'] == label_handler.pattern_dir_name
                and provenance['renamed'] is is_renamed
                and provenance['destination'] == str(label_handler.destin_dir)
                and provenance['orig_files'] == [file['path'] for file in orig_files]
                and provenance['files'] == [file['path'] for file in (current_files if current_files is not None else files)]
                and provenance['click'] == expected_click
            )
            print(f"provenance.yml keys: {list(provenance)}  as expected: {is_provenance_as_expected}")
            print(f"  written {provenance['written']!r}  renamed {provenance['renamed']}  "
                  f"release_name {provenance['release_name']!r}")
            click = provenance['click']
            print(f"  click: {None if click is None else list(click)}")
            if case_name == 'florist shape, renamed':
                print(sidecar_files['provenance.yml'], end='')
            all_as_expected = all_as_expected and is_dir_as_expected and is_nfo_as_expected and is_provenance_as_expected

        print("--- sidecars that cannot be built, movie_nfo patched to raise")

        def broken_movie_nfo(handler) -> str:
            raise ValueError('movie_nfo broken on purpose')

        broken_torrent = DelugapiTorrent(
            tid='00d1efbc6ebd63daabdfe9cbf50bfda49f0e942c',
            name=yts_folder,
            files=yts_files,
            orig_files=yts_files,
            download_location='/deluge/completed',
            label='movin',
        )
        broken_handler = TorrentHandlorMovin.factory(
            'movin',
            delugapi_torrent=broken_torrent,
            survey_data=survey('single_directory'),
            browser_source_data=florist_record,
        )
        original_movie_nfo = TorrentHandlorMovin.movie_nfo
        TorrentHandlorMovin.movie_nfo = property(broken_movie_nfo)
        try:
            with tempfile.TemporaryDirectory(prefix='sidecar_build_') as scratch_sdir:
                broken_dir = Path(scratch_sdir) / 'movin' / 'the.florist.2026'
                broken_paths = broken_handler.write_sidecars(broken_dir)
                is_broken_as_expected = broken_paths == [] and not broken_dir.exists()
                print(f"written: {broken_paths}  folder made: {broken_dir.exists()}  {is_broken_as_expected}")
        finally:
            TorrentHandlorMovin.movie_nfo = original_movie_nfo
        all_as_expected = all_as_expected and is_broken_as_expected

        print("--- tv-in handler, florist shape")
        tv_torrent = DelugapiTorrent(
            tid='00d1efbc6ebd63daabdfe9cbf50bfda49f0e942c',
            name=yts_folder,
            files=yts_files,
            download_location='/deluge/completed',
            label='tv-in',
        )
        tv_handler = TorrentHandlorTvin.factory(
            'tv-in',
            delugapi_torrent=tv_torrent,
            survey_data=survey('single_directory'),
            browser_source_data=florist_record,
        )
        is_tv_as_expected = tv_handler.sidecar_dir is None and tv_handler.sidecar_files == {}
        all_as_expected = all_as_expected and is_tv_as_expected
        print(f"sidecar_dir: {tv_handler.sidecar_dir}  sidecar_files: {tv_handler.sidecar_files}  {is_tv_as_expected}")
        print(f"all as expected: {all_as_expected}")


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
