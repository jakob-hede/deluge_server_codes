from __future__ import annotations
from pathlib import Path

from .logge import TorrentHandlorLoggor
from delugapi.torrent import DelugapiTorrent


class TorrentHandlor:
    handler_type = 'super'

    def __init__(self,
                 delugapi_torrent: DelugapiTorrent | None = None,  # todo> make 2 required and only args
                 survey_data: dict | None = None,
                 torrent_id: str = '',
                 torrent_name: str = '',
                 base_dir: str = '',
                 label: str = '',
                 quiet: bool = False,
                 ):
        self._delugapi_torrent: DelugapiTorrent | None = delugapi_torrent
        self._survey_data: dict = survey_data
        if delugapi_torrent:
            torrent_id = delugapi_torrent.tid
            torrent_name = delugapi_torrent.name
            base_dir = delugapi_torrent.download_location
            label = delugapi_torrent.label
        self._torrent_id: str = torrent_id
        self._torrent_name: str = torrent_name
        self._base_dir: str = base_dir
        self._label: str = label
        super().__init__()
        self.logger = TorrentHandlorLoggor()
        if not quiet:
            self.logger.info(f"TorrentHandlor initialized for '{self._torrent_name}' with label '{self._label}'")

    @property
    def torrent_id(self) -> str:
        if not self._torrent_id:
            raise ValueError("torrent_id is empty")
        return self._torrent_id

    @property
    def torrent_name(self) -> str:
        if not self._torrent_name:
            raise ValueError("torrent_name is empty")
        return self._torrent_name

    @property
    def base_dir(self) -> str:
        if not self._base_dir:
            raise ValueError("base_dir is empty")
        return self._base_dir

    @property
    def label(self) -> str:
        if not self._label:
            raise ValueError("label is empty")
        return self._label

    @property
    def title(self) -> str:
        title = self._delugapi_torrent.title
        return title


class TorrentLabelHandlor(TorrentHandlor):
    _klasses_dict: dict = {}
    label = 'super'
    _destin_dir: Path = Path('/ocean/video/misplaced')

    @classmethod
    def factory(cls, label: str, **kwargs) -> TorrentLabelHandlor | None:
        klass: type[TorrentHandlor] | None = cls._klasses_dict.get(label, None)
        if klass is None:
            return None
        instance = klass(label=label, **kwargs)  # noqa
        return instance

    @classmethod
    def __init_subclass__(cls, **kwargs):
        TorrentLabelHandlor._klasses_dict[cls.label] = cls

    @property
    def destin_dir(self) -> Path:
        return self._destin_dir


class TorrentHandlorMovin(TorrentLabelHandlor):
    handler_type = 'movin'
    label = 'movin'
    _destin_dir: Path = Path('/ocean/video/movies/movin')

    @property
    def destin_dir(self) -> Path:
        dest_dir = self._destin_dir
        try:
            structure_type = self._survey_data['torrent_data']['structure']['structure_type']
        except (KeyError, TypeError):
            self.logger.warning("Could not determine structure_type from survey_data, using base destin_dir")
            return dest_dir
        if not structure_type == 'single_directory':
            dir_name = self.title.lower()
            dest_dir = self._destin_dir / dir_name
        return dest_dir


class TorrentHandlorTvin(TorrentLabelHandlor):
    handler_type = 'tvin'
    label = 'tv-in'
    _destin_dir: Path = Path('/ocean/video/tv/_tvin')

    @property
    def destin_dir(self) -> Path:
        dest_dir = self._destin_dir
        if not self._delugapi_torrent.is_title_conform:
            return dest_dir

        tv_base_dir = self._destin_dir.parent
        dest_dir = tv_base_dir / self.title.lower()

        if self._delugapi_torrent.is_season_code_conform:
            season_code = self._delugapi_torrent.season_code
        else:
            season_code = 's00'
        dest_dir = dest_dir / season_code

        return dest_dir


class TorrentHandlorTvarc(TorrentLabelHandlor):
    handler_type = 'tvarc'
    label = 'tv-arc'
    _destin_dir: Path = Path('/ocean/video/tv/_tvarc')

    @property
    def destin_dir(self) -> Path:
        dest_dir = self._destin_dir
        if not self._delugapi_torrent.is_title_conform:
            return dest_dir

        tv_base_dir = self._destin_dir.parent
        dest_dir = tv_base_dir / self.title.lower()

        return dest_dir
