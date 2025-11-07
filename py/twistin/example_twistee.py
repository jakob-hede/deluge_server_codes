from __future__ import annotations
from typing import Generator, Any

from twisted.internet import reactor, defer, task
from executin.logge import Loggor


class Twistee:
    def __init__(self):
        super().__init__()
        self.loggor = Loggor(klass=self.__class__)

    @defer.inlineCallbacks
    def main_reactize_func(self) -> Generator[Any, Any, dict]:
        self.loggor.exclaim('reactize')
        raise NotImplementedError('main_reactize_func must be implemented by subclass')

    # def executize(self):
    #     self.loggor.exclaim('executize')
    #     reactor.callWhenRunning(self.main_react_func)
    #     reactor.run()
    #     self.loggor.debug('executize DONE')


class TwisteeExample1(Twistee):
    def __init__(self):
        super().__init__()

    @defer.inlineCallbacks
    def main_reactize_func(self) -> Generator[Any, Any, dict]:
        self.loggor.exclaim('main_reactize_func')
        # print('reactize')
        self.loggor.debug('Starting async dummy process...')
        yield task.deferLater(reactor, 1, lambda: None)
        self.loggor.debug('Async dummy process completed')
        reply: dict = {'status': 'success', 'duration': 1}

        # exc = TwistinTestException('Simulated exception in reactize')
        # # exc = Exception('Simulated exception in reactize')
        # raise exc

        defer.returnValue(reply)
