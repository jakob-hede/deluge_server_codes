from __future__ import annotations
from typing import Generator, Any
from twisted.internet import defer, task
from twisted.internet.interfaces import IReactorTime

from twistin.twistee import Twistee


class TwisteeExample1(Twistee):
    def __init__(self):
        super().__init__()

    @defer.inlineCallbacks
    def main_reactize_func(self) -> Generator[Any, Any, dict]:
        # def main_reactize_func(self, reactor_clock: IReactorTime) -> Generator[Any, Any, dict]:
        self.loggor.exclaim('main_reactize_func')
        # print('reactize')
        self.loggor.debug('Starting async dummy process...')
        # yield task.deferLater(reactor, 1, lambda: None)
        from twisted.internet import reactor
        reactor_clock: IReactorTime = reactor  # ty pe: ignore
        delay: float = 1
        callee = lambda: None
        yield task.deferLater(reactor_clock, delay, callable=callee)
        self.loggor.debug('Async dummy process completed')
        reply: dict = {'status': 'success', 'duration': 1}

        # from twistin.exceptions import TwistinTestException
        # exc = TwistinTestException('Simulated exception in main_reactize_func')
        # # exc = Exception('Simulated exception in reactize')
        # raise exc

        defer.returnValue(reply)

"""
def deferLater(
    clock: IReactorTime,
    delay: float,
    callable: Optional[Callable[..., _T]] = None,
    *args: object,
    **kw: object,
"""