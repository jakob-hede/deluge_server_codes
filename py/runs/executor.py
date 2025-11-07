#!/usr/bin/env python3

import sys
import import_helpor  # noqa NEEDED!!!

from executin.commons import ExecutorException
from executin.logge import ExecutorLoggor
from executin.torrentor import Torrentor

from delugapi.delugapi import DelugApi


class Executor:
    def __init__(self):
        super().__init__()
        self.loggor = ExecutorLoggor()

    def tryxetize(self):
        try:
            self.executize()
        except Exception as e:
            # enfo = f'{e.__class__.__name__}: {e.args}'
            # self.loggor.error(f'Executor.tryxetize Exception: {enfo}')
            # from .commons import ExecutorException
            enew = ExecutorException.factory_from_exception(e, 'in Executor.tryxetize')
            self.loggor.error(f'{enew}')
            raise enew
            # raise ExecutorException(f'Executor.tryxetize Exception: {enfo}')
            # import traceback
            # traceback.print_exc()
            # reactor.stop()  # noqa

    def executize(self):
        self.loggor.exclaim("Executor.executize...")
        # self.loggor.info("Executor.executize")
        pop_args = sys.argv.copy()
        pop_args.pop(0)  # Remove script name
        event_name = ''
        if len(pop_args) > 0:
            event_name = pop_args.pop(0)
        else:
            self.loggor.error(f'Executor.executize NO arguments provided. {len(pop_args)}')
            DelugApi.delugapi_stop()
            return None
        if 'status' in event_name:
            self.statusize(event_name)
            # self.loggor.warning(f'Executor.executize Faking status')

            # from delugapi.transaction import DelugApiStatusTransaction
            # x = DelugApiStatusTransaction

            # DelugApi.delugapi_stop()
            return None
        if len(pop_args) < 3:
            # print('Too few arguments provided.')
            self.loggor.error(f'Executor.executize Too few arguments provided. {len(pop_args)}')
            # from twisted.internet import defer, reactor  # noqa
            # reactor.stop()  # noqa
            DelugApi.delugapi_stop()
            return None
            # sys.exit(1)
        # for indx, arg in enumerate(pop_args):
        #     print(f" - {indx}: '{arg}'")

        # self.loggor.info(f"Executor.executize: {', '.join(pop_args)}")

        torrent_id = pop_args.pop(0)
        torrent_name = pop_args.pop(0)
        base_sdir = pop_args.pop(0)

        self.loggor.info(f'Executor.executize: "{event_name}", "{torrent_name}", "{base_sdir}"')

        # print(f"Event: '{event_name}'")
        # print(f"Torrent ID: '{torrent_id}'")
        # print(f"Torrent Name: '{torrent_name}'")
        # print(f"Base Save Dir: '{base_sdir}'")

        torrentor = Torrentor(torrent_id, torrent_name, base_sdir)
        torrentor.process_event(event_name)
        self.loggor.info(f'DONE Executor.executize: "{event_name}", "{torrent_name}", "{base_sdir}"')
        return None

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


# def main_function():
#     executor = Executor()
#     executor.executize()
#     # DelugApi.delugapi_unwrap()

def main_function():
    executor = Executor()
    try:
        executor.tryxetize()
    except Exception as e:
        e_str = str(e)
        executor.loggor.error(f"Error in main_function: {e_str}")
        # from twisted.internet import reactor  # noqa
        # reactor.stop()  # Stop reactor after execution completes or fails
    finally:
        executor.loggor.info("Executor main_function DONE")


def main():
    # loggor = ExecutorLoggor()
    # loggor.info("Executor main called")
    DelugApi.delugapi_wrap(main_function)


# def main():
#     from twisted.internet import reactor
#
#     def main_function():
#         try:
#             print("main_function")
#             executor = Executor()
#             executor.executize()
#         except Exception as e:
#             print(f"Error in main_function: {e}")
#             import traceback
#             traceback.print_exc()
#         finally:
#             reactor.stop()  # Stop reactor after execution completes or fails
#
#     print(f'wrap {main_function}')
#     DelugApi.delugapi_wrap(main_function)


if __name__ == '__main__':
    main()
