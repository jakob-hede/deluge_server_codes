from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generator, Any, runtime_checkable, Protocol

from twisted.internet import defer
from twisted.internet.interfaces import IReactorTime

from executin.logge import Loggor
from twistin.response import TwistResponse


class Twistee(ABC):
    def __init__(self):
        super().__init__()
        self.loggor = Loggor(klass=self.__class__)

    @abstractmethod
    @defer.inlineCallbacks
    def main_reactize_func(self, reactor_clock: IReactorTime) -> Generator[Any, Any, TwistResponse]:
        # def main_reactize_func(self) -> Generator[Any, Any, TwistResponse]:
        ...
        # self.loggor.exclaim('main_reactize_func')
        # raise NotImplementedError('main_reactize_func must be implemented by subclass')


class DummyTwistee(Twistee):
    def __init__(self):
        super().__init__()

    @defer.inlineCallbacks
    def main_reactize_func(self, reactor_clock: IReactorTime) -> Generator[Any, Any, TwistResponse]:
        # def main_reactize_func(self) -> Generator[Any, Any, TwistResponse]:
        raise NotImplementedError('DummyTwistee main_reactize_func not implemented')


# TwisteeProtocol shall be a Protocol with method main_reactize_func
@runtime_checkable
class TwisteeProtocol(Protocol):
    def main_reactize_func(self, reactor_clock: IReactorTime) -> Generator[Any, Any, TwistResponse]:
        # def main_reactize_func(self) -> Generator[Any, Any, TwistResponse]:
        ...
