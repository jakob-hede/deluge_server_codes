from pathlib import Path
from time import sleep

import yaml
from twisted.internet.defer import Deferred

from .commons import Commons
from .logge import DelugapiTorrentorLoggor
from .torrenthandlor import TorrentLabelHandlor
from .torrentparsor import TorrentParsor

from delugapi.response import DelugApiResponse
from delugapi import DelugApi

from typing import Generator, Any
from twisted.internet import defer

from delugapi import DelugapiClient
from delugapi.transaction import DelugApiStatusTransaction, DelugApiMoveTransaction, DelugApiTransactionReplyWrapper
from delugapi.torrent import DelugapiTorrent


class Torrentor:
    torrents_dir: Path = Commons.singleton.deluge_root_dir / 'torrents'
    surveys_dir: Path = Commons.singleton.deluge_root_dir / 'surveys'

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
            self.on_added()
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

    def on_added(self):
        """Create a survey file when a torrent is added."""
        self.logger.info(f"Torrent '{self.torrent_name}' has been added..")
        torrent_file = self.torrents_dir / f"{self.torrent_name}.torrent"
        if torrent_file.exists():
            self.logger.info(f"SUCCES: Torrent file '{torrent_file}' exists")
        else:
            self.logger.info(f"Error: Torrent file '{torrent_file}' not found")
            return
        survey_data: dict = {}
        execute_args_data: dict = {
            'torrent_id': self.torrent_id,
            'torrent_name': self.torrent_name,
            'added_base_dir': self.base_sdir,
            'timestamp': Commons.singleton.timestamp(),
        }
        survey_data['execute_args'] = execute_args_data
        parsor = TorrentParsor(torrent_file)
        torrent_data = parsor.parse()
        survey_data['torrent_data'] = torrent_data
        self.survey_file_write_data(survey_data)

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

        @defer.inlineCallbacks
        def reactize() -> Generator[Any, Any, dict]:
            print('reactize')
            transaction = DelugApiStatusTransaction(torrent_id=self.torrent_id)
            reply = yield api_client.api.transactize(transaction)
            transaction_response = transaction.response
            print(f"transaction_response: {transaction_response}")
            torrent_status_dict: dict = transaction_response.result
            delugapi_torrent = DelugapiTorrent.from_dict(torrent_status_dict)
            print(f' - delugapi_torrent: {delugapi_torrent}')

            reply_wrapper = DelugApiTransactionReplyWrapper(reply)
            self.logger.remark(reply_wrapper.pressence)

            label = delugapi_torrent.label
            if label:
                print(f' - label: "{label}"')
                survey_data = self.survey_file_read_data()
                label_handler = TorrentLabelHandlor.factory(
                    label,
                    delugapi_torrent=delugapi_torrent,
                    survey_data=survey_data,
                )
                if label_handler:
                    torrent_id = delugapi_torrent.tid
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
                            if not destination_dir.is_dir():
                                destination_dir.mkdir(parents=True, exist_ok=True)
                            transaction = DelugApiMoveTransaction(torrent_id=torrent_id,
                                                                  destination=str(destination_sdir))
                            reply = yield api_client.api.transactize(transaction)
                            transaction_response = transaction.response
                            print(f"transaction_response: {transaction_response}")
                            # self.jellyfin_refresh(label, destination_str)
                        else:
                            self.logger.warning('Not at daemon, skipping move')
                    else:
                        self.logger.warning('Destination is the same as current move_completed_path, skipping move')
                    if label_handler.is_jellyable:
                        self.logger.exclaim(f'jellyfin_refresh')
                        sleep(5)  # wait for file move to complete
                        # self.logger.info(f'label            "{label}"')
                        # self.logger.info(f'destination_sdir "{destination_sdir}"')

                        transaction = DelugApiStatusTransaction(torrent_id=self.torrent_id)
                        reply = yield Commons.singleton.api_client.api.transactize(transaction)
                        transaction_response = transaction.response
                        print(f"transaction_response: {transaction_response}")
                        torrent_status_dict: dict = transaction_response.result
                        delugapi_torrent = DelugapiTorrent.from_dict(torrent_status_dict)
                        print(f' - delugapi_torrent: {delugapi_torrent}')

                        # from delugapi.transaction import DelugApiTransactionReplyWrapper
                        reply_wrapper = DelugApiTransactionReplyWrapper(reply)
                        self.logger.remark(reply_wrapper.pressence)

                        if Commons.singleton.is_at_daemon:
                            self.logger.info(f'jellyfin_refresh At daemon!')
                        print()

                        # x = self.fetch_delugapi_torrent()
                        # pass

                        # self.jellyfin_refresh()
                        # pass
                        # self.jellyfin_refresh(label, destination_str)

            self.reaction_response.result = transaction_response.result
            self.reaction_response.error = transaction_response.error

            # Reactor lifecycle is managed by delugapi_wrap / Twistor — do NOT stop here
            return reply

        self.reaction_response = DelugApiResponse()
        d = DelugApi.delugapi_wrap(reactize)
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
    # def jellyfin_refresh(self, label: str, destination: str) -> None:
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
