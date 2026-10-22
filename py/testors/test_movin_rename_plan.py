#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
from delugapi.torrent import DelugapiTorrent
from executin.torrenthandlor import TorrentHandlorMovin, TorrentHandlorTvin


class Testor:
    def __init__(self):
        super().__init__()

    def executize(self):
        print("Testor.executize...")
        yts_folder = 'The Florist (2026) [NORDICSUBS] [1080p] [WEBRip] [5.1] [YTS.GG - YTS.BZ]'
        yts_files = [
            {'index': 0, 'path': f'{yts_folder}/The.Florist.2026.NORDICSUBS.1080p.WEBRip.x264.AAC5.1-[YTS.GG].mp4'},
            {'index': 1, 'path': f'{yts_folder}/www.YTS.GG.jpg'},
            {'index': 2, 'path': f'{yts_folder}/YTSProxies.com.txt'},
        ]
        renamed_files = [{**file, 'path': file['path'].replace(yts_folder, 'the.florist.2026', 1)} for file in yts_files]
        bare_name = 'The Florist 2026 1080p WEB-DL HEVC x265 5.1 BONE.mkv'
        bare_files = [{'index': 0, 'path': bare_name}]
        wrapped_files = [{'index': 0, 'path': f'the.florist.2026/{bare_name}'}]
        two_root_files = [
            {'index': 0, 'path': f'{yts_folder}/The.Florist.2026.mp4'},
            {'index': 1, 'path': 'Extras/making.of.mp4'},
        ]
        mixed_files = [
            {'index': 0, 'path': f'{yts_folder}/The.Florist.2026.mp4'},
            {'index': 1, 'path': 'readme.txt'},
        ]
        moonrise_folder = 'Moonrise Kingdom (2012) Criterion (...)'
        moonrise_files = [{'index': 0, 'path': f'{moonrise_folder}/Moonrise Kingdom (...).mkv'}]
        moonrise_renamed_files = [{'index': 0, 'path': 'moonrise.kingdom.2012/Moonrise Kingdom (...).mkv'}]

        def survey(structure_type: str) -> dict:
            return {'torrent_data': {'structure': {'structure_type': structure_type}}}

        florist_record = {'media_title': 'The Florist', 'media_year': 2026, 'media_type': 'movie', 'media_via': 'tmdb'}
        moonrise_record = {'media_title': 'Moonrise Kingdom', 'media_year': 2012, 'media_type': 'movie', 'media_via': 'tmdb'}
        movin_dir = '/ocean/video/movies/movin'
        yts_plan = (f'{yts_folder}/', 'the.florist.2026/')
        bare_plan = [(0, 'the.florist.2026/the.florist.2026.mkv')]
        moonrise_plan = (f'{moonrise_folder}/', 'moonrise.kingdom.2012/')
        # (case, name, files, survey, record, rename outcome, expected plan, expected destin_dir)
        cases = [
            ('yts folder, confirmed', yts_folder, yts_files, survey('single_directory'), florist_record,
             'confirmed', yts_plan, movin_dir),
            ('yts folder, failed', yts_folder, yts_files, survey('single_directory'), florist_record,
             'failed', yts_plan, movin_dir),
            ('bare file, confirmed', bare_name, bare_files, survey('single_file'), florist_record,
             'confirmed', bare_plan, movin_dir),
            ('bare file, failed', bare_name, bare_files, survey('single_file'), florist_record,
             'failed', bare_plan, f'{movin_dir}/the.florist.2026'),
            ('yts folder, no record, confirmed', yts_folder, yts_files, survey('single_directory'), {},
             'confirmed', (f'{yts_folder}/', 'the.florist/'), movin_dir),
            ('yts folder, already renamed', yts_folder, renamed_files, survey('single_directory'), florist_record,
             None, None, movin_dir),
            ('bare file, already wrapped', bare_name, wrapped_files, survey('single_file'), florist_record,
             None, None, movin_dir),
            ('two root folders', yts_folder, two_root_files, survey('multiple_directories'), florist_record,
             None, None, f'{movin_dir}/the.florist.2026'),
            ('root file beside a folder', yts_folder, mixed_files, survey('mixed'), florist_record,
             None, None, f'{movin_dir}/the.florist.2026'),
            ('no files', yts_folder, [], survey('single_directory'), florist_record,
             None, None, movin_dir),
            ('no files, survey missing', yts_folder, [], {}, florist_record,
             None, None, f'{movin_dir}/the.florist.2026'),
            ('survey missing, yts folder, confirmed', yts_folder, yts_files, {}, florist_record,
             'confirmed', yts_plan, movin_dir),
            ('survey missing, yts folder, failed', yts_folder, yts_files, {}, florist_record,
             'failed', yts_plan, f'{movin_dir}/the.florist.2026'),
            ('survey missing, bare file, failed', bare_name, bare_files, {}, florist_record,
             'failed', bare_plan, f'{movin_dir}/the.florist.2026'),
            ('survey missing, two root folders', yts_folder, two_root_files, {}, florist_record,
             None, None, f'{movin_dir}/the.florist.2026'),
            ('moonrise shape, confirmed', moonrise_folder, moonrise_files, survey('single_file'), moonrise_record,
             'confirmed', moonrise_plan, movin_dir),
            ('moonrise shape, failed', moonrise_folder, moonrise_files, survey('single_file'), moonrise_record,
             'failed', moonrise_plan, f'{movin_dir}/moonrise.kingdom.2012'),
            ('moonrise shape, already renamed', moonrise_folder, moonrise_renamed_files, survey('single_file'),
             moonrise_record, None, None, movin_dir),
        ]
        all_as_expected = True
        for case_name, name, files, survey_data, browser_source_data, outcome, expected_plan, expected_dir in cases:
            print(f"--- {case_name}")
            delugapi_torrent = DelugapiTorrent(
                tid='0123456789abcdef0123456789abcdef01234567',
                name=name,
                files=files,
                download_location='/deluge/completed',
                label='movin',
            )
            label_handler = TorrentHandlorMovin.factory(
                'movin',
                delugapi_torrent=delugapi_torrent,
                survey_data=survey_data,
                browser_source_data=browser_source_data,
            )
            rename_plan = label_handler.rename_plan
            # on_completed's rule: renamed when the wait loop confirmed it, or when already in the pattern folder
            if rename_plan is None and label_handler.is_in_pattern_dir:
                label_handler.is_renamed = True
            elif rename_plan is not None and outcome == 'confirmed':
                label_handler.is_renamed = True
            destin_dir = label_handler.destin_dir
            is_plan_as_expected = rename_plan == expected_plan
            is_dir_as_expected = str(destin_dir) == expected_dir
            all_as_expected = all_as_expected and is_plan_as_expected and is_dir_as_expected
            print(f"rename_plan: {rename_plan}  expected {expected_plan}  {is_plan_as_expected}")
            print(f"rename outcome: {outcome}  is_renamed: {label_handler.is_renamed}  pattern_dir: '{label_handler.pattern_dir}'")
            print(f"destin_dir: '{destin_dir}'  expected '{expected_dir}'  {is_dir_as_expected}")

        print("--- tv-in handler, yts folder")
        tv_torrent = DelugapiTorrent(
            tid='0123456789abcdef0123456789abcdef01234567',
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
        is_tv_as_expected = (tv_handler.rename_plan is None and not tv_handler.is_in_pattern_dir
                             and tv_handler.pattern_dir is None and not tv_handler.is_renamed)
        all_as_expected = all_as_expected and is_tv_as_expected
        print(f"rename_plan: {tv_handler.rename_plan}  is_in_pattern_dir: {tv_handler.is_in_pattern_dir}  "
              f"pattern_dir: {tv_handler.pattern_dir}  is_renamed: {tv_handler.is_renamed}  {is_tv_as_expected}")
        print(f"all as expected: {all_as_expected}")


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
