from abc import abstractmethod
from typing import Generator, Any, TYPE_CHECKING, cast

from twisted.internet import defer, reactor as twisted_reactor, task as twisted_task
from twisted.internet.interfaces import IReactorTime

ReactorInterface = IReactorTime
adapted_reactor: ReactorInterface = twisted_reactor  # type: ignore
adapted_task = twisted_task

#twisteds:
defer_inline_callbacks = defer.inlineCallbacks
defer_return_value = defer.returnValue

from twistin import (
    Twistee as _AdaptedTwistee,
    TwistResponse as _AdaptedTwistResponse,
    Twistor as _AdaptedTwistor,
    TwistinIncompleteException as _AdaptedTwistinIncompleteException,
)


# if TYPE_CHECKING:
#     # x = DelugApiResponse
#     from response import DelugApiResponse as DelugApiResponseType
# else:
#     type DelugApiResponseType = 'DelugApiResponse'


class DelugApiResponse(_AdaptedTwistResponse):
    pass


class IncompleteDelugApiResponse(DelugApiResponse):
    def __init__(self, message: str = "Incomplete Response") -> None:
        super().__init__(result=None, error=_AdaptedTwistinIncompleteException(message))


class DelugApiTwistee(_AdaptedTwistee):
    @abstractmethod
    @defer.inlineCallbacks
    def main_twistee_func(self, reactor_clock: IReactorTime) -> Generator[Any, Any, DelugApiResponse]:
        ...


class DelugApiTwistor(_AdaptedTwistor):
    def executize(self) -> DelugApiResponse:
        adapted_response: _AdaptedTwistResponse = super().executize()
        delugapi_response: DelugApiResponse = cast(DelugApiResponse, adapted_response)
        return delugapi_response
