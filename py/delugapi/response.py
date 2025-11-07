class DelugApiResponse:
    def __init__(self, result=None, error: Exception = None) -> None:
        self.result = result
        self.error = error

    def __str__(self) -> str:
        txt = ""
        if self.error:
            txt += f"Error: {self.error}\n"
        if self.result:
            result_str = str(self.result)
            txt += f"Result: {result_str[:32]} ..."
        return txt

    @property
    def is_ok(self) -> bool:
        return self.error is None

    @property
    def is_valid(self) -> bool:
        valid = self.is_ok and isinstance(self.result, dict)
        return valid
