#!/usr/bin/env python3

import sys
from typing import Generator, Any, Protocol
import import_helpor  # noqa NEEDED!!!
from delugapi import DelugapiClient
from delugapi.transaction import DelugApiTransaction, DelugApiMoveTransaction
from delugapi.transaction_twistee import DelugApiStatusTransactionTwistee, DelugApiTransactionTwistee
from delugapi.twistin_adaptors import DelugApiTwistee, defer_inline_callbacks, ReactorInterface, \
    adapted_task
from delugapi.response import DelugApiResponse, IncompleteDelugApiResponse

from executin.commons import ExecutorException
from executin.logge import ExecutorLoggor
from executin.torrentor import Torrentor

from delugapi.delugapi import DelugApi


# @runtime_checkable
class ExecutwisteeProtocol(Protocol):
    def main_twistee_func(self, reactor_clock: ReactorInterface) -> Generator[Any, Any, DelugApiResponse]:
        # def main_twistee_func(self) -> Generator[Any, Any, TwistResponse]:
        ...

    def post_process_response(self, response: DelugApiResponse | None = None) -> None:
        ...


class StatusExecutwistee(DelugApiStatusTransactionTwistee):
    def __init__(self, api: DelugApi):
        super().__init__(api)
        self.api: DelugApi = api

    def post_process_response(self, response: DelugApiResponse | None = None) -> None:
        response = response or self.transaction.response

        first_item = next(iter(response.result.items()), None)
        if first_item:
            # first_item_dict = first_item[1]
            first_item_dict = response.result
            # pass
            from delugapi.torrent import DelugapiTorrent
            torrent = DelugapiTorrent.from_dict(first_item_dict)
            self.loggor.remark('First Torrent from_dict:')
            self.loggor.info(f'\n{torrent.tid}'
                             f'\n{torrent.name}'
                             f'\n{torrent.label}'
                             f'\n{torrent.save_path}'
                             )

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

        # self.loggor.debug(f'Final Response: {response}')
        if response.is_valid:
            # self.loggor.info('TwistinTestor.executize SUCCESS')
            elaborate()


class EventExecutwistee(DelugApiTransactionTwistee):
    def __init__(self, api: DelugApi, event_name: str, torrent_id: str, torrent_name: str, base_sdir: str):
        destination = 'dummy-destination'
        # transaction: DelugApiTransaction = DelugApiMoveTransaction(torrent_id, destination)
        transaction = None
        super().__init__(api, transaction=transaction)
        self.api: DelugApi = api
        self.event_name: str = event_name
        self.torrent_id: str = torrent_id
        self.torrent_name: str = torrent_name
        self.base_sdir: str = base_sdir

    @defer_inline_callbacks
    def main_twistee_func(self, reactor_clock: ReactorInterface) -> Generator[Any, Any, DelugApiResponse]:
        self.loggor.exclaim('main_twistee_func')
        # status_dict = yield self.api.transactize(self.transaction)
        delay: float = 1
        callee = lambda: None
        yield adapted_task.deferLater(reactor_clock, delay, callable=callee)
        self.loggor.debug('Async dummy process completed')
        reply_dict: dict = {'status': 'success', 'duration': 1}

        torrentor = Torrentor(self.torrent_id, self.torrent_name, self.base_sdir)
        d = torrentor.process_event(self.event_name)
        if d is not None:
            yield d
        self.loggor.info(f'DONE Executor.executize: "{self.event_name}", "{self.torrent_name}", "{self.base_sdir}"')

        response = DelugApiResponse(result=reply_dict)
        return response

    def post_process_response(self, response: DelugApiResponse | None = None) -> None:
        # response = response or self.transaction.response
        self.loggor.debug(f'EventExecutwistee.post_process_response: {response}')


class ExecutorDelugapiClient(DelugapiClient):
    def executwist(self, executwistee: ExecutwisteeProtocol) -> DelugApiResponse:
        response = self.twistorize(executwistee)  # noqa
        # executwistee.post_process_response(response)
        return response

    # def executwist(self, twistee: DelugApiTwistee) -> DelugApiResponse:
    #     response = self.twistorize(twistee)
    #     return response

    def test5_status(self) -> DelugApiResponse:
        self.loggor.exclaim('DelugapiClient test5_status method called')
        self.reaction_response = DelugApiResponse()
        twistee: DelugApiTwistee = DelugApiStatusTransactionTwistee(self.api)
        response = self.twistorize(twistee)
        self.reaction_response = response
        self.handle_status_reaction_response()
        return response


