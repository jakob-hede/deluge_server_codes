from __future__ import annotations
from typing import Generator, Any
from twisted.internet import defer, task
from twisted.internet.interfaces import IReactorTime

from ..response import TwistResponse
from ..twistee import Twistee


class TwisteeExample2(Twistee):
    def __init__(self):
        super().__init__()

    @defer.inlineCallbacks
    def main_twistee_func(self, reactor_clock: IReactorTime) -> Generator[Any, Any, TwistResponse]:
        self.loggor.exclaim('main_twistee_func')
        self.loggor.debug('Starting async MAIN STATUS process...')
        results_dict: dict = {}
        response = TwistResponse(result=results_dict)
        for test_name in 'A B C'.split():
            self.loggor.debug(f'Processing test: {test_name}')
            sub_response = yield self.test_subfunc(reactor_clock, test_name)
            results_dict[test_name] = sub_response.result
        defer.returnValue(response)

    @defer.inlineCallbacks
    def test_subfunc(self, reactor_clock: IReactorTime, test_name: str) -> Generator[Any, Any, TwistResponse]:
        self.loggor.exclaim('test_subfunc')
        self.loggor.debug('Starting async TEST SUB process...')
        delay: float = 1
        callee = lambda: None
        yield task.deferLater(reactor_clock, delay, callable=callee)
        self.loggor.debug('Async TEST SUB process completed')
        reply_dict: dict = {'status': 'success', 'duration': 1}
        response = TwistResponse(result=reply_dict)
        defer.returnValue(response)
