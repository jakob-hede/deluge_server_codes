from pathlib import Path

import yaml

from .commons import Commons
from .logge import DelugapiTorrentorLoggor
from .torrenthandlor import TorrentLabelHandlor
from .torrentparsor import TorrentParsor

from delugapi.response import DelugApiResponse
from delugapi import DelugApi


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
            self.on_completed()
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

    def on_completed(self):
        print(f"Torrentor '{self.torrent_name}' has completed downloading..")
        from typing import Generator, Any
        from twisted.internet import defer  # , reactor  # noqa

        from delugapi import DelugapiClient
        # from pydelu.delugapi.response import DelugApiResponse
        # from pydelu.delugapi import DelugApi
        # from delugapi import DelugApiStatusTransaction, DelugApiMoveTransaction
        from delugapi.transaction import DelugApiStatusTransaction, DelugApiMoveTransaction
        from delugapi.torrent import DelugapiTorrent

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
                    destination_str = str(destination_dir)
                    origin_str = str(origin_dir)
                    print(f'origin: "{origin_str}"')
                    self.logger.info(
                        f'Handling labelled torrent: "{label}" "{delugapi_torrent.title}" to "{destination_str}"')

                    if destination_str != delugapi_torrent.download_location:
                        if Commons.singleton.is_at_daemon:
                            self.logger.info(f'At daemon, moving torrent from "{origin_str}" ...')
                            if not destination_dir.is_dir():
                                destination_dir.mkdir(parents=True, exist_ok=True)
                            transaction = DelugApiMoveTransaction(torrent_id=torrent_id,
                                                                  destination=str(destination_str))
                            reply = yield api_client.api.transactize(transaction)
                            transaction_response = transaction.response
                            print(f"transaction_response: {transaction_response}")
                        else:
                            self.logger.warning('Not at daemon, skipping move')
                    else:
                        self.logger.warning('Destination is the same as current move_completed_path, skipping move')

            self.reaction_response.result = transaction_response.result
            self.reaction_response.error = transaction_response.error

            # reactor.stop()  # noqa
            DelugApi.delugapi_stop()
            return reply

        self.reaction_response = DelugApiResponse()
        DelugApi.delugapi_wrap(reactize)
        response = self.reaction_response

        print(f"on_completed response: {response}")

    def on_removed(self):
        self.logger.info(f"Torrent '{self.torrent_name}' has been removed..")
