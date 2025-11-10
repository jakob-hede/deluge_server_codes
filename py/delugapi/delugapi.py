from typing import Generator, Any

from twisted.internet import defer, reactor  # noqa
from twisted.internet.interfaces import IReactorTime

from delugapi.transaction_twistee import DelugApiTransactionTwistee
from deluge.ui.client import client as ui_client
from delugapi.transaction import DelugApiTransaction
from twistin import TwistResponse


class DelugApi:
    def __init__(
            self,
            host: str = "127.0.0.1",
            port: int = 58846,
            user: str = "deluge",
            password: str = "deluge") -> None:
        super().__init__()
        self.host: str = host
        self.port: int = port
        self.user: str = user
        self.password: str = password
        print(self)

    def __str__(self) -> str:
        txt: str = f"DelugApi {self.host}, {self.port}, {self.user}, {self.password}"
        return txt

    @defer.inlineCallbacks
    def transactize(self, transaction: DelugApiTransaction) -> Generator[Any, Any, dict]:
        print(f"Transactizing {transaction}")

        if not reactor.running:  # noqa
            raise RuntimeError("Reactor not running, cannot transactize")

        reply = {}
        try:
            # Connect to daemon
            yield ui_client.connect(
                host=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
            )
            is_connected = ui_client.connected()
            if not is_connected:
                raise ConnectionError("Failed to connect to daemon")

            # NOW yield the transaction execution since it's a deferred
            reply = yield transaction.executize()
            transaction.response.result = reply

        except Exception as e:
            print(f"Exception in transaction: {e}")
            transaction.response.error = e
        finally:
            if ui_client.connected():
                ui_client.disconnect()
            defer.returnValue(reply)

    @classmethod
    def delugapi_wrap(cls, function):
        print(f"wrap {function}")
        a = reactor.callWhenRunning(function)  # noqa
        b = reactor.run()  # noqa
        print("Reactor finished")

    @classmethod
    def delugapi_stop(cls):
        print("Stopping reactor...")
        reactor.stop()  # noqa
        print("Reactor stopped")

    @classmethod
    def delugapi_twistorize(cls, function):
        print(f"delugapi_twistorize {function}")
        a = reactor.callWhenRunning(function)  # noqa
        b = reactor.run()  # noqa
        print("Reactor finished")



# class DelugApiTransactizeTwistee(DelugApiTransactionTwistee):
#     @defer.inlineCallbacks
#     def main_twistee_func(self, reactor_clock: IReactorTime) -> Generator[Any, Any, TwistResponse]:
#         reply: dict = yield self.transactize()
#         response = TwistResponse(result=reply)
#         defer.returnValue(response)
