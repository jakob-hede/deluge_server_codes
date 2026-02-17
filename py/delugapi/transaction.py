from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generator, Any

from delugapi.twistin_adaptors import defer_inline_callbacks, adapted_task
# from twisted.internet import defer

from deluge.ui.client import client as ui_client
from delugapi.response import DelugApiResponse


class DelugApiTransactionReplyWrapper:
    @classmethod
    def from_dict(cls, data: dict) -> DelugApiTransactionReplyWrapper:
        reply = cls(data)
        return reply

    def __init__(self, data: dict | None) -> None:
        super().__init__()
        self._data = data
        self._essence = {}
        if data:
            _hash, _dict = next(iter(data.items()), None)
            if _dict:
                essence_keys: list[str] = '''
                name
                download_location
                save_path
                move_completed_path
                label
                '''.strip().split()
                # hash
                # files
                # orig_files
                for key in essence_keys:
                    self._essence[key] = _dict.get(key, 'unfound')

    @property
    def pressence(self) -> str:
        if not self._essence:
            return 'unpopulated'
        txt = (
            f'\npressence:\n'
            f' - name: {self._essence["name"]}\n'
            f' - download_location:   {self._essence["download_location"]}\n'
            f' - save_path:           {self._essence["save_path"]}\n'
            f' - move_completed_path: {self._essence["move_completed_path"]}\n'
            f' - label: {self._essence["label"]}\n'
        )
        return txt

    @property
    def data(self) -> dict:
        return self._data


class DelugApiTransaction(ABC):
    def __init__(self) -> None:
        super().__init__()
        print(f"{self.__class__.__name__} initialized")
        self.response: DelugApiResponse = DelugApiResponse()

    def __str__(self) -> str:
        txt = f"<{self.__class__.__name__}>"
        return txt

    @abstractmethod
    def executize(self) -> Generator[Any, Any, dict]:
        raise NotImplementedError  # pragma: no cover


class DelugApiStatusTransaction(DelugApiTransaction):
    interesting_keys: list[str] = '''
    name
    label
    hash
    move_completed_path
    save_path
    download_location
    files
    orig_files
    '''.strip().split()

    def __init__(self, torrent_id: str = '') -> None:
        super().__init__()
        self.torrent_id: str = torrent_id

    @defer_inline_callbacks
    def executize(self) -> Generator[Any, Any, dict]:  # noqa
        print(f"executize {self.__class__.__name__}...")
        reply: dict = yield self.fetch_torrents_status()
        return reply

    @defer_inline_callbacks
    def fetch_torrents_status(self,
                              filter_dict: dict = None,
                              keys: list = None) -> Generator[Any, Any, dict]:
        if filter_dict is None:
            filter_dict = {}
            if self.torrent_id:
                filter_dict = {'id': [self.torrent_id]}
        if keys is None:
            keys: list[str] = self.interesting_keys
        print("coring...")
        reply_dict: dict = yield ui_client.core.get_torrents_status(filter_dict, keys)
        print(f'return reply_dict: {str(reply_dict)[:100]}...')
        return reply_dict


class DelugApiMoveTransaction(DelugApiTransaction):
    def __init__(self, torrent_id: str, destination: str) -> None:
        super().__init__()
        self.torrent_id: str = torrent_id
        self.destination: str = destination

    @defer_inline_callbacks
    def executize(self) -> Generator[Any, Any, dict]:  # noqa
        print(f"executize {self.__class__.__name__}...")
        reply: dict = yield self.fetch_move()
        return reply

    @defer_inline_callbacks
    def fetch_move(self) -> Generator[Any, Any, dict]:
        print("coring...")
        torrent_ids: list[str] = [self.torrent_id]
        reply_dict: dict = yield ui_client.core.move_storage(torrent_ids, self.destination)
        return reply_dict

    @defer_inline_callbacks
    def fetch_dummy(self) -> Generator[Any, Any, dict]:
        from twisted.internet import reactor
        print("fetch_dummy...")
        delay: float = 1
        callee = lambda: None
        yield adapted_task.deferLater(reactor, delay, callable=callee)
        reply_dict: dict = {'status': 'dummy_completed', 'duration': delay}
        return reply_dict

    @defer_inline_callbacks
    def coring_force_recheck(self) -> Generator[Any, Any, dict]:
        from twisted.internet import reactor
        print("force_recheck...")
        torrent_ids: list[str] = [self.torrent_id]
        reply_dict: dict = yield ui_client.core.force_recheck(torrent_ids)
        return reply_dict
