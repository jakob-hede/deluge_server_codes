from typing import Generator, Any

from twisted.internet import reactor, defer, task
from executin.logge import Loggor


class Twistor:
    def __init__(self):
        super().__init__()
        self.loggor = Loggor(klass=self.__class__)

    def executize(self):
        self.loggor.exclaim('executize')
        reactor.callWhenRunning(self.main_react_func)
        reactor.run()
        self.loggor.debug('executize DONE')


class Twistor1(Twistor):
    def main_react_func(self):
        self.loggor.exclaim('Inside main_react_func')

        @defer.inlineCallbacks
        def reactize() -> Generator[Any, Any, dict]:
            print('reactize')

            # Simulate an async operation that takes 2 seconds
            self.loggor.debug('Starting async dummy process...')
            yield task.deferLater(reactor, 1, lambda: None)
            self.loggor.debug('Async dummy process completed')
            reply: dict = {'status': 'success', 'duration': 1}

            # yield defer.succeed(None)  # Add a yield to make it a generator
            # reply: dict = {'status': 'success'}
            defer.returnValue(reply)
            # return reply

        def on_complete(result):
            self.loggor.info(f'reactize completed with result: {result}')
            # reactor.stop()

        def on_error(failure):
            self.loggor.error(f'reactize failed: {failure}')
            # reactor.stop()

        # start the reactize process in the reactor, and wait for it to complete

        # d = defer.ensureDeferred(reactize())
        d = reactize()
        d.addCallback(on_complete)
        d.addErrback(on_error)
        self.loggor.debug('post reactize called')

        # How to wait for d to complete here before proceeding?

        # d = yield reactize()
        # self.loggor.debug('post yield')

        # reactor.stop()  # noqa
        self.loggor.debug('main_react_func DONE')
        # reactor.stop()

        # d = reactize()
        #
        # def on_success(result):
        #     self.loggor.debug(f'reactize succeeded with result: {result}')
        #
        # def on_failure(failure):
        #     self.loggor.error(f'reactize failed with error: {failure}')
        #
        # d.addCallbacks(on_success, on_failure)

        # from twisted.internet import reactor
        #
        # def stop_reactor():
        #     self.loggor.exclaim('Stopping reactor...')
        #     reactor.stop()
        #     self.loggor.exclaim('Reactor stopped')
        #
        # self.loggor.exclaim('Starting reactor...')
        # reactor.callWhenRunning(stop_reactor)
        # reactor.run()
        # self.loggor.exclaim('Reactor finished')


class Twistor2(Twistor):
    @defer.inlineCallbacks
    def main_react_func(self):
        self.loggor.exclaim('Inside main_react_func')

        @defer.inlineCallbacks
        def reactize() -> Generator[Any, Any, dict]:
            self.loggor.exclaim('reactize')
            # print('reactize')
            self.loggor.debug('Starting async dummy process...')
            yield task.deferLater(reactor, 1, lambda: None)
            self.loggor.debug('Async dummy process completed')
            reply: dict = {'status': 'success', 'duration': 1}
            defer.returnValue(reply)

        try:
            result = yield reactize()
            self.loggor.info(f'reactize completed with result: {result}')
        except Exception as e:
            self.loggor.error(f'reactize failed: {e}')
        finally:
            self.loggor.debug('finally block reached')
            reactor.stop()  # noqa
            self.loggor.debug('main_react_func DONE')

# @classmethod
# def twist_wrap(cls, function):
#     print(f'wrap {function}')
#     a = reactor.callWhenRunning(function)  # noqa
#     b = reactor.run()  # noqa
#     print('Reactor finished')
#
# @classmethod
# def twist_stop(cls):
#     print('Stopping reactor...')
#     reactor.stop()  # noqa
#     print('Reactor stopped')
