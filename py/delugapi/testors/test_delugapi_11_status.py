#!/usr/bin/env python3
from pathlib import Path
import import_helpor  # noqa NEEDED!!!
from delugapi.response import DelugApiResponse
from executin.logge import Loggor


class Testor:
    def __init__(self):
        super().__init__()
        self.loggor = Loggor(klass=self.__class__)

    def executize(self):
        self.loggor.exclaim("Testor.executize...")
        self.commonize()
        self.statusize()

    def commonize(self):
        from executin.commons import Commons
        deluge_root_dir: Path = Commons.singleton.deluge_root_dir
        self.loggor.debug(f"Deluge Root Dir: '{deluge_root_dir}'")

    def statusize(self):
        self.loggor.exclaim("Testor.statusize...")
        from delugapi import DelugapiClient
        client = DelugapiClient()
        response: DelugApiResponse = client.test5_status()
        # print(f"FINAL response: {response}")

        # def _x_statusize(self):
        #     self.loggor.exclaim('statusize')
        #     from delugapi.transaction_twistee import DelugApiTransactionTwistee
        #     from delugapi.transaction_twistee import DelugApiStatusTransactionTwistee
        #     from twistin import Twistor
        #     from twistin import TwistResponse
        #
        #     twistee: DelugApiTransactionTwistee = DelugApiStatusTransactionTwistee()
        #     twistor = Twistor(twistee)
        #     response: TwistResponse = twistor.executize()
        #     print(f'Final Response.result: {response.result}')
        self.loggor.debug(f'Final Response: {response}')
        if response.is_valid:
            self.loggor.info('TwistinTestor.executize SUCCESS')
            # self.loggor.remark('Torrents Status:')
            # for key, value in response.result.items():
            #     # self.loggor.info(f'  - {key}: {value}')
            #     name = value.get('name', 'N/A')
            #     txt = (
            #         f'  - {name}: '
            #         # f'  - {key}: '
            #         # f'{value}'
            #     )
            #     self.loggor.info(txt)
        else:
            self.loggor.error('TwistinTestor.executize FAILURE')
            self.loggor.error(f'Response: {response}')

    # def x_torrentor_process_event(self):
    #     print("Testor.executize...")
    #     # event_name = 'exe_completed'
    #     event_name = 'exe_added'
    #     torrent_id = '94941321a2d383ddf0b276f94c889b980715c072'
    #     torrent_name = 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]'
    #     # base_sdir = '/ocean/video/movies/movin'
    #     base_sdir = '/ocean/test/area51'
    #
    #     # print(f"Event: '{event_name}'")
    #     # print(f"Torrent ID: '{torrent_id}'")
    #     # print(f"Torrent Name: '{torrent_name}'")
    #     # print(f"Base Save Dir: '{base_sdir}'")
    #
    #     from executin.torrentor import Torrentor
    #     torrentor = Torrentor(torrent_id, torrent_name, base_sdir)
    #     torrentor.process_event(event_name)


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
