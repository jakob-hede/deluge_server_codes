from __future__ import annotations
import os
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


class Commons:
    singleton: Commons | None = None
    deluge_root_dir: Path = Path('/deluge')
    # the live box's addresses, the daemon's and Jellyfin's; the container's environment overrides each, through
    # MAGNETICS_DELUGED_HOST, MAGNETICS_DELUGED_PORT and MAGNETICS_JELLYFIN_URL, an unset or empty variable leaving
    # the default, so a second daemon on the box sets its own in its compose
    default_deluged_host: str = '10.4.9.12'
    default_deluged_port: int = 58846
    default_jellyfin_url: str = 'http://10.4.9.11:8096'

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
        self.deluged_host: str = self.environ_text('MAGNETICS_DELUGED_HOST', self.default_deluged_host)
        self.deluged_port: int = self.environ_int('MAGNETICS_DELUGED_PORT', self.default_deluged_port)
        self.jellyfin_url: str = self.environ_text('MAGNETICS_JELLYFIN_URL', self.default_jellyfin_url).rstrip('/')

    @staticmethod
    def environ_text(name: str, default: str) -> str:
        # an empty value counts as unset
        return os.environ.get(name) or default

    @staticmethod
    def environ_int(name: str, default: int) -> int:
        # loud at the first event, never a silent default for a value that is there and wrong
        text = os.environ.get(name)
        if not text:
            return default
        try:
            return int(text)
        except ValueError:
            raise ValueError(f"Commons; {name} '{text}' is not an integer") from None

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
