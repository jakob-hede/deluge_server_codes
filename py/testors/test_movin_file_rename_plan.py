#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
from delugapi.torrent import DelugapiTorrent
from executin.torrenthandlor import TorrentHandlorMovin, TorrentHandlorTvin


class Testor:
    def __init__(self):
        super().__init__()

    def executize(self):
        print("Testor.executize...")
        pattern = 'by.any.means.2026'
        release_stem = 'By.Any.Means.2026.1080p.WEBRip.x264.AAC5.1-[YTS.GG - YTS.BZ]'
        movie = {'index': 0, 'path': f'{pattern}/{release_stem}.mp4', 'size': 2147483648}
        root_srt = {'index': 1, 'path': f'{pattern}/{release_stem}.srt', 'size': 84275}
        french = {'index': 2, 'path': f'{pattern}/Subs/Canadian.fre.srt', 'size': 90112}
        english = {'index': 3, 'path': f'{pattern}/Subs/English.srt', 'size': 84275}
        sdh = {'index': 4, 'path': f'{pattern}/Subs/SDH.eng.srt', 'size': 95232}
        txt = {'index': 5, 'path': f'{pattern}/YIFYStatus.com.txt', 'size': 400}
        jpg = {'index': 6, 'path': f'{pattern}/YTS.GG - Official site.jpg', 'size': 38690}
        by_any_means_files = [movie, root_srt, french, english, sdh, txt, jpg]
        record = {'media_title': 'By Any Means', 'media_year': 2026, 'media_type': 'movie', 'media_via': 'tmdb', 'site': 'yts'}
        by_any_means_plan = {
            0: f'{pattern}/{pattern}.mp4',
            1: f'{pattern}/release.{release_stem}.srt',
            3: f'{pattern}/{pattern}.en.srt',
            4: f'{pattern}/{pattern}.en.sdh.srt',
        }
        root_srt_larger = {**root_srt, 'size': 84378}
        yts_flags_files = [
            movie,
            {'index': 1, 'path': f'{pattern}/Subs/SDH.eng.HI.srt', 'size': 95232},
            {'index': 2, 'path': f'{pattern}/Subs/Forced.eng.srt', 'size': 2048},
            {'index': 3, 'path': f'{pattern}/Subs/dan.srt', 'size': 80896},
        ]
        jellyfin_name_files = [
            movie,
            {'index': 1, 'path': f'{pattern}/movie.nfo', 'size': 3000},
            {'index': 2, 'path': f'{pattern}/folder.jpg', 'size': 120000},
            {'index': 3, 'path': f'{pattern}/Extras/folder.jpg', 'size': 110000},
        ]
        second_video_files = [
            movie,
            {'index': 1, 'path': f'{pattern}/Sample/sample.mkv', 'size': 30000000},
            {'index': 2, 'path': f'{pattern}/trailer.mp4', 'size': 50000000},
        ]
        renamed_files = [{**file, 'path': by_any_means_plan.get(file['index'], file['path'])} for file in by_any_means_files]
        danish_pattern = 'the.danish.girl.2015'
        danish_stem = 'The.Danish.Girl.2015.1080p.BluRay.x264-[YTS.AM]'
        danish_files = [
            {'index': 0, 'path': f'{danish_pattern}/{danish_stem}.mp4', 'size': 2000000000},
            {'index': 1, 'path': f'{danish_pattern}/{danish_stem}.srt', 'size': 70000},
        ]
        danish_record = {'media_title': 'The Danish Girl', 'media_year': 2015, 'media_type': 'movie', 'media_via': 'tmdb', 'site': 'yts'}
        # the specimen hq relayed: the root srt is the size twin of Forced.eng.srt, not of English.srt
        master_pattern = 'masterplan.2026'
        master_stem = 'Masterplan.2026.1080p.WEBRip.x265.10bit.AAC5.1-[YTS.GG - YTS.BZ]'
        master_other_names = [
            'ara.srt', 'heb.Apartheid State.srt', 'Brazilian.por.srt', 'Canadian.fre.srt', 'Castilian.spa.srt',
            'Catalan.cat.srt', 'cze.srt', 'dut.srt', 'fin.srt', 'ger.srt', 'gre.srt', 'hin.srt', 'hun.srt',
            'Iberian.por.srt', 'ind.srt', 'ita.srt', 'jpn.srt', 'kan.srt', 'kor.srt', 'nor.srt', 'pol.srt', 'rum.srt',
        ]
        master_files = [
            {'index': 0, 'path': f'{master_pattern}/{master_stem}.mp4', 'size': 2400000000},
            {'index': 1, 'path': f'{master_pattern}/{master_stem}.srt', 'size': 13722},
            {'index': 2, 'path': f'{master_pattern}/Subs/English.srt', 'size': 86528},
            {'index': 3, 'path': f'{master_pattern}/Subs/Forced.eng.srt', 'size': 13722},
            {'index': 4, 'path': f'{master_pattern}/Subs/dan.srt', 'size': 80000},
        ] + [{'index': 5 + offset, 'path': f'{master_pattern}/Subs/{name}', 'size': 70000 + offset}
             for offset, name in enumerate(master_other_names)]
        master_record = {'media_title': 'Masterplan', 'media_year': 2026, 'media_type': 'movie', 'media_via': 'tmdb', 'site': 'yts'}
        # (case, files, record, expected plan as {index: new_path})
        cases = [
            ('by any means, yts', by_any_means_files, record, by_any_means_plan),
            ('root srt 82.4 K, yts: English.srt keeps .en, the root copy is skipped as a collision',
             [movie, root_srt_larger, french, english, sdh, txt, jpg], record,
             {key: value for key, value in by_any_means_plan.items() if key != 1}),
            ('root srt 82.4 K, 1337x: the root copy is skipped',
             [movie, root_srt_larger, french, english, sdh, txt, jpg], {**record, 'site': '1337x'},
             {key: value for key, value in by_any_means_plan.items() if key != 1}),
            ('SDH.eng.HI, Forced.eng, dan', yts_flags_files, record,
             {0: f'{pattern}/{pattern}.mp4', 1: f'{pattern}/{pattern}.en.sdh.srt',
              2: f'{pattern}/{pattern}.en.forced.srt', 3: f'{pattern}/{pattern}.da.srt'}),
            ("Jellyfin's names at the root", jellyfin_name_files, record,
             {0: f'{pattern}/{pattern}.mp4', 1: f'{pattern}/release.movie.nfo', 2: f'{pattern}/release.folder.jpg'}),
            ('a second and a third video, smaller', second_video_files, record, {0: f'{pattern}/{pattern}.mp4'}),
            ('the plan applied to its own result', renamed_files, record, {}),
            ('a title word that is a language, read after the movie stem', danish_files, danish_record,
             {0: f'{danish_pattern}/{danish_pattern}.mp4', 1: f'{danish_pattern}/{danish_pattern}.en.srt'}),
            ('masterplan: the root srt is the twin of Forced.eng.srt, twenty-two other languages skipped',
             master_files, master_record,
             {0: f'{master_pattern}/{master_pattern}.mp4', 1: f'{master_pattern}/release.{master_stem}.srt',
              2: f'{master_pattern}/{master_pattern}.en.srt', 3: f'{master_pattern}/{master_pattern}.en.forced.srt',
              4: f'{master_pattern}/{master_pattern}.da.srt'}),
        ]
        all_as_expected = True
        for case_name, files, browser_source_data, expected_plan in cases:
            print(f"--- {case_name}")
            delugapi_torrent = DelugapiTorrent(
                tid='0123456789abcdef0123456789abcdef01234567',
                name=files[0]['path'].split('/', 1)[0],
                files=files,
                download_location='/deluge/completed',
                label='movin',
            )
            label_handler = TorrentHandlorMovin.factory(
                'movin',
                delugapi_torrent=delugapi_torrent,
                survey_data={'torrent_data': {'structure': {'structure_type': 'single_directory'}}},
                browser_source_data=browser_source_data,
            )
            file_plan = label_handler.file_rename_plan(files)
            is_as_expected = dict(file_plan) == expected_plan and len(file_plan) == len(expected_plan)
            all_as_expected = all_as_expected and is_as_expected
            for index, new_path in file_plan:
                print(f"  {index}: {new_path}")
            print(f"plan as expected: {is_as_expected}")

        print("--- a bare .mkv through rename_plan, the one-step wrap")
        bare_name = 'By Any Means 2026 1080p WEB-DL HEVC x265 5.1 BONE.MKV'
        bare_torrent = DelugapiTorrent(
            tid='0123456789abcdef0123456789abcdef01234567',
            name=bare_name,
            files=[{'index': 0, 'path': bare_name, 'size': 1500000000}],
            download_location='/deluge/completed',
            label='movin',
        )
        bare_handler = TorrentHandlorMovin.factory(
            'movin',
            delugapi_torrent=bare_torrent,
            survey_data={'torrent_data': {'structure': {'structure_type': 'single_file'}}},
            browser_source_data=record,
        )
        bare_plan = bare_handler.rename_plan
        is_bare_as_expected = bare_plan == [(0, f'{pattern}/{pattern}.mkv')]
        all_as_expected = all_as_expected and is_bare_as_expected
        print(f"rename_plan: {bare_plan}  {is_bare_as_expected}")
        wrapped_files = [{'index': 0, 'path': f'{pattern}/{pattern}.mkv', 'size': 1500000000}]
        bare_file_plan = bare_handler.file_rename_plan(wrapped_files)
        is_wrapped_as_expected = bare_file_plan == []
        all_as_expected = all_as_expected and is_wrapped_as_expected
        print(f"file_rename_plan after the wrap: {bare_file_plan}  {is_wrapped_as_expected}")

        print("--- tv-in handler")
        tv_handler = TorrentHandlorTvin.factory(
            'tv-in',
            delugapi_torrent=DelugapiTorrent(tid='0123456789abcdef0123456789abcdef01234567', name='x', label='tv-in'),
        )
        is_tv_as_expected = tv_handler.file_rename_plan(by_any_means_files) == []
        all_as_expected = all_as_expected and is_tv_as_expected
        print(f"file_rename_plan: {tv_handler.file_rename_plan(by_any_means_files)}  {is_tv_as_expected}")
        print(f"all as expected: {all_as_expected}")


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
