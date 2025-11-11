from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generator, Any, runtime_checkable, Protocol

from twisted.internet import defer
from twisted.internet.interfaces import IReactorTime

from executin.logge import Loggor
from .response import TwistResponse


# TwisteeProtocol shall be a Protocol with method main_twistee_func
@runtime_checkable
class TwisteeProtocol(Protocol):
    def main_twistee_func(self, reactor_clock: IReactorTime) -> Generator[Any, Any, TwistResponse]:
        # def main_twistee_func(self) -> Generator[Any, Any, TwistResponse]:
        ...


class Twistee(ABC):
    def __init__(self):
        super().__init__()
        self.loggor = Loggor(klass=self.__class__)

    @abstractmethod
    @defer.inlineCallbacks
    def main_twistee_func(self, reactor_clock: IReactorTime) -> Generator[Any, Any, TwistResponse]:
        # def main_twistee_func(self) -> Generator[Any, Any, TwistResponse]:
        ...
        # self.loggor.exclaim('main_twistee_func')
        # raise NotImplementedError('main_twistee_func must be implemented by subclass')


class DummyTwistee(Twistee):
    def __init__(self):
        super().__init__()

    @defer.inlineCallbacks
    def main_twistee_func(self, reactor_clock: IReactorTime) -> Generator[Any, Any, TwistResponse]:
        # def main_twistee_func(self) -> Generator[Any, Any, TwistResponse]:
        raise NotImplementedError('DummyTwistee main_twistee_func not implemented')
