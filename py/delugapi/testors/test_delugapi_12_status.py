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
        response: DelugApiResponse = client.test6_id_status()

        # print(f"FINAL response: {response}")
        def elaborate():
            self.loggor.remark('Torrents Status:')
            for key, value in response.result.items():
                # self.loggor.info(f'  - {key}: {value}')
                name = value.get('name', 'N/A')
                txt = (
                    f'  - {name}: '
                    # f'  - {key}: '
                    # f'{value}'
                )
                self.loggor.info(txt)

        self.loggor.debug(f'Final Response: {response}')
        if response.is_valid:
            self.loggor.info('TwistinTestor.executize SUCCESS')
            # elaborate()
            # sample_key = list(response.result.keys())[0]
            # response: DelugApiResponse = client.test6_id_status(torrent_id=sample_key)
            # self.loggor.debug(f'Final Response (test6_id_status): {response}')
        else:
            self.loggor.error('TwistinTestor.executize FAILURE')
            self.loggor.error(f'Response: {response}')


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
