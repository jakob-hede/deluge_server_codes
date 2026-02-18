from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generator, Any

from delugapi.twistin_adaptors import defer_inline_callbacks, adapted_task
# from twisted.internet import defer

from deluge.ui.client import client as ui_client
from delugapi.response import DelugApiResponse
from delugapi.torrent import DelugapiTorrent


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
    essence_keys: list[str] = '''
    name
    download_location
    save_path
    move_completed_path
    label
    '''.strip().split()

    interesting_keys: list[str] = essence_keys + '''
    hash
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

    @property
    def essence(self) -> dict | None:
        _essence = {}
        data = self.response.result
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
                    _essence[key] = _dict.get(key, 'unfound')
        return _essence

    @property
    def pressence(self) -> str:
        _essence = self.essence
        if not _essence:
            return 'unpopulated'
        txt = (
            f'\npressence:\n'
            f' - name: {_essence["name"]}\n'
            f' - download_location:   {_essence["download_location"]}\n'
            f' - save_path:           {_essence["save_path"]}\n'
            f' - move_completed_path: {_essence["move_completed_path"]}\n'
            f' - label: {_essence["label"]}\n'
        )
        return txt

    def delugapi_torrent_from_status(self) -> DelugapiTorrent | None:
        from delugapi.torrent import DelugapiTorrent
        data = self.response.result
        if isinstance(data, dict) and data:
            torrent = DelugapiTorrent.from_dict(data)
            return torrent
        return None


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
        print("fetch_move coring move_storage...")
        torrent_ids: list[str] = [self.torrent_id]
        reply_dict: dict = yield ui_client.core.move_storage(torrent_ids, self.destination)
        # reply_dict = {'status': 'move_dispatched', 'torrent_id': self.torrent_id, 'destination': self.destination}
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
