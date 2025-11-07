from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generator, Any  # , runtime_checkable, Protocol

from twisted.internet import defer

from executin.logge import Loggor


class Twistee(ABC):
    def __init__(self):
        super().__init__()
        self.loggor = Loggor(klass=self.__class__)

    @abstractmethod
    @defer.inlineCallbacks
    def main_reactize_func(self) -> Generator[Any, Any, dict]:
        self.loggor.exclaim('reactize')
        raise NotImplementedError('main_reactize_func must be implemented by subclass')

# # TwisteeProtocol shall be a Protocol with method main_reactize_func
# @runtime_checkable
# class TwisteeProtocol(Protocol):
#     def main_reactize_func(self) -> Generator[Any, Any, dict]:
#         ...
