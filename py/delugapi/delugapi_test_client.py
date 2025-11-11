import json
from pathlib import Path
from typing import Generator, Any

from delugapi import DelugapiClient, DelugApi
from delugapi.response import DelugApiResponse, IncompleteDelugApiResponse
from delugapi.torrent import DelugapiTorrent
from delugapi.transaction import DelugApiTransaction, DelugApiStatusTransaction
from delugapi.transaction_twistee import DelugApiStatusTransactionTwistee
from delugapi.twistin_adaptors import DelugApiTwistee, defer_inline_callbacks, ReactorInterface, defer_return_value


class DelugapiTestClient(DelugapiClient):
    def test3_seasonality(self) -> DelugApiResponse:

        print("DelugapiClient test3_seasonality method called")
        self.reaction_response = DelugApiResponse()
        DelugApi.delugapi_wrap(self.get_status_wrapped)

        response = self.reaction_response
        print(f"response: {response}")
        # dumps_dir = self.deluge_root_dir / 'dumps'
        if response.is_ok and isinstance(response.result, dict):
            for indx, (torrent_id, torrent_dict) in enumerate(response.result.items()):
                torrent__status_dict = {torrent_id: torrent_dict}
                delugapi_torrent = DelugapiTorrent.from_dict(torrent__status_dict)
                label = delugapi_torrent.label
                if label and label in 'donin movin':
                    continue
                name = delugapi_torrent.name
                tid = delugapi_torrent.tid
                title = delugapi_torrent.title

                base_sdir = Path(delugapi_torrent.download_location)
                destination_str = ''

                # region label_handler
                if label:
                    from executin.torrentor import Torrentor
                    from executin.torrenthandlor import TorrentLabelHandlor
                    torrentor = Torrentor(torrent_id, name, base_sdir)
                    survey_data = torrentor.survey_file_read_data()
                    label_handler = TorrentLabelHandlor.factory(
                        label,
                        delugapi_torrent=delugapi_torrent,
                        survey_data=survey_data,
                        quiet=True,
                    )
                    if label_handler:
                        destination_dir = label_handler.destin_dir
                        video_base_dir = Path('/ocean/video')
                        destination_relative_dir = destination_dir.relative_to(video_base_dir)
                        destination_str = str(destination_relative_dir)
                # endregion label_handler

                label_part = f'label="{label}", ' if label else ''
                season_episode_part = f'"{delugapi_torrent.season_episode_code}", ' if delugapi_torrent.season_episode_code else ''
                season_part = f'"{delugapi_torrent.season_code}", ' if delugapi_torrent.season_code else ''
                destination_part = f'"{destination_str}", ' if destination_str else ''
                print(
                    f' - {indx:03d}, '
                    f'{label_part:<22}'
                    f'{season_episode_part:<10}'
                    f'{season_part:<8}'
                    f'{destination_part:>16}'
                    f'title="{title}"'
                )

        return self.reaction_response

    def test2_status(self) -> DelugApiResponse:
        print("DelugapiClient test2_status method called")
        self.reaction_response = DelugApiResponse()
        DelugApi.delugapi_wrap(self.get_status_wrapped)  # Wrap the call to run in reactor
        self.handle_status_reaction_response()
        return self.reaction_response

    def test5_status(self) -> DelugApiResponse:
        self.loggor.exclaim('DelugapiClient test5_status method called')
        self.reaction_response = DelugApiResponse()
        # from delugapi.transaction_twistee import DelugApiStatusTransactionTwistee
        twistee: DelugApiTwistee = DelugApiStatusTransactionTwistee(self.api)
        # twistor = DelugApiTwistor(twistee)
        # response: DelugApiResponse = twistor.executize()
        # self.reaction_response = response
        # self.handle_status_reaction_response()
        # return response
        response = self.twistorize(twistee)
        self.reaction_response = response
        self.handle_status_reaction_response()
        return response

    def test6_id_status(self) -> DelugApiResponse:
        api = self.api

        # , torrent_id: str = ''

        class Test6Twistee(DelugApiTwistee):
            def __init__(self) -> None:
                super().__init__()
                self.transaction: DelugApiTransaction = DelugApiStatusTransaction(torrent_id='')

            # @abstractmethod
            # @defer.inlineCallbacks
            @defer_inline_callbacks
            def main_twistee_func(self, reactor_clock: ReactorInterface) -> Generator[Any, Any, DelugApiResponse]:
                status_dict = yield api.transactize(self.transaction)
                response = DelugApiResponse(result=status_dict)
                sample_id = self.handle_status_reaction_response(response)
                sub_transaction: DelugApiTransaction = DelugApiStatusTransaction(torrent_id=sample_id)
                transaction_status_dict = yield api.transactize(sub_transaction)
                sample_status_dict = transaction_status_dict.get(sample_id, {})
                name = sample_status_dict.get('name', '')
                self.loggor.remark(f'Sample Torrent Name for id="{sample_id}": {name}')
                # defer.returnValue(response)
                defer_return_value(response)

            def handle_status_reaction_response(self, response):
                print(f"response: {response}")
                sample_id = ''
                if response.is_ok and isinstance(response.result, dict):
                    self.loggor.remark('Torrents Status:')
                    for indx, (torrent_id, torrent_dict) in enumerate(response.result.items()):
                        label = torrent_dict["label"]
                        label_part = f'  label: "{label}"  ' if label else ''
                        name = torrent_dict['name']
                        truncated_name = f'{name[:36]} ...' if len(name) > 40 else name
                        self.loggor.info(
                            f' - {indx:03d}:'
                            f'{label_part:<20}'
                            f'name: "{truncated_name}"'
                            # f')'
                        )
                        if indx < 1:
                            sample_id = torrent_id
                        elif indx > 5:
                            print('...')
                            break
                self.loggor.remark(f'sample_id: "{sample_id}"')
                return sample_id

        self.loggor.exclaim('DelugapiClient test6_id_status method called')
        self.reaction_response = IncompleteDelugApiResponse()
        # twistee: DelugApiTwistee = DelugApiStatusTransactionTwistee(self.api)
        twistee: DelugApiTwistee = Test6Twistee()
        self.reaction_response = self.twistorize(twistee)
        # self.handle_status_reaction_response()
        return self.reaction_response

        return self.reaction_response

    #     self.loggor.exclaim('DelugapiClient test6_id_status method called')
    #     self.reaction_response = DelugApiResponse()  # dummy init
    #     twistee: DelugApiTwistee = DelugApiStatusTransactionTwistee(self.api, torrent_id=torrent_id)
    #     response = self.twistorize(twistee)
    #     self.reaction_response = response
    #     self.handle_status_reaction_response()
    #     return response

    def test2_json(self) -> DelugApiResponse:
        print("DelugapiClient test2_json method called")
        transaction = DelugApiStatusTransaction()
        response = self.api.transactize(transaction)
        print(f"response: {response}")
        dumps_dir = Path('/data/dumps')
        if response.is_ok and isinstance(response.result, dict):
            for indx, (torrent_id, torrent_dict) in enumerate(response.result.items()):
                label = torrent_dict["label"]
                label_part = f'label="{label}, " ' if label else ''
                print(
                    f' - {indx} TorrentInfo(id={torrent_id[:40]}, '
                    f'{label_part:<20}'
                    f'name="{torrent_dict['name']}")'
                )
                if indx < 5:
                    if dumps_dir.is_dir():
                        dump_file = dumps_dir / f'torrents_dump_{indx}.json'
                        dump_json = json.dumps(torrent_dict, indent=4)
                        dump_file.write_text(dump_json, encoding='utf-8')
        return response
