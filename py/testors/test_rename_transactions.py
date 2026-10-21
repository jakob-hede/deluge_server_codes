#!/usr/bin/env python3
from unittest import mock

import import_helpor  # noqa NEEDED!!!
from twisted.internet import defer

from delugapi import transaction as transaction_module
from delugapi.delugapi import DelugApi
from delugapi.transaction import DelugApiRenameFolderTransaction, DelugApiRenameFilesTransaction


class FakeCore:
    def __init__(self):
        super().__init__()
        self.received_rename_folder: list[tuple[str, str, str]] = []
        self.received_rename_files: list[tuple[str, list[tuple[int, str]]]] = []

    def rename_folder(self, torrent_id, folder, new_folder):
        self.received_rename_folder.append((torrent_id, folder, new_folder))
        return defer.succeed(None)

    def rename_files(self, torrent_id, filenames):
        self.received_rename_files.append((torrent_id, filenames))
        return defer.succeed(None)


class SilentCore:
    def rename_folder(self, torrent_id, folder, new_folder):
        return defer.Deferred()


class FakeUiClient:
    def __init__(self):
        super().__init__()
        self.core = FakeCore()


class SilentUiClient:
    def __init__(self):
        super().__init__()
        self.core = SilentCore()


class Testor:
    def __init__(self):
        super().__init__()

    def executize(self):
        print("Testor.executize...")
        torrent_id = '0123456789abcdef0123456789abcdef01234567'
        folder = 'The Florist (2026) [NORDICSUBS] [1080p] [WEBRip] [5.1] [YTS.GG - YTS.BZ]/'
        new_folder = 'the.florist.2026/'
        filenames = [(0, 'the.florist.2026/The Florist 2026 1080p WEB-DL HEVC x265 5.1 BONE.mkv')]
        fake_ui_client = FakeUiClient()
        silent_ui_client = SilentUiClient()
        folder_transaction = DelugApiRenameFolderTransaction(torrent_id, folder, new_folder)
        files_transaction = DelugApiRenameFilesTransaction(torrent_id, filenames)
        silent_transaction = DelugApiRenameFolderTransaction(torrent_id, folder, new_folder)
        print(f"default timeouts: {folder_transaction.timeout} {files_transaction.timeout}")
        silent_transaction.timeout = 0.5
        timed_out: list[str] = []

        # one reactor run for all, a stopped reactor cannot be restarted
        @defer.inlineCallbacks
        def reactize():
            with mock.patch.object(transaction_module, 'ui_client', fake_ui_client):
                yield folder_transaction.executize()
                yield files_transaction.executize()
            with mock.patch.object(transaction_module, 'ui_client', silent_ui_client):
                try:
                    yield silent_transaction.executize()
                except defer.TimeoutError as ex:
                    timed_out.append(f'{type(ex).__name__}: {ex}')

        DelugApi.delugapi_wrap(reactize)
        received_folder = fake_ui_client.core.received_rename_folder
        print(f"fake core.rename_folder received: {received_folder}")
        print(f"as given: {received_folder == [(torrent_id, folder, new_folder)]}")
        received_files = fake_ui_client.core.received_rename_files
        print(f"fake core.rename_files received: {received_files}")
        print(f"as given: {received_files == [(torrent_id, filenames)]}")
        print(f"silent core.rename_folder, timeout {silent_transaction.timeout}: {timed_out}")
        print(f"timed out: {len(timed_out) == 1}")


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
