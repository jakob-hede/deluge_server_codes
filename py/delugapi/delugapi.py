from typing import Generator, Any

# from twisted.internet import defer, reactor  # noqa
from deluge.ui.client import client as ui_client
from .transaction import DelugApiTransaction
from .twistin_adaptors import defer_inline_callbacks, defer_return_value, ReactorInterface, adapted_reactor



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

    @defer_inline_callbacks
    def transactize(self, transaction: DelugApiTransaction) -> Generator[Any, Any, dict]:
        print(f"Transactizing {transaction}")

        # if not ReactorInterface.running:  # noqa
        if not adapted_reactor.running:  # noqa
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
            defer_return_value(reply)

    @classmethod
    def delugapi_wrap(cls, function):
        print(f"wrap {function}")
        if adapted_reactor.running:  # noqa
            # Reactor already running (inside Twistor) — call directly
            # and return the Deferred for the caller to yield
            d = function()
            return d
        else:
            # We manage the reactor lifecycle: start it and auto-stop after completion
            def wrapped():
                d = function()
                d.addBoth(lambda _: adapted_reactor.stop())
                return d
            adapted_reactor.callWhenRunning(wrapped)  # noqa
            adapted_reactor.run()  # noqa
            print("Reactor finished (self-managed)")
            return None

    @classmethod
    def delugapi_stop(cls):
        print("Stopping ReactorType...")
        if adapted_reactor.running:  # noqa
            adapted_reactor.stop()  # noqa
        print("Reactor stopped")

    # @classmethod
    # def delugapi_twistorize(cls, function):
    #     print(f"delugapi_twistorize {function}")
    #     a = reactor.callWhenRunning(function)  # noqa
    #     b = reactor.run()  # noqa
    #     print("Reactor finished")
