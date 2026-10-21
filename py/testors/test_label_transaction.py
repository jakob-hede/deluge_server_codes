#!/usr/bin/env python3
from unittest import mock

import import_helpor  # noqa NEEDED!!!
from twisted.internet import defer

from delugapi import transaction as transaction_module
from delugapi.delugapi import DelugApi
from delugapi.transaction import DelugApiLabelTransaction


class FakeLabelPlugin:
    def __init__(self):
        super().__init__()
        self.received: list[tuple[str, str]] = []

    def set_torrent(self, torrent_id, label_id):
        self.received.append((torrent_id, label_id))
        return defer.succeed(None)


class FakeUiClient:
    def __init__(self):
        super().__init__()
        self.label = FakeLabelPlugin()


class Testor:
    def __init__(self):
        super().__init__()

    def executize(self):
        print("Testor.executize...")
        torrent_id = '0123456789abcdef0123456789abcdef01234567'
        label = 'tv-in'
        fake_ui_client = FakeUiClient()
        transaction = DelugApiLabelTransaction(torrent_id, label)
        with mock.patch.object(transaction_module, 'ui_client', fake_ui_client):
            DelugApi.delugapi_wrap(transaction.executize)
        print(f"fake label.set_torrent received: {fake_ui_client.label.received}")
        print(f"as given: {fake_ui_client.label.received == [(torrent_id, label)]}")


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
