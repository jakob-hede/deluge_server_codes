from abc import ABC, abstractmethod
from typing import Generator, Any, TYPE_CHECKING

from twisted.internet import defer
from twisted.internet.interfaces import IReactorTime

from delugapi.transaction import DelugApiTransaction, DelugApiStatusTransaction
from deluge.ui.client import client as ui_client
from delugapi.response import DelugApiResponse
from twistin import Twistee, TwistResponse

if TYPE_CHECKING:
    from delugapi import DelugApi as DelugApiType
else:
    DelugApiType = 'DelugApi'


class DelugApiTransactionTwistee(Twistee):
    def __init__(self, api: DelugApiType, transaction: DelugApiTransaction) -> None:
        super().__init__()
        self.api: DelugApiType = api
        self.transaction: DelugApiTransaction = transaction

    @abstractmethod
    @defer.inlineCallbacks
    def main_twistee_func(self, reactor_clock: IReactorTime) -> Generator[Any, Any, TwistResponse]:
        ...

    # def main_twistee_func(self, reactor_clock: IReactorTime) -> Generator[Any, Any, TwistResponse]:
    #     pass

    #     print(f"{self.__class__.__name__} initialized")
    #     self.response: DelugApiResponse = DelugApiResponse()
    #
    # def __str__(self) -> str:
    #     txt = f"<{self.__class__.__name__}>"
    #     return txt
    #
    # @abstractmethod
    # def executize(self) -> Generator[Any, Any, dict]:
    #     raise NotImplementedError  # pragma: no cover


class DelugApiStatusTransactionTwistee(DelugApiTransactionTwistee):
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

    def __init__(self, api: DelugApiType, torrent_id: str = '') -> None:
        transaction: DelugApiTransaction = DelugApiStatusTransaction(torrent_id=torrent_id)
        super().__init__(api, transaction)
        self.torrent_id: str = torrent_id

    @defer.inlineCallbacks
    def main_twistee_func(self, reactor_clock: IReactorTime) -> Generator[Any, Any, TwistResponse]:
        self.loggor.exclaim('main_twistee_func')

        status_dict = yield self.api.transactize(self.transaction)
        response = TwistResponse(result=status_dict)
        pass

        # self.loggor.debug('Starting async MAIN STATUS process...')
        # results_dict: dict = {}
        # response = TwistResponse(result=results_dict)
        # for test_name in 'A B C'.split():
        #     self.loggor.debug(f'Processing test: {test_name}')
        #     sub_response = yield self.test_subfunc(reactor_clock, test_name)
        #     results_dict[test_name] = sub_response.result
        defer.returnValue(response)

    @defer.inlineCallbacks
    def executize(self) -> Generator[Any, Any, dict]:  # noqa
        print(f"executize {self.__class__.__name__}...")
        reply: dict = yield self.fetch_torrents_status()
        defer.returnValue(reply)

    @defer.inlineCallbacks
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

# class DelugApiMoveTransaction(DelugApiTransactionTwistee):
#     def __init__(self, torrent_id: str, destination: str) -> None:
#         super().__init__()
#         self.torrent_id: str = torrent_id
#         self.destination: str = destination
#
#     @defer.inlineCallbacks
#     def executize(self) -> Generator[Any, Any, dict]:  # noqa
#         print(f"executize {self.__class__.__name__}...")
#         reply: dict = yield self.fetch_move()
#         defer.returnValue(reply)
#
#     @defer.inlineCallbacks
#     def fetch_move(self) -> Generator[Any, Any, dict]:
#         print("coring...")
#         torrent_ids: list[str] = [self.torrent_id]
#         reply_dict: dict = yield ui_client.core.move_storage(torrent_ids, self.destination)
#         defer.returnValue(reply_dict)
