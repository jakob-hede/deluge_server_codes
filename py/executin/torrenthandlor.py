from __future__ import annotations
import re
import unicodedata
from pathlib import Path

from .logge import TorrentHandlorLoggor
from delugapi.torrent import DelugapiTorrent


media_letter_spellings: dict[str, str] = {
    'æ': 'ae', 'ø': 'oe', 'å': 'aa', 'œ': 'oe', 'ß': 'ss', 'ð': 'd', 'þ': 'th', 'ł': 'l', 'đ': 'd',
    'Æ': 'AE', 'Ø': 'OE', 'Å': 'AA', 'Œ': 'OE', 'Ð': 'D', 'Þ': 'TH', 'Ł': 'L', 'Đ': 'D',
}


def media_dir_name(media_title: str, media_year: int | None) -> str:
    """Folder name from a browser-source record's media_title and media_year, '' when the title sanitizes to nothing."""
    spelled_title = ''.join(media_letter_spellings.get(c, c) for c in media_title)
    decomposed_title = unicodedata.normalize('NFKD', spelled_title)
    plain_title = ''.join(c for c in decomposed_title if not unicodedata.combining(c))
    dir_name = re.sub(r'[^a-z0-9]+', '.', plain_title.lower()).strip('.')
    if not dir_name:
        return ''
    if isinstance(media_year, int):
        dir_name = f'{dir_name}.{media_year}'
    return dir_name


class TorrentHandlor:
    handler_type = 'super'

    def __init__(self,
                 delugapi_torrent: DelugapiTorrent | None = None,  # todo> make 2 required and only args
                 survey_data: dict | None = None,
                 browser_source_data: dict | None = None,
                 torrent_id: str = '',
                 torrent_name: str = '',
                 base_dir: str = '',
                 label: str = '',
                 quiet: bool = False,
                 ):
        self._delugapi_torrent: DelugapiTorrent | None = delugapi_torrent
        self._survey_data: dict = survey_data
        self._browser_source_data: dict | None = browser_source_data
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
    _is_jellyable: bool = False
    jelly_wrong_library_name: str = 'wrong-name'
    jelly_library_name: str = jelly_wrong_library_name

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

    @property
    def is_jellyable(self) -> bool:
        return self._is_jellyable


class TorrentHandlorMovin(TorrentLabelHandlor):
    handler_type = 'movin'
    label = 'movin'
    _destin_dir: Path = Path('/ocean/video/movies/movin')
    _is_jellyable: bool = True
    jelly_library_name = 'movin'

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
            browser_source_data = self._browser_source_data
            media_type = browser_source_data.get('media_type') if browser_source_data else None
            media_title = browser_source_data.get('media_title') if browser_source_data else None
            record_dir_name = media_dir_name(media_title, browser_source_data.get('media_year')) if media_title else ''
            if not browser_source_data:
                self.logger.info(f"Folder named by name rule: '{dir_name}', no browser-source record")
            elif media_type != 'movie':
                self.logger.info(f"Folder named by name rule: '{dir_name}', browser-source media_type '{media_type}' is not movie")
            elif not media_title:
                self.logger.info(f"Folder named by name rule: '{dir_name}', browser-source record has no media_title")
            elif not record_dir_name:
                self.logger.info(f"Folder named by name rule: '{dir_name}', browser-source media_title '{media_title}' sanitizes to nothing")
            else:
                dir_name = record_dir_name
                self.logger.info(f"Folder named by browser-source record: '{dir_name}' (media_via '{browser_source_data.get('media_via')}')")
            dest_dir = self._destin_dir / dir_name
        return dest_dir


class TorrentHandlorTvin(TorrentLabelHandlor):
    handler_type = 'tvin'
    label = 'tv-in'
    _destin_dir: Path = Path('/ocean/video/tv/_tvin')
    _is_jellyable: bool = True
    jelly_library_name = 'TV'

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
    _is_jellyable: bool = True
    jelly_library_name = 'TV'

    @property
    def destin_dir(self) -> Path:
        dest_dir = self._destin_dir
        if not self._delugapi_torrent.is_title_conform:
            return dest_dir

        tv_base_dir = self._destin_dir.parent
        dest_dir = tv_base_dir / self.title.lower()

        return dest_dir
