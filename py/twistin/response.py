from twistin.exceptions import TwistinIncompleteException


class TwistResponse:
    def __init__(self, result: dict | None = None, error: Exception | None = None) -> None:
        self.result: dict | None = result
        self.error: Exception | None = error

    def __str__(self) -> str:
        txt = f'EMPTY {self.__class__.__name__}\n'
        if self.error:
            txt = f'Error: {self.error}\n'
        if self.result:
            result_str = str(self.result)
            txt = f'Result: {result_str[:32]} ...\n'
        return txt

    @property
    def is_ok(self) -> bool:
        return self.error is None

    @property
    def is_valid(self) -> bool:
        valid = self.is_ok and isinstance(self.result, dict)
        return valid


class IncompleteTwistResponse(TwistResponse):
    def __init__(self, message: str = "Incomplete TwistResponse") -> None:
        super().__init__(result=None, error=TwistinIncompleteException(message))
