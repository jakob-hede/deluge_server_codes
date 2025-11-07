from __future__ import annotations


class TwistinException(Exception):
    """Exception raised for errors in the Twistin module."""

    def x__str__(self):
        super_str = super().__str__()
        txt = (f"\n- {self.__class__.__name__}:"
               f"\n\t - args: {self.args}"
               f"\n\t - super_str: {super_str}"
               )
        return txt

    @classmethod
    def factory_from_exception(cls, e: Exception, *args) -> TwistinException:
        enfo = f'{e.__class__.__name__}: {e.args}'
        args_str = ', '.join([str(a) for a in args])
        exc = cls(f"Wrapped exception: {enfo} |  {args_str}")
        return exc


class TwistinTestException(TwistinException):
    """Exception raised for transaction errors in the Twistin module."""
    pass
