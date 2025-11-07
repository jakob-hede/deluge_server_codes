from __future__ import annotations
from typing import TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from delugapi import DelugapiClient


class ExecutinException(Exception):
    """Exception raised for errors in the Executin module."""

    def __str__(self):
        super_str = super().__str__()
        txt = (f"\n- {self.__class__.__name__}:"
               f"\n\t - args: {self.args}"
               f"\n\t - super_str: {super_str}"
               )
        return txt

    @classmethod
    def factory_from_exception(cls, e: Exception, *args) -> ExecutinException:
        enfo = f'{e.__class__.__name__}: {e.args}'
        args_str = ', '.join([str(a) for a in args])
        exc = cls(f"Wrapped exception: {enfo} |  {args_str}")
        return exc


class TransactionException(ExecutinException):
    """Exception raised for transaction errors in the Executin module."""
    pass


class ExecutorException(ExecutinException):
    """Exception raised for executor errors in the Executin module."""
    pass


class Commons:
    singleton: Commons | None = None
    deluge_root_dir: Path = Path('/deluge')

    @classmethod
    def __init_subclass__(cls):
        super().__init_subclass__()
        singleton = Commons()
        Commons.singleton = singleton

    def __init__(self):
        super().__init__()
        self.is_at_daemon: bool = False
        self._api_client: DelugapiClient | None = None
        if self.deluge_root_dir.is_dir():
            self.is_at_daemon = True
        else:
            self.deluge_root_dir = Path(
                # '/opt/projects/ronja_project/roots/media_docker_root/sermin/docker/deluge/_develop'
                '/opt/projects/deluge_source_project/deluge_root_dir'
            )
        if not self.deluge_root_dir.is_dir():
            raise ValueError(f"Commons; deluge_root_dir '{self.deluge_root_dir}' is not a directory")

    #         api_client = DelugapiClient()
    @property
    def api_client(self) -> DelugapiClient:
        if not self._api_client:
            from delugapi import DelugapiClient
            self._api_client = DelugapiClient()
        return self._api_client

    @staticmethod
    def timestamp() -> str:
        from datetime import datetime

        now = datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        return timestamp_str


class _SubCommons(Commons):
    pass
