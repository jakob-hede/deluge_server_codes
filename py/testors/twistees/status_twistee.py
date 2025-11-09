from __future__ import annotations
from typing import Generator, Any
from twisted.internet import defer, task
from twisted.internet.interfaces import IReactorTime

from twistin.response import TwistResponse
from twistin.twistee import Twistee


class StatusTwistee(Twistee):
    def __init__(self):
        super().__init__()

    @defer.inlineCallbacks
    def main_twistee_func(self, reactor_clock: IReactorTime) -> Generator[Any, Any, TwistResponse]:
        self.loggor.exclaim('main_twistee_func')
        self.loggor.debug('Starting async MAIN STATUS process...')
        # response = yield self.dummy_subfunc(reactor_clock)
        response = yield self.status_subfunc(reactor_clock)
        defer.returnValue(response)

    @defer.inlineCallbacks
    def status_subfunc(self, reactor_clock: IReactorTime) -> Generator[Any, Any, TwistResponse]:
        self.loggor.exclaim('status_subfunc')
        self.loggor.debug('Starting async STATUS SUB process...')
        delay: float = 1
        callee = lambda: None
        yield task.deferLater(reactor_clock, delay, callable=callee)
        self.loggor.debug('Async STATUS SUB process completed')
        reply_dict: dict = {'status': 'success', 'duration': 1}
        response = TwistResponse(result=reply_dict)
        defer.returnValue(response)

    @defer.inlineCallbacks
    def dummy_subfunc(self, reactor_clock: IReactorTime) -> Generator[Any, Any, TwistResponse]:
        self.loggor.exclaim('dummy_subfunc')
        self.loggor.debug('Starting async DUMMY SUB process...')
        delay: float = 1
        callee = lambda: None
        yield task.deferLater(reactor_clock, delay, callable=callee)
        self.loggor.debug('Async DUMMY SUB process completed')
        reply_dict: dict = {'status': 'success', 'duration': 1}
        response = TwistResponse(result=reply_dict)
        defer.returnValue(response)
