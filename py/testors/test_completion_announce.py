#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
import os

import requests

from delugapi.torrent import DelugapiTorrent
from executin.announcor import HookAnnouncor
from executin.logge import TestLoggor
from executin.naming import HumanNamor
from executin.torrenthandlor import TorrentHandlorMovin, TorrentHandlorTvin
from ntfying.libs.client import NtfyClient, NtfyResult


class TestorHookAnnouncor(HookAnnouncor):
    """The real send carries the tag test, so the phone tells it from a real completion."""

    def say(self, kind, title, lines, *, priority=None, tags=()):
        return super().say(kind, title, lines, priority=priority, tags=(*tags, 'test'))


class Testor:
    def __init__(self):
        super().__init__()

    def executize(self):
        print("Testor.executize...")
        # the sender the box's dotenv will not have, set before the first message builds the habitat
        os.environ['NTFYING_SENDER'] = 'testor@asusi7'
        logger = TestLoggor()
        all_as_expected = True

        # ---
        print("--- the human name, the brief's three cases, hq's two trim rulings and a series record")
        for record, fallback, expected in (
                (None, 'Frankenstein (2025) [1080p] [WEBRip] [x265] [10bit] [5.1] [YTS.MX]', 'Frankenstein (2025)'),
                (None, 'VisionQuest.S01E04.1080p.x265-ELiTE', 'VisionQuest S01E04 1080p x265-ELiTE'),
                (None, 'Tenzing 2026 1080p WEBRip x265 DDP5.1-CSP', 'Tenzing 2026 1080p WEBRip x265 DDP5.1-CSP'),
                (None, 'debian-13.1.0-amd64-netinst.iso', 'debian-13.1.0-amd64-netinst'),
                (None, 'Tenzing.2026.1080p.WEBRip.x265.DDP5.1-CSP', 'Tenzing 2026 1080p WEBRip x265 DDP5.1-CSP'),
                (None, 'Star.Wars', 'Star Wars'),
                (None, 'The.Movie.2020.1080p.mp4', 'The Movie 2020 1080p'),
                (None, 'The.Movie.2020.1080p.MKV', 'The Movie 2020 1080p'),
                ({'media_title': 'VisionQuest', 'media_type': 'series'}, 'VisionQuest.S01E04.1080p.x265-ELiTE',
                 'VisionQuest S01E04'),
        ):
            name = HumanNamor.human_name(record, fallback)
            is_as_expected = name == expected
            all_as_expected &= is_as_expected
            print(f"{fallback!r} -> {name!r}  as expected: {is_as_expected}")

        yts_folder = 'The Florist (2026) [NORDICSUBS] [1080p] [WEBRip] [5.1] [YTS.GG - YTS.BZ]'
        yts_files = [
            {'index': 0, 'path': f'{yts_folder}/The.Florist.2026.NORDICSUBS.1080p.WEBRip.x264.AAC5.1-[YTS.GG].mp4', 'size': 1943466000},
            {'index': 1, 'path': f'{yts_folder}/www.YTS.GG.jpg', 'size': 53812},
            {'index': 2, 'path': f'{yts_folder}/YTSProxies.com.txt', 'size': 2568},
        ]
        renamed_files = [{**file, 'path': file['path'].replace(yts_folder, 'the.florist.2026', 1)} for file in yts_files]
        bare_name = 'The Florist 2026 1080p WEB-DL HEVC x265 5.1 BONE.mkv'
        bare_files = [{'index': 0, 'path': bare_name, 'size': 1500000000}]
        tv_name = 'VisionQuest.S01E03.1080p.x265-ELiTE'
        tv_files = [{'index': 0, 'path': f'{tv_name}/{tv_name}.mkv', 'size': 900000000}]
        iso_name = 'debian-13.1.0-amd64-netinst.iso'
        iso_files = [{'index': 0, 'path': iso_name, 'size': 790000000}]
        infohash = '00d1efbc6ebd63daabdfe9cbf50bfda49f0e942c'
        florist_record = {
            'infohash': infohash,
            'dn': 'The Florist (2026) [1080p] [YTS.GG]',
            'site': 'yts',
            'label_hint': 'movin',
            'imdb_id': 'tt33214716',
            'tmdb_id': 1476746,
            'media_title': 'The Florist',
            'media_year': 2026,
            'media_type': 'movie',
            'media_via': 'tmdb',
        }

        def survey(structure_type: str) -> dict:
            return {'torrent_data': {'structure': {'structure_type': structure_type}}}

        def torrent(name: str, files: list[dict], label: str) -> DelugapiTorrent:
            return DelugapiTorrent(
                tid=infohash,
                name=name,
                files=files,
                orig_files=files,
                download_location='/deluge/completed',
                label=label,
                total_wanted=sum(file['size'] for file in files),
            )

        captured: list[dict] = []

        def stubbed_request(client, method, path, payload=None, extra_headers=None):
            captured.append(payload)
            return NtfyResult(200, {'id': f'stub{len(captured)}', 'topic': payload['topic']})

        original_request = NtfyClient._request
        NtfyClient._request = stubbed_request
        try:
            # ---
            print("--- renamed and moved movie, lookup title")
            florist_torrent = torrent(yts_folder, yts_files, 'movin')
            florist_handler = TorrentHandlorMovin.factory('movin', delugapi_torrent=florist_torrent,
                                                          survey_data=survey('single_directory'),
                                                          browser_source_data=florist_record)
            florist_handler.is_renamed = True
            florist_handler.current_files = renamed_files
            announcor = HookAnnouncor(logger)
            message_id = announcor.completed(florist_torrent, florist_handler, browser_source_data=florist_record,
                                             destination=str(florist_handler.destin_dir), refreshed=True)
            all_as_expected &= self._check(message_id, captured[-1], 'done: The Florist (2026)',
                                           ['in movies/movin', 'jellyfin refreshed', 'renamed to the.florist.2026/', '1.9 GB',
                                            f'hash {infohash}'],
                                           ['white_check_mark', 'movin', 'testor@asusi7'], None)

            # ---
            print("--- tv-in torrent, no record")
            tv_torrent = torrent(tv_name, tv_files, 'tv-in')
            tv_handler = TorrentHandlorTvin.factory('tv-in', delugapi_torrent=tv_torrent,
                                                    survey_data=survey('single_directory'), browser_source_data={})
            announcor = HookAnnouncor(logger)
            message_id = announcor.completed(tv_torrent, tv_handler, browser_source_data={},
                                             destination=str(tv_handler.destin_dir), refreshed=True)
            all_as_expected &= self._check(message_id, captured[-1], 'done: VisionQuest S01E03 1080p x265-ELiTE',
                                           ['in tv/visionquest/s01', 'jellyfin refreshed', 'as released: VisionQuest S01E03 1080p x265-ELiTE/',
                                            '0.9 GB', f'hash {infohash}'],
                                           ['white_check_mark', 'tv-in', 'testor@asusi7'], None)

            # ---
            print("--- unlabelled torrent")
            announcor = HookAnnouncor(logger)
            message_id = announcor.completed(torrent(iso_name, iso_files, ''))
            all_as_expected &= self._check(message_id, captured[-1], 'done: debian-13.1.0-amd64-netinst',
                                           ['not moved: no label', 'jellyfin not refreshed', 'as released: debian-13.1.0-amd64-netinst',
                                            '0.8 GB', f'hash {infohash}'],
                                           ['white_check_mark', 'testor@asusi7'], None)

            # ---
            print("--- not moved, bare movie file off the daemon")
            bare_torrent = torrent(bare_name, bare_files, 'movin')
            bare_handler = TorrentHandlorMovin.factory('movin', delugapi_torrent=bare_torrent,
                                                       survey_data=survey('single_file'),
                                                       browser_source_data=florist_record)
            announcor = HookAnnouncor(logger)
            message_id = announcor.completed(bare_torrent, bare_handler, browser_source_data=florist_record,
                                             not_moved='not at daemon')
            all_as_expected &= self._check(message_id, captured[-1], 'done: The Florist (2026)',
                                           ['not moved: not at daemon', 'jellyfin not refreshed',
                                            'as released: The Florist 2026 1080p WEB-DL HEVC x265 5.1 BONE', '1.5 GB', f'hash {infohash}'],
                                           ['white_check_mark', 'movin', 'testor@asusi7'], None)

            # ---
            print("--- arrived already in its pattern folder, moved")
            named_torrent = torrent('the.florist.2026', renamed_files, 'movin')
            named_handler = TorrentHandlorMovin.factory('movin', delugapi_torrent=named_torrent,
                                                        survey_data=survey('single_directory'),
                                                        browser_source_data=florist_record)
            named_handler.is_renamed = True
            announcor = HookAnnouncor(logger)
            message_id = announcor.completed(named_torrent, named_handler, browser_source_data=florist_record,
                                             destination=str(named_handler.destin_dir), refreshed=True,
                                             already_named=True)
            all_as_expected &= self._check(message_id, captured[-1], 'done: The Florist (2026)',
                                           ['in movies/movin', 'jellyfin refreshed', 'already the.florist.2026/',
                                            '1.9 GB', f'hash {infohash}'],
                                           ['white_check_mark', 'movin', 'testor@asusi7'], None)

            # ---
            print("--- bare movie file wrapped and moved")
            wrapped_handler = TorrentHandlorMovin.factory('movin', delugapi_torrent=bare_torrent,
                                                          survey_data=survey('single_file'),
                                                          browser_source_data=florist_record)
            wrapped_handler.is_renamed = True
            announcor = HookAnnouncor(logger)
            message_id = announcor.completed(bare_torrent, wrapped_handler, browser_source_data=florist_record,
                                             destination=str(wrapped_handler.destin_dir), refreshed=True)
            all_as_expected &= self._check(message_id, captured[-1], 'done: The Florist (2026)',
                                           ['in movies/movin', 'jellyfin refreshed', 'wrapped into the.florist.2026/',
                                            '1.5 GB', f'hash {infohash}'],
                                           ['white_check_mark', 'movin', 'testor@asusi7'], None)

            # ---
            print("--- moved with two diversions noted")
            diverted_handler = TorrentHandlorMovin.factory('movin', delugapi_torrent=florist_torrent,
                                                           survey_data=survey('single_directory'),
                                                           browser_source_data=florist_record)
            announcor = HookAnnouncor(logger)
            announcor.note('folder rename not reported after 60 rounds, moved as not renamed')
            announcor.note('not where expected for the Jellyfin refresh, none asked for')
            message_id = announcor.completed(florist_torrent, diverted_handler, browser_source_data=florist_record,
                                             destination=str(diverted_handler.destin_dir))
            all_as_expected &= self._check(message_id, captured[-1], 'done: The Florist (2026)',
                                           ['in movies/movin', 'jellyfin not refreshed',
                                            '! folder rename not reported after 60 rounds, moved as not renamed',
                                            '! not where expected for the Jellyfin refresh, none asked for',
                                            'as released: The Florist (2026)/', '1.9 GB', f'hash {infohash}'],
                                           ['white_check_mark', 'movin', 'warning', 'diverted', 'testor@asusi7'], 4)

            # ---
            print("--- moved, the Jellyfin refresh raised")
            announcor = HookAnnouncor(logger)
            refused_text = f"HTTPConnectionPool(host='10.4.9.11', port=8096): Max retries exceeded {'x' * 200}\nsecond line"
            try:
                raise requests.ConnectionError(refused_text)
            except Exception as exc:  # the note as on_completed words it
                announcor.note(f'jellyfin refresh failed: {type(exc).__name__}: {str(exc).partition("\n")[0][:200]}')
            message_id = announcor.completed(florist_torrent, florist_handler, browser_source_data=florist_record,
                                             destination=str(florist_handler.destin_dir))
            all_as_expected &= self._check(message_id, captured[-1], 'done: The Florist (2026)',
                                           ['in movies/movin', 'jellyfin not refreshed',
                                            f'! jellyfin refresh failed: ConnectionError: {refused_text[:200]}',
                                            'renamed to the.florist.2026/', '1.9 GB', f'hash {infohash}'],
                                           ['white_check_mark', 'movin', 'warning', 'diverted', 'testor@asusi7'], 4)

            # ---
            print("--- failed at rename, one diversion noted before")
            announcor = HookAnnouncor(logger)
            announcor.label = 'movin'
            announcor.stage = 'rename'
            announcor.note('survey missing, no torrent file to write it from')
            message_id = announcor.failed(announcor.stage, RuntimeError('rename transaction raised on purpose'),
                                          yts_folder)
            all_as_expected &= self._check(message_id, captured[-1], 'failed: The Florist (2026)',
                                           ['at rename: RuntimeError: rename transaction raised on purpose',
                                            '! survey missing, no torrent file to write it from'],
                                           ['x', 'movin', 'testor@asusi7'], 4)

            # ---
            print("--- removed, deleted and told to Jellyfin, named by the provenance record")
            announcor = HookAnnouncor(logger)
            message_id = announcor.removed('/ocean/video/movies/movin/the.florist.2026', 'deleted with 6 files', True,
                                           record=florist_record)
            all_as_expected &= self._check(message_id, captured[-1], 'removed: The Florist (2026)',
                                           ['deleted with 6 files, jellyfin told', 'folder movies/movin/the.florist.2026/'],
                                           ['wastebasket', 'testor@asusi7'], None)

            # ---
            print("--- removed, refused outside the movie library")
            refused_outcome = "refused: its download location is outside '/ocean/video/movies/movin'"
            announcor = HookAnnouncor(logger)
            message_id = announcor.removed(f'/ocean/video/tv/visionquest/s01/{tv_name}', refused_outcome, None)
            all_as_expected &= self._check(message_id, captured[-1], 'removed: VisionQuest S01E03 1080p x265-ELiTE',
                                           [refused_outcome, f'folder tv/visionquest/s01/{tv_name}/'],
                                           ['wastebasket', 'testor@asusi7'], None)

            # ---
            print("--- removed, deleted, the double-wrapped parent left for the hand, no provenance")
            moonrise_name = 'Moonrise Kingdom (2012) Criterion (2160p)'
            parent_diversion = "parent moonrise.kingdom.2012/ holds no video, left for the operator's hand"
            announcor = HookAnnouncor(logger)
            announcor.note(parent_diversion)
            message_id = announcor.removed(f'/ocean/video/movies/movin/moonrise.kingdom.2012/{moonrise_name}',
                                           'deleted with 7 files', True)
            all_as_expected &= self._check(message_id, captured[-1], f'removed: {moonrise_name}',
                                           ['deleted with 7 files, jellyfin told', f'! {parent_diversion}',
                                            f'folder movies/movin/moonrise.kingdom.2012/{moonrise_name}/'],
                                           ['wastebasket', 'warning', 'diverted', 'testor@asusi7'], 4)

            # ---
            print("--- removed, deleted, the Jellyfin call raised")
            announcor = HookAnnouncor(logger)
            try:
                raise requests.ConnectionError('refused on purpose')
            except Exception as exc:  # the note as on_removed words it
                announcor.note(f'jellyfin not told: {type(exc).__name__}: {str(exc).partition("\n")[0][:200]}')
            message_id = announcor.removed('/ocean/video/movies/movin/the.florist.2026', 'deleted with 6 files', False,
                                           record=florist_record)
            all_as_expected &= self._check(message_id, captured[-1], 'removed: The Florist (2026)',
                                           ['deleted with 6 files, jellyfin not told: call failed',
                                            '! jellyfin not told: ConnectionError: refused on purpose',
                                            'folder movies/movin/the.florist.2026/'],
                                           ['wastebasket', 'warning', 'diverted', 'testor@asusi7'], 4)
        finally:
            NtfyClient._request = original_request

        # ---
        print("--- one real send: the renamed and moved movie, tag test")
        announcor = TestorHookAnnouncor(logger)
        message_id = announcor.completed(florist_torrent, florist_handler, browser_source_data=florist_record,
                                         destination=str(florist_handler.destin_dir), refreshed=True)
        is_sent = message_id is not None
        all_as_expected = all_as_expected and is_sent
        print(f"real send id: {message_id}  failure: {announcor.failure}  {is_sent}")
        print(f"all as expected: {all_as_expected}")

    @staticmethod
    def _check(message_id, payload: dict, title: str, lines: list[str], tags: list[str], priority: int | None) -> bool:
        print(f"id: {message_id}  topic: {payload['topic']}")
        print(f"title: {payload.get('title')!r}")
        for line in payload['message'].split('\n'):
            print(f"  | {line}")
        print(f"tags: {payload.get('tags')}  priority: {payload.get('priority')}  click: {payload.get('click')}")
        is_as_expected = (
            message_id is not None
            and payload.get('title') == title
            and payload['message'].split('\n') == lines
            and payload.get('tags') == tags
            and payload.get('priority') == priority
            and 'click' not in payload
        )
        print(f"as expected: {is_as_expected}")
        return is_as_expected


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