class Executor:
    def __init__(self):
        super().__init__()
        self.loggor = ExecutorLoggor()

    def tryxetize(self):
        try:
            self.executize()
        except Exception as e:
            enew = ExecutorException.factory_from_exception(e, 'in Executor.tryxetize')
            self.loggor.error(f'{enew}')
            raise enew

    def executize(self):
        self.loggor.exclaim("Executor.executize...")

        pop_args = sys.argv.copy()
        pop_args.pop(0)  # Remove script name
        event_name = ''
        if len(pop_args) > 0:
            event_name = pop_args.pop(0)
        else:
            self.loggor.error(f'Executor.executize NO arguments provided. {len(pop_args)}')
            # DelugApi.delugapi_stop()
            return None

        client = ExecutorDelugapiClient()
        executwistee: ExecutwisteeProtocol | None = None
        if 'status' in event_name:
            executwistee = StatusExecutwistee(client.api)
            # return None
        elif len(pop_args) < 3:
            # print('Too few arguments provided.')
            self.loggor.error(f'Executor.executize Too few arguments provided. {len(pop_args)}')
            return None

        if len(pop_args) >= 3:
            torrent_id = pop_args.pop(0)
            torrent_name = pop_args.pop(0)
            base_sdir = pop_args.pop(0)
            self.loggor.debug(f'Executor.executize: "{event_name}", "{torrent_name}", "{base_sdir}"')
            executwistee = EventExecutwistee(client.api, event_name, torrent_id, torrent_name, base_sdir)

        if executwistee is None:
            self.loggor.error('Executor.executize No valid twistee created')
            return None

        response = client.executwist(executwistee)
        self.loggor.debug(f'Final Response: {response}')
        if response.is_valid:
            self.loggor.info('Executor.executize SUCCESS')
        else:
            self.loggor.error('Executor.executize FAILURE')
            self.loggor.error(f'Response: {response}')
            return None

        executwistee.post_process_response()
        return None

    # def _x_executize(self):
    #     self.loggor.exclaim("Executor.executize...")
    #     # self.loggor.info("Executor.executize")
    #     pop_args = sys.argv.copy()
    #     pop_args.pop(0)  # Remove script name
    #     event_name = ''
    #     if len(pop_args) > 0:
    #         event_name = pop_args.pop(0)
    #     else:
    #         self.loggor.error(f'Executor.executize NO arguments provided. {len(pop_args)}')
    #         DelugApi.delugapi_stop()
    #         return None
    #     if 'status' in event_name:
    #         self.statusize(event_name)
    #         # self.loggor.warning(f'Executor.executize Faking status')
    #
    #         # from delugapi.transaction import DelugApiStatusTransaction
    #         # x = DelugApiStatusTransaction
    #
    #         # DelugApi.delugapi_stop()
    #         return None
    #     if len(pop_args) < 3:
    #         # print('Too few arguments provided.')
    #         self.loggor.error(f'Executor.executize Too few arguments provided. {len(pop_args)}')
    #         # from twisted.internet import defer, reactor  # noqa
    #         # reactor.stop()  # noqa
    #         DelugApi.delugapi_stop()
    #         return None
    #         # sys.exit(1)
    #     # for indx, arg in enumerate(pop_args):
    #     #     print(f" - {indx}: '{arg}'")
    #
    #     # self.loggor.info(f"Executor.executize: {', '.join(pop_args)}")
    #
    #     torrent_id = pop_args.pop(0)
    #     torrent_name = pop_args.pop(0)
    #     base_sdir = pop_args.pop(0)
    #
    #     self.loggor.info(f'Executor.executize: "{event_name}", "{torrent_name}", "{base_sdir}"')
    #
    #     # print(f"Event: '{event_name}'")
    #     # print(f"Torrent ID: '{torrent_id}'")
    #     # print(f"Torrent Name: '{torrent_name}'")
    #     # print(f"Base Save Dir: '{base_sdir}'")
    #
    #     torrentor = Torrentor(torrent_id, torrent_name, base_sdir)
    #     torrentor.process_event(event_name)
    #     self.loggor.info(f'DONE Executor.executize: "{event_name}", "{torrent_name}", "{base_sdir}"')
    #     return None

    def test_basic(self):
        self.loggor.info("Executor.test_basic called")

    def statusize(self, event_name):
        self.loggor.info(f'Executor.executize Getting status')
        from executin.statusor import Statusor
        statusor = Statusor()
        statusor.process_event(event_name)
        self.loggor.info(f'DONE Executor.executize Getting status')


'''
 - 0: '/codes/py/executor.py'
 - 1: 'exe_added'
 - 2: '8178b09bde84d46c945b7b601b8bc3c0a959569e'
 - 3: 'Friendship (2025) [1080p] [WEBRip] [5.1] [YTS.MX]'
 - 4: '/deluge/downloads'
'''


def main_function():
    print("main_function")


def main():
    executor = Executor()
    executor.tryxetize()


if __name__ == '__main__':
    main()
