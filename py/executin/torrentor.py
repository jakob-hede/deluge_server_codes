from pathlib import Path
from time import sleep
import shutil

import yaml
from twisted.internet.defer import Deferred

from .announcor import HookAnnouncor
from .commons import Commons
from .jellyfin_communicator import JellyfinCommunicator
from .logge import DelugapiTorrentorLoggor
from .torrenthandlor import TorrentLabelHandlor, TorrentHandlorMovin
from .torrentparsor import TorrentParsor

from delugapi.response import DelugApiResponse
from delugapi import DelugApi

from typing import Generator, Any
from twisted.internet import defer

from delugapi import DelugapiClient
from delugapi.transaction import DelugApiStatusTransaction, DelugApiMoveTransaction, DelugApiLabelTransaction
from delugapi.transaction import DelugApiRenameFolderTransaction, DelugApiRenameFilesTransaction

type deferred_response = Generator[Any, Any, dict | None]


def move_cap_rounds(total_wanted: int) -> int:
    """Rounds of one second the move is waited for: 20 MiB/s, at least five minutes, at most one hour."""
    return max(300, min(3600, total_wanted // (20 * 1024 * 1024)))


class Torrentor:
    torrents_dir: Path = Commons.singleton.deluge_root_dir / 'torrents'
    surveys_dir: Path = Commons.singleton.deluge_root_dir / 'surveys'
    browser_source_dir: Path = Commons.singleton.deluge_root_dir / 'browser-source'

    def __init__(self, torrent_id, torrent_name, base_sdir):
        self.torrent_id: str = torrent_id
        self.torrent_name: str = torrent_name
        self.base_sdir: str = base_sdir
        self.logger = DelugapiTorrentorLoggor()
        self.reaction_response: DelugApiResponse = None

    def process_event(self, event_name):
        print(f"Processing event '{event_name}' for torrent '{self.torrent_name}' ({self.torrent_id})")
        # Here you would add logic to handle different events
        if event_name == 'exe_added':
            return self.on_added()
        elif event_name == 'exe_completed':
            return self.on_completed()
        elif event_name == 'exe_removed':
            self.on_removed()
        else:
            print(f"Unknown event: {event_name}")

    @property
    def survey_file(self) -> Path:
        return self.surveys_dir / f'{self.torrent_id}.yml'

    def survey_file_write_data(self, data: dict):
        survey_yaml = yaml.dump(data, sort_keys=False)
        if not self.surveys_dir.exists():
            self.surveys_dir.mkdir(parents=True, exist_ok=True)
        self.survey_file.write_text(survey_yaml)

    def survey_file_read_data(self) -> dict:
        if not self.survey_file.exists():
            print(f"Error: Survey file '{self.survey_file}' not found")
            return {}
        survey_yaml = self.survey_file.read_text()
        data: dict = yaml.safe_load(survey_yaml)
        return data

    def torrent_file_for(self, *names: str) -> Path | None:
        # the daemon names its copy of the torrent by the torrent's name when the metadata arrives,
        # which for a magnet is often not the name the added event carried
        looked_for: list[str] = []
        for name in names:
            if not name or name in looked_for:
                continue
            looked_for.append(name)
            torrent_file = self.torrents_dir / f'{name}.torrent'
            if torrent_file.exists():
                return torrent_file
        return None

    def survey_write(self, torrent_file: Path, event_name: str) -> dict:
        survey_data: dict = {}
        execute_args_data: dict = {
            'torrent_id': self.torrent_id,
            'torrent_name': self.torrent_name,
            'added_base_dir': self.base_sdir,
            'timestamp': Commons.singleton.timestamp(),
            'event': event_name,
            'torrent_file': str(torrent_file),
        }
        survey_data['execute_args'] = execute_args_data
        parsor = TorrentParsor(torrent_file)
        torrent_data = parsor.parse()
        survey_data['torrent_data'] = torrent_data
        self.survey_file_write_data(survey_data)
        return survey_data

    @property
    def browser_source_file(self) -> Path:
        return self.browser_source_dir / f'{self.torrent_id}.yml'

    def browser_source_file_read_data(self) -> dict:
        if not self.browser_source_file.exists():
            print(f"Error: Browser-source file '{self.browser_source_file}' not found")
            return {}
        browser_source_yaml = self.browser_source_file.read_text()
        data: dict = yaml.safe_load(browser_source_yaml)
        return data

    def on_added(self) -> Deferred:
        """Create a survey file when a torrent is added."""
        self.logger.info(f"Torrent '{self.torrent_name}' has been added..")

        api_client: DelugapiClient = Commons.singleton.api_client

        @defer.inlineCallbacks
        def reactize() -> deferred_response:
            print('reactize')
            transaction = None
            reply = {}
            browser_source_data = self.browser_source_file_read_data()
            label_hint = browser_source_data.get('label_hint') if browser_source_data else None
            if not browser_source_data:
                self.logger.info(f"No browser-source file '{self.browser_source_file}', skipping label")
            elif label_hint not in ('movin', 'tv-in', 'tv-arc'):
                self.logger.info(f"Browser-source label_hint '{label_hint}' is not a label, skipping label")
            else:
                self.logger.info(f"Browser-source label_hint '{label_hint}' from '{self.browser_source_file}'")
                transaction = DelugApiStatusTransaction(torrent_id=self.torrent_id)
                reply = yield api_client.api.transactize(transaction)
                delugapi_torrent = transaction.delugapi_torrent_from_status()
                print(f' - delugapi_torrent: {delugapi_torrent}')
                self.logger.remark(transaction.pressence)

                if delugapi_torrent is None:
                    self.logger.warning(f"No status for torrent '{self.torrent_id}', skipping label")
                elif delugapi_torrent.label:
                    self.logger.info(
                        f'Label "{delugapi_torrent.label}" already set, hand-set label wins, skipping "{label_hint}"')
                else:
                    self.logger.info(f'Setting label "{label_hint}" for "{delugapi_torrent.title}"')
                    transaction = DelugApiLabelTransaction(torrent_id=self.torrent_id, label=label_hint)
                    reply = yield api_client.api.transactize(transaction)
                    transaction_response = transaction.response
                    print(f"transaction_response: {transaction_response}")
                    if transaction_response.error:
                        self.logger.error(f"Error setting label: {transaction_response.error}")
                    else:
                        self.logger.remark(f"Dispatched label '{label_hint}' for {delugapi_torrent.name}")

                    transaction = DelugApiStatusTransaction(torrent_id=self.torrent_id)
                    reply = yield api_client.api.transactize(transaction)
                    updated_torrent = transaction.delugapi_torrent_from_status()
                    current_label = updated_torrent.label if updated_torrent else None
                    self.logger.info(f"Current label: '{current_label}'")

            if transaction is not None:
                self.reaction_response.result = transaction.response.result
                self.reaction_response.error = transaction.response.error

            # a magnet's copy is written only when the metadata arrives, under the name the daemon reports from then on
            torrent_file = None
            daemon_name = ''
            top = 120
            for i in range(1, top + 1):
                transaction = DelugApiStatusTransaction(torrent_id=self.torrent_id)
                reply = yield api_client.api.transactize(transaction)
                updated_torrent = transaction.delugapi_torrent_from_status()
                daemon_name = updated_torrent.name if updated_torrent else ''
                torrent_file = self.torrent_file_for(daemon_name, self.torrent_name)
                if torrent_file is not None:
                    self.logger.info(f"SUCCES: Torrent file '{torrent_file}' exists ({i}/{top})")
                    break
                if i == 1 or i % 10 == 0:
                    self.logger.info(
                        f"Waiting for torrent file... ({i}/{top}) under '{daemon_name}' or '{self.torrent_name}'")
                sleep(1)
            if torrent_file is None:
                self.logger.warning(
                    f"Error: Torrent file not found after {top} rounds under '{daemon_name}' or '{self.torrent_name}', no survey")
                return
            self.survey_write(torrent_file, 'exe_added')

            # Reactor lifecycle is managed by delugapi_wrap / Twistor — do NOT stop here
            return reply

        self.reaction_response = DelugApiResponse()
        d = DelugApi.delugapi_wrap(reactize)
        if d is not None:
            print(f"on_added: Deferred pending (reactor already running)")
        else:
            print(f"on_added response: {self.reaction_response}")
        return d

    # def _x_fetch_delugapi_torrent(self) -> DelugapiTorrent:
    #     print('fetch_delugapi_torrent')
    #
    #     # api_client: DelugapiClient = Commons.singleton.api_client
    #     fetched = {}
    #
    #     @defer.inlineCallbacks
    #     def fetch() -> Generator[Any, Any, dict]:
    #         transaction_ = DelugApiStatusTransaction(torrent_id=self.torrent_id)
    #         reply_ = yield Commons.singleton.api_client.api.transactize(transaction_)
    #         fetched['transaction'] = transaction_
    #         fetched['reply'] = reply_
    #         # return transaction_, reply_
    #         return reply_
    #
    #     # transaction, reply = yield fetch()
    #
    #     reply = yield fetch()
    #     transaction_response = fetched['transaction'].response
    #     print(f"transaction_response: {transaction_response}")
    #     torrent_status_dict: dict = transaction_response.result
    #     delugapi_torrent = DelugapiTorrent.from_dict(torrent_status_dict)
    #     print(f' - delugapi_torrent: {delugapi_torrent}')
    #     return delugapi_torrent
    #
    # @defer.inlineCallbacks
    # def fetch_delugapi_torrent(self) -> Generator[Any, Any, dict]:
    #     transaction = DelugApiStatusTransaction(torrent_id=self.torrent_id)
    #     reply = yield Commons.singleton.api_client.api.transactize(transaction)
    #     transaction_response = transaction.response
    #     print(f"transaction_response: {transaction_response}")
    #     torrent_status_dict: dict = transaction_response.result
    #     delugapi_torrent = DelugapiTorrent.from_dict(torrent_status_dict)
    #     print(f' - delugapi_torrent: {delugapi_torrent}')
    #     return reply

    def on_completed(self) -> Deferred:  # Generator[Any, Any, dict]
        print(f"Torrentor '{self.torrent_name}' has completed downloading..")
        # from typing import Generator, Any
        # from twisted.internet import defer
        #
        # from delugapi import DelugapiClient
        # from delugapi.transaction import DelugApiStatusTransaction, DelugApiMoveTransaction
        # from delugapi.torrent import DelugapiTorrent

        api_client: DelugapiClient = Commons.singleton.api_client
        announcor = HookAnnouncor(self.logger)

        @defer.inlineCallbacks
        def reactize() -> deferred_response:
            print('reactize')
            # carried to the announce at the end, each set where its branch knows it
            label_handler = None
            browser_source_data = None
            announce_destination = None
            announce_refreshed = None
            announce_not_moved = None
            transaction = DelugApiStatusTransaction(torrent_id=self.torrent_id)
            reply = yield api_client.api.transactize(transaction)
            # transaction_response = transaction.response
            # print(f"transaction_response: {transaction_response}")
            # torrent_status_dict: dict = transaction_response.result
            # delugapi_torrent = DelugapiTorrent.from_dict(torrent_status_dict)
            delugapi_torrent = transaction.delugapi_torrent_from_status()
            print(f' - delugapi_torrent: {delugapi_torrent}')
            self.logger.remark(transaction.pressence)

            label = delugapi_torrent.label
            announcor.label = label
            if label:
                print(f' - label: "{label}"')
                announcor.stage = 'survey'
                survey_data = self.survey_file_read_data()
                if not survey_data:
                    # the added event found no copy of the torrent, at completion the metadata is certain
                    torrent_file = self.torrent_file_for(delugapi_torrent.name, self.torrent_name)
                    if torrent_file is not None:
                        survey_data = self.survey_write(torrent_file, 'exe_completed')
                        self.logger.info(f"Survey missing at completed, written now from '{torrent_file}'")
                    else:
                        self.logger.warning(
                            f"Survey missing at completed, no torrent file under '{delugapi_torrent.name}' or '{self.torrent_name}'")
                        announcor.note('survey missing, no torrent file to write it from')
                browser_source_data = self.browser_source_file_read_data()
                label_handler = TorrentLabelHandlor.factory(
                    label,
                    delugapi_torrent=delugapi_torrent,
                    survey_data=survey_data,
                    browser_source_data=browser_source_data,
                )
                if label_handler:
                    torrent_id = delugapi_torrent.tid
                    announcor.stage = 'rename'
                    rename_plan = label_handler.rename_plan
                    if rename_plan is None and label_handler.is_in_pattern_dir:
                        label_handler.is_renamed = True
                        self.logger.info(f'Already in pattern folder "{label_handler.pattern_dir_name}/", no rename')
                    elif rename_plan is not None:
                        if Commons.singleton.is_at_daemon:
                            self.logger.info(f'At daemon, renaming by plan {rename_plan} ...')
                            new_folder = f'{label_handler.pattern_dir_name}/'
                            # a folder plan is a (folder, new_folder) tuple, a files plan a list of (index, new_path)
                            if isinstance(rename_plan, tuple):
                                folder, new_folder = rename_plan
                                transaction = DelugApiRenameFolderTransaction(torrent_id=torrent_id,
                                                                              folder=folder,
                                                                              new_folder=new_folder)
                            else:
                                transaction = DelugApiRenameFilesTransaction(torrent_id=torrent_id,
                                                                             filenames=rename_plan)
                            reply = yield api_client.api.transactize(transaction)
                            transaction_response = transaction.response
                            print(f"transaction_response: {transaction_response}")
                            if transaction_response.error:
                                self.logger.error(f"Error renaming, moving as not renamed: {transaction_response.error}")
                                announcor.note('folder rename failed, moved as not renamed')
                            else:
                                self.logger.remark(
                                    f"Dispatched renaming {delugapi_torrent.name} to '{new_folder}', {str(transaction_response).strip()}")
                                top = 60
                                for i in range(1, top + 1):
                                    transaction = DelugApiStatusTransaction(torrent_id=self.torrent_id)
                                    reply = yield api_client.api.transactize(transaction)
                                    updated_torrent = transaction.delugapi_torrent_from_status()
                                    current_paths = [file['path'] for file in updated_torrent.files] if updated_torrent else []
                                    first_path = current_paths[0] if current_paths else ''
                                    self.logger.info(f"Waiting for rename to complete... ({i}/{top}) first path: '{first_path}'")
                                    if current_paths and all(path.startswith(new_folder) for path in current_paths):
                                        label_handler.is_renamed = True
                                        label_handler.current_files = updated_torrent.files
                                        self.logger.info("Rename completed successfully!")
                                        break
                                    sleep(1)
                                if not label_handler.is_renamed:
                                    self.logger.warning(f'Rename not reported after {top} rounds, moving as not renamed')
                                    announcor.note(f'folder rename not reported after {top} rounds, moved as not renamed')
                        else:
                            self.logger.warning('Not at daemon, skipping rename')
                    announcor.stage = 'file renames'
                    # the files are renamed only inside a confirmed pattern folder, a failed folder rename nests as before
                    if label_handler.is_renamed:
                        if Commons.singleton.is_at_daemon:
                            file_plan = label_handler.file_rename_plan(label_handler.latest_files)
                            if file_plan:
                                self.logger.info(f'At daemon, renaming files by plan {file_plan} ...')
                                transaction = DelugApiRenameFilesTransaction(torrent_id=torrent_id,
                                                                             filenames=file_plan)
                                reply = yield api_client.api.transactize(transaction)
                                transaction_response = transaction.response
                                print(f"transaction_response: {transaction_response}")
                                if transaction_response.error:
                                    self.logger.warning(f"Error renaming files, moving as named: {transaction_response.error}")
                                    announcor.note('file renames failed, moved as named')
                                else:
                                    self.logger.remark(
                                        f"Dispatched renaming {len(file_plan)} files, {str(transaction_response).strip()}")
                                    planned_paths = dict(file_plan)
                                    is_files_renamed = False
                                    top = 60
                                    for i in range(1, top + 1):
                                        transaction = DelugApiStatusTransaction(torrent_id=self.torrent_id)
                                        reply = yield api_client.api.transactize(transaction)
                                        updated_torrent = transaction.delugapi_torrent_from_status()
                                        current_paths = {file['index']: file['path'] for file in updated_torrent.files} if updated_torrent else {}
                                        done_count = sum(current_paths.get(index) == path for index, path in planned_paths.items())
                                        self.logger.info(f"Waiting for file renames to complete... ({i}/{top}) {done_count}/{len(planned_paths)} done")
                                        if done_count == len(planned_paths):
                                            label_handler.current_files = updated_torrent.files
                                            is_files_renamed = True
                                            self.logger.info("File renames completed successfully!")
                                            break
                                        sleep(1)
                                    if not is_files_renamed:
                                        if updated_torrent:
                                            label_handler.current_files = updated_torrent.files
                                        self.logger.warning(f'File renames not reported after {top} rounds, moving as named')
                                        announcor.note(f'file renames not reported after {top} rounds, moved as named')
                        else:
                            self.logger.warning('Not at daemon, skipping file renames')
                    announcor.stage = 'move'
                    destination_dir = label_handler.destin_dir
                    origin_dir = delugapi_torrent.download_location
                    destination_sdir = str(destination_dir)
                    origin_sdir = str(origin_dir)
                    print(f'origin: "{origin_sdir}"')
                    current_sdir = origin_sdir
                    self.logger.info(
                        f'Handling labelled torrent: "{label}" "{delugapi_torrent.title}" to "{destination_sdir}"')

                    if destination_sdir != delugapi_torrent.download_location:
                        if Commons.singleton.is_at_daemon:
                            self.logger.info(f'At daemon, moving torrent from "{origin_sdir}" ...')
                            pattern_dir = label_handler.pattern_dir
                            if pattern_dir is not None and pattern_dir.exists():
                                self.logger.warning(
                                    f'Pattern folder "{pattern_dir}" already exists, moving anyway, its files are not replaced')
                                announcor.note(f'pattern folder {pattern_dir.name}/ already existed, its files not replaced')
                            sidecar_dir = label_handler.sidecar_dir
                            if sidecar_dir is not None:
                                self.logger.info(f"Writing sidecars to '{sidecar_dir}' before the move")
                                sidecar_paths = label_handler.write_sidecars(sidecar_dir)
                                if not sidecar_paths:
                                    announcor.note('no sidecar written')
                            if not destination_dir.is_dir():
                                destination_dir.mkdir(parents=True, exist_ok=True)
                            transaction = DelugApiMoveTransaction(torrent_id=torrent_id,
                                                                  destination=str(destination_sdir))
                            reply = yield api_client.api.transactize(transaction)
                            transaction_response = transaction.response
                            print(f"transaction_response: {transaction_response}")
                            # # self.jellyfin_refresh(label, destination_str)
                            # if transaction_response.error:
                            #     self.logger.error(f"Error moving torrent: {transaction_response.error}")
                            # elif transaction_response.is_valid:
                            self.logger.remark(f"Dispatched moving {delugapi_torrent.name} to '{destination_sdir}'")
                            sleep(0.1)
                            top = move_cap_rounds(delugapi_torrent.total_wanted)
                            self.logger.info(f"Move cap {top} rounds for {delugapi_torrent.total_wanted} bytes")
                            for i in range(1, top):
                                self.logger.info(f"Waiting for move to complete... ({i}/{top})")
                                # Check if move is complete by verifying the torrent's current download location
                                transaction = DelugApiStatusTransaction(torrent_id=self.torrent_id)
                                reply = yield api_client.api.transactize(transaction)
                                updated_torrent = transaction.delugapi_torrent_from_status()
                                # transaction_response = transaction.response
                                # torrent_status_dict: dict = transaction_response.result
                                # updated_torrent = DelugapiTorrent.from_dict(torrent_status_dict)
                                current_sdir = updated_torrent.download_location
                                self.logger.info(f"Current download location: '{current_sdir}'")
                                if current_sdir == destination_sdir:
                                    self.logger.info("Move completed successfully!")
                                    announce_destination = destination_sdir
                                    break
                                sleep(1)
                            if current_sdir != destination_sdir:
                                announcor.note(f'move not reported after {top - 1} rounds')
                                announce_not_moved = 'move not confirmed'
                        else:
                            self.logger.warning('Not at daemon, skipping move')
                            announce_not_moved = 'not at daemon'
                    else:
                        self.logger.warning('Destination is the same as current move_completed_path, skipping move')
                        announce_not_moved = 'already at the destination'
                    announcor.stage = 'refresh'
                    if label_handler.is_jellyable:
                        self.logger.exclaim(f'jellyfin_refresh: {destination_sdir}')

                        transaction = DelugApiStatusTransaction(torrent_id=self.torrent_id)
                        reply = yield api_client.api.transactize(transaction)
                        updated_torrent = transaction.delugapi_torrent_from_status()
                        # transaction_response = transaction.response
                        # torrent_status_dict: dict = transaction_response.result
                        # updated_torrent = DelugapiTorrent.from_dict(torrent_status_dict)
                        current_sdir = updated_torrent.download_location
                        self.logger.info(f"Current download location: '{current_sdir}'")
                        if current_sdir == destination_sdir:
                            self.logger.info(
                                f'Media is in expected location for Jellyfin refresh: "{destination_sdir}"')
                            dev_mode = True
                            if dev_mode or Commons.singleton.is_at_daemon:
                                self.logger.info(f'jellyfin_refresh At daemon!  {destination_sdir}')
                                try:
                                    self.jellyfin_refresh(label_handler, destination_sdir)
                                    announce_refreshed = True
                                except Exception as exc:
                                    announcor.note(f'jellyfin refresh failed: {type(exc).__name__}: {str(exc).partition("\n")[0][:200]}')
                        else:
                            self.logger.warning(f'Media is NOT in expected location for Jellyfin refresh: '
                                                f'Expected: "{destination_sdir}"'
                                                f'Current: "{current_sdir}"')
                            announcor.note('not where expected for the Jellyfin refresh, none asked for')

                        # sleep(5)  # wait for file move to complete
                        # # self.logger.info(f'label            "{label}"')
                        # # self.logger.info(f'destination_sdir "{destination_sdir}"')
                        #
                        # transaction = DelugApiStatusTransaction(torrent_id=self.torrent_id)
                        # reply = yield Commons.singleton.api_client.api.transactize(transaction)
                        # transaction_response = transaction.response
                        # print(f"transaction_response: {transaction_response}")
                        # torrent_status_dict: dict = transaction_response.result
                        # delugapi_torrent = DelugapiTorrent.from_dict(torrent_status_dict)
                        # print(f' - delugapi_torrent: {delugapi_torrent}')
                        #
                        # # from delugapi.transaction import DelugApiTransactionReplyWrapper
                        # reply_wrapper = DelugApiTransactionReplyWrapper(reply)
                        # self.logger.remark(reply_wrapper.pressence)

                        # if Commons.singleton.is_at_daemon:
                        #     self.logger.info(f'jellyfin_refresh At daemon!  {destination_sdir}')
                        print()

                        # x = self.fetch_delugapi_torrent()
                        # pass

                        # self.jellyfin_refresh()
                        # pass
                        # self.jellyfin_refresh(label, destination_str)

            announced = announcor.completed(delugapi_torrent, label_handler,
                                            browser_source_data=browser_source_data,
                                            destination=announce_destination,
                                            refreshed=announce_refreshed,
                                            not_moved=announce_not_moved)
            if announced:
                self.logger.info(f'Announced {announced}')

            self.reaction_response.result = transaction.response.result
            self.reaction_response.error = transaction.response.error

            # self.reaction_response.result = transaction_response.result
            # self.reaction_response.error = transaction_response.error

            # Reactor lifecycle is managed by delugapi_wrap / Twistor — do NOT stop here
            return reply

        @defer.inlineCallbacks
        def announced_reactize() -> deferred_response:
            # the one place the completed hook dies: the twistor catches whatever reactize raises,
            # so the failure is announced here and raised on, the outcome as it was
            try:
                reply = yield reactize()
            except Exception as exc:
                announcor.failed(announcor.stage, exc, self.torrent_name)
                raise
            return reply

        self.reaction_response = DelugApiResponse()
        d = DelugApi.delugapi_wrap(announced_reactize)
        if d is not None:
            print(f"on_completed: Deferred pending (reactor already running)")
        else:
            print(f"on_completed response: {self.reaction_response}")
        return d

    # def jellyfin_refresh(self):
    #     self.logger.exclaim(f'jellyfin_refresh')
    #     # self.logger.info(f'label            "{label}"')
    #     # self.logger.info(f'destination_sdir "{destination_sdir}"')
    #
    #     transaction = DelugApiStatusTransaction(torrent_id=self.torrent_id)
    #     reply = yield Commons.singleton.api_client.api.transactize(transaction)
    #     transaction_response = transaction.response
    #     print(f"transaction_response: {transaction_response}")
    #     torrent_status_dict: dict = transaction_response.result
    #     delugapi_torrent = DelugapiTorrent.from_dict(torrent_status_dict)
    #     print(f' - delugapi_torrent: {delugapi_torrent}')
    #
    #     from delugapi.transaction import DelugApiTransactionReplyWrapper
    #     reply_wrapper = DelugApiTransactionReplyWrapper(reply)
    #     print(reply_wrapper.pressence)
    #
    #     if Commons.singleton.is_at_daemon:
    #         self.logger.info(f'jellyfin_refresh At daemon!')
    #     print()

    # # TODO: implement actual Jellyfin API call
    # # POST http://<jellyfin_host>:8096/Library/Refresh
    # # Header: Authorization: MediaBrowser Token="<api_key>"
    def jellyfin_refresh(self, label_handler: TorrentLabelHandlor, destination: str) -> None:
        label = label_handler.label
        library_name = label_handler.jelly_library_name
        title = label_handler.title
        self.logger.exclaim(f'jellyfin_refresh: "{label}" "{library_name}" "{destination}"')
        communicator = JellyfinCommunicator()
        communicator.refresh_library(library_name, title=title)

    #     """Trigger a Jellyfin library rescan after moving media."""
    #     media_labels = ('movin', 'tv-in', 'tv-arc')
    #     if label not in media_labels:
    #         self.logger.debug(f'Skipping Jellyfin refresh for non-media label "{label}"')
    #         return
    #     self.logger.info(f'Jellyfin library refresh triggered for "{label}" at "{destination}"')
    #     # TODO: replace with actual HTTP call:
    #     # from urllib.request import Request, urlopen
    #     # req = Request('http://<host>:8096/Library/Refresh', method='POST')
    #     # req.add_header('Authorization', 'MediaBrowser Token="<api_key>"')
    #     # urlopen(req)

    def on_removed(self):
        self.logger.info(f"Torrent '{self.torrent_name}' has been removed..")
        folder = Path(self.base_sdir) / self.torrent_name
        self.remove_emptied_folder(folder, TorrentHandlorMovin._destin_dir)

    def remove_emptied_folder(self, folder: Path, library_dir: Path, top: int = 60) -> bool:
        # a remove with data deletes only the torrent's own files, so the folder keeps what Jellyfin and the
        # sidecars put there; it goes once no video is left in it, and never anything outside the library
        library = library_dir.resolve()
        if '..' in folder.parts:
            self.logger.info(f"Not removing '{folder}', its path climbs with '..'")
            return False
        if folder.resolve() == library:
            self.logger.info(f"Not removing '{folder}', it is the library itself")
            return False
        if not folder.parent.resolve().is_relative_to(library):
            self.logger.info(f"Not removing '{folder}', its download location is outside '{library_dir}'")
            return False
        if folder.is_symlink():
            self.logger.info(f"Not removing '{folder}', it is a symlink")
            return False
        if not folder.exists():
            self.logger.info(f"Not removing '{folder}', it does not exist")
            return False
        if not folder.is_dir():
            self.logger.info(f"Not removing '{folder}', it is not a directory")
            return False
        resolved_folder = folder.resolve()
        if resolved_folder == library or not resolved_folder.is_relative_to(library):
            self.logger.info(f"Not removing '{folder}', it resolves to '{resolved_folder}', not below '{library_dir}'")
            return False

        # libtorrent deletes the data in its own thread after the event, so the video may still be going
        video_extensions = TorrentHandlorMovin.video_extensions
        videos: list[Path] | None = None
        for i in range(1, top + 1):
            try:
                videos = [path for path in folder.rglob('*') if path.suffix.lower() in video_extensions and path.is_file()]
            except OSError:
                videos = None
            if videos == []:
                self.logger.info(f"No video left in '{folder}' ({i}/{top})")
                break
            if i == 1 or i % 10 == 0:
                videos_text = 'scan interrupted' if videos is None else f"{len(videos)} video, first '{videos[0].relative_to(folder)}'"
                self.logger.info(f"Waiting for the video to go... ({i}/{top}) {videos_text}")
            sleep(1)
        if videos != []:
            self.logger.info(f"Video still in '{folder}' after {top} rounds, left as a remove without data")
            return False

        if not folder.exists():
            self.logger.info(f"'{folder}' is gone already, nothing to delete")
            return False
        left = sorted(str(path.relative_to(folder)) for path in folder.rglob('*'))
        self.logger.info(f"Deleting '{folder}' with what is left: {left}")
        try:
            shutil.rmtree(folder)
        except OSError as e:
            self.logger.error(f"Error deleting '{folder}': {e}")
            return False
        self.logger.remark(f"Deleted '{folder}'")

        # a double-wrapped folder's parent is below the library too, it is left for the operator's hand
        parent = folder.parent
        if parent.resolve() != library:
            parent_videos = [path for path in parent.rglob('*') if path.suffix.lower() in video_extensions and path.is_file()]
            if not parent_videos:
                self.logger.warning(f"Parent '{parent}' holds no video, left for the operator's hand")
        return True


