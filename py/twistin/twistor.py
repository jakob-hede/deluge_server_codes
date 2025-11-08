from __future__ import annotations
from typing import Generator, Any, Callable, cast

from twisted.internet import defer  # , task, reactor
from twisted.internet import reactor as real_reactor
from twisted.internet.interfaces import IReactorTime

from executin.logge import Loggor
from twistin.response import TwistResponse
from twistin.twistee import TwisteeProtocol, DummyTwistee
from twistin.exceptions import TwistinException, TwistinTestException

_DEFAULT_REACTOR: IReactorTime = cast(IReactorTime, cast(object, real_reactor))


class Twistor:
    def __init__(self, twistee: TwisteeProtocol):
        super().__init__()
        self.loggor = Loggor(klass=self.__class__)
        # self.reactor_clock: IReactorTime = cast(IReactorTime, reactor)  # ty pe: ignore
        # Preferred: intermediate cast to object to satisfy strict checkers
        # self.reactor_clock: IReactorTime = cast(IReactorTime, cast(object, reactor))
        self.reactor_clock: IReactorTime = _DEFAULT_REACTOR

        self.main_twistee_func: Callable = DummyTwistee().main_twistee_func  # To be set by subclass

        # Runtime check if using @runtime_checkable
        if not isinstance(twistee, TwisteeProtocol):
            raise TypeError(f"twistee must conform to TwisteeProtocol, got {type(twistee)}")

        twist_callable = twistee.main_twistee_func
        # self.main_twistee_func = twistee.main_twistee_func  # Bind method for reactor call
        # x = self.main_twistee_func

        if not callable(twist_callable):
            raise TypeError(f"main_twistee_func must be callable, got {type(twist_callable)}")

        # Check if it's an inlineCallbacks generator function
        import inspect
        func = twist_callable
        # For methods, get the underlying function
        if hasattr(func, '__func__'):
            func = func.__func__

        # Check if it's a generator function OR if it's wrapped by inlineCallbacks
        is_generator = inspect.isgeneratorfunction(func)
        is_inline_callbacks = hasattr(func, '_generator') or (
                hasattr(func, '__wrapped__') and inspect.isgeneratorfunction(func.__wrapped__)
        )

        if not (is_generator or is_inline_callbacks):
            raise TypeError("main_twistee_func must be decorated with @defer.inlineCallbacks (generator function)")

        self.main_twistee_func = twist_callable

        pass

    def executize(self):
        self.loggor.exclaim('executize')
        # reactor.callWhenRunning(self.main_twistee_func, self.reactor_clock)
        startup_tuple = self.reactor_clock.callWhenRunning(self.execute_reactize)
        self.reactor_clock.run()
        self.loggor.debug(f'executize completed with startup_tuple: {startup_tuple}')
        self.loggor.info('executize DONE')

    @defer.inlineCallbacks
    def execute_reactize(self) -> Generator[Any, Any, TwistResponse]:
        self.loggor.exclaim('Inside main_react_func')

        response = TwistResponse()
        try:
            response = yield self.main_twistee_func(self.reactor_clock)
            self.loggor.info(f'reactize completed with result: {response}')
        except TwistinException as e:
            self.loggor.error(f'reactize failed: {e}')
        except Exception as e:
            self.loggor.error(f'UNKNOWN reactize failed: {e}')
        finally:
            self.loggor.debug('finally block reached')
            self.reactor_clock.stop()
            self.loggor.debug('main_react_func DONE')
            defer.returnValue(response)

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


# class Twistor1(Twistor):
#     def main_react_func(self):
#         self.loggor.exclaim('Inside main_react_func')
#
#         @defer.inlineCallbacks
#         def reactize() -> Generator[Any, Any, TwistResponse]:
#             print('reactize')
#
#             # Simulate an async operation that takes 2 seconds
#             self.loggor.debug('Starting async dummy process...')
#             yield task.deferLater(reactor, 1, lambda: None)
#             self.loggor.debug('Async dummy process completed')
#             reply: dict = {'status': 'success', 'duration': 1}
#
#             # yield defer.succeed(None)  # Add a yield to make it a generator
#             # reply: dict = {'status': 'success'}
#             defer.returnValue(reply)
#             # return reply
#
#         def on_complete(result):
#             self.loggor.info(f'reactize completed with result: {result}')
#             # reactor.stop()
#
#         def on_error(failure):
#             self.loggor.error(f'reactize failed: {failure}')
#             # reactor.stop()
#
#         # start the reactize process in the reactor, and wait for it to complete
#
#         # d = defer.ensureDeferred(reactize())
#         d = reactize()
#         d.addCallback(on_complete)
#         d.addErrback(on_error)
#         self.loggor.debug('post reactize called')
#
#         # How to wait for d to complete here before proceeding?
#
#         # d = yield reactize()
#         # self.loggor.debug('post yield')
#
#         # reactor.stop()  # noqa
#         self.loggor.debug('main_react_func DONE')
#         # reactor.stop()
#
#         # d = reactize()
#         #
#         # def on_success(result):
#         #     self.loggor.debug(f'reactize succeeded with result: {result}')
#         #
#         # def on_failure(failure):
#         #     self.loggor.error(f'reactize failed with error: {failure}')
#         #
#         # d.addCallbacks(on_success, on_failure)
#
#         # from twisted.internet import reactor
#         #
#         # def stop_reactor():
#         #     self.loggor.exclaim('Stopping reactor...')
#         #     reactor.stop()
#         #     self.loggor.exclaim('Reactor stopped')
#         #
#         # self.loggor.exclaim('Starting reactor...')
#         # reactor.callWhenRunning(stop_reactor)
#         # reactor.run()
#         # self.loggor.exclaim('Reactor finished')
#
#
# class Twistor2(Twistor):
#     @defer.inlineCallbacks
#     def main_react_func(self):
#         self.loggor.exclaim('Inside main_react_func')
#
#         @defer.inlineCallbacks
#         def reactize() -> Generator[Any, Any, TwistResponse]:
#             self.loggor.exclaim('reactize')
#             # print('reactize')
#             self.loggor.debug('Starting async dummy process...')
#             yield task.deferLater(reactor, 1, lambda: None)
#             self.loggor.debug('Async dummy process completed')
#             reply: dict = {'status': 'success', 'duration': 1}
#
#             exc = TwistinTestException('Simulated exception in reactize')
#             # exc = Exception('Simulated exception in reactize')
#             raise exc
#
#             defer.returnValue(reply)
#
#         try:
#             result = yield reactize()
#             self.loggor.info(f'reactize completed with result: {result}')
#         except TwistinException as e:
#             self.loggor.error(f'reactize failed: {e}')
#         except Exception as e:
#             self.loggor.error(f'UNKNOWN reactize failed: {e}')
#         finally:
#             self.loggor.debug('finally block reached')
#             reactor.stop()  # noqa
#             self.loggor.debug('main_react_func DONE')
