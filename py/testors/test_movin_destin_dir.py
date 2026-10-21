#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
from delugapi.torrent import DelugapiTorrent
from executin.torrenthandlor import TorrentHandlorMovin


class Testor:
    def __init__(self):
        super().__init__()

    def executize(self):
        print("Testor.executize...")
        delugapi_torrent = DelugapiTorrent(
            tid='0123456789abcdef0123456789abcdef01234567',
            name='The.Florist.2026.1080p.WEBRip.x265-GROUP.mkv',
            download_location='/deluge/downloads',
            label='movin',
        )
        single_file_survey = {'torrent_data': {'structure': {'structure_type': 'single_file'}}}
        single_directory_survey = {'torrent_data': {'structure': {'structure_type': 'single_directory'}}}
        movie_record = {'media_title': 'The Florist', 'media_year': 2026, 'media_type': 'movie', 'media_via': 'tmdb'}
        null_record = {'media_title': None, 'media_year': None, 'media_type': None, 'media_via': None}
        movin_dir = '/ocean/video/movies/movin'
        cases = [
            ('movie record', single_file_survey, movie_record, f'{movin_dir}/the.florist.2026'),
            ('movie record, null year', single_file_survey, {**movie_record, 'media_year': None}, f'{movin_dir}/the.florist'),
            ('no record', single_file_survey, None, f'{movin_dir}/the.florist'),
            ('absent file', single_file_survey, {}, f'{movin_dir}/the.florist'),
            ('series record', single_file_survey, {**movie_record, 'media_type': 'series'}, f'{movin_dir}/the.florist'),
            ('null record', single_file_survey, null_record, f'{movin_dir}/the.florist'),
            ('movie, null title', single_file_survey, {**movie_record, 'media_title': None}, f'{movin_dir}/the.florist'),
            ('movie, punctuation title', single_file_survey, {**movie_record, 'media_title': '...'}, f'{movin_dir}/the.florist'),
            ('single_directory, movie record', single_directory_survey, movie_record, movin_dir),
            ('single_directory, no record', single_directory_survey, None, movin_dir),
            ('no survey, movie record', {}, movie_record, f'{movin_dir}/the.florist.2026'),
        ]
        all_as_expected = True
        for case_name, survey_data, browser_source_data, expected in cases:
            print(f"--- {case_name}")
            label_handler = TorrentHandlorMovin.factory(
                'movin',
                delugapi_torrent=delugapi_torrent,
                survey_data=survey_data,
                browser_source_data=browser_source_data,
            )
            destin_dir = label_handler.destin_dir
            is_as_expected = str(destin_dir) == expected
            all_as_expected = all_as_expected and is_as_expected
            print(f"destin_dir: '{destin_dir}'  expected '{expected}'  {is_as_expected}")
        print(f"all as expected: {all_as_expected}")


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
