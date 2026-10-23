from __future__ import annotations
import os
import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime
from functools import cached_property
from pathlib import Path

import yaml

from . import extensions
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
        self.is_renamed: bool = False
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
    current_files: list[dict] | None = None
    # the torrent's own meta-files go under a dot-directory, which Jellyfin's scanner skips, named by its hash
    oceanmeta_dir_name: str = '.oceanmeta'
    # set by the hook for the record: the torrent's other hashes, the chain's entry, and the survey's text as it came
    record_alternates: tuple[str, ...] = ()
    record_entry: str | None = None
    survey_text: str | None = None

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
    def rename_plan(self) -> tuple[str, str] | list[tuple[int, str]] | None:
        return None

    @property
    def is_in_pattern_dir(self) -> bool:
        return False

    @property
    def pattern_dir(self) -> Path | None:
        return None

    def file_rename_plan(self, files: list[dict]) -> list[tuple[int, str]]:
        return []

    @property
    def latest_files(self) -> list[dict]:
        # the daemon's files as last read: after a confirmed rename, else as fetched before it
        return self.current_files if self.current_files is not None else self._delugapi_torrent.files

    @property
    def sidecar_dir(self) -> Path | None:
        # the folder that will hold the largest file after the move, where Jellyfin puts its own files: a movie's
        # folder, or a TV episode's season folder
        files = self.latest_files
        if not files:
            self.logger.info("No sidecar folder, torrent has no files")
            return None
        largest_file = max(files, key=lambda file: file.get('size', 0))
        return self.destin_dir / Path(largest_file['path']).parent

    @property
    def sidecar_files(self) -> dict[str, str]:
        # the torrent's record and its survey as it came, under the dot-directory, each named by its hash, so a season
        # folder fed by many torrents holds each one's
        oceanmeta = f'{self.oceanmeta_dir_name}/{self.torrent_id}'
        sidecar_files = {f'{oceanmeta}.yml': self.oceanmeta_yml}
        if self.survey_text is None:
            self.logger.info(f"Sidecars {list(sidecar_files)}, no survey to copy beside the record")
        else:
            sidecar_files[f'{oceanmeta}.survey.yml'] = self.survey_text
        return sidecar_files

    @property
    def oceanmeta_yml(self) -> str:
        # what the folder holds and where it came from, the hashes the torrent is known by first
        browser_source_data = self._browser_source_data
        # the record's magnet, subtitles and extras are long and stay in the record itself
        click = {key: value for key, value in browser_source_data.items()
                 if key not in ('magnet', 'subtitles', 'extras')} if browser_source_data else None
        hashes = [self.torrent_id, *(alternate for alternate in self.record_alternates if alternate != self.torrent_id)]
        record = {
            'written': datetime.now().astimezone().isoformat(timespec='seconds'),
            'infohash': self.torrent_id,
            'hashes': hashes,
            'entry': self.record_entry,
            'label': self.label,
            'release_name': self._delugapi_torrent.name,  # as fetched before the rename
            'folder': getattr(self, 'pattern_dir_name', None),
            'renamed': self.is_renamed,
            'destination': str(self.destin_dir),
            'orig_files': [file['path'] for file in self._delugapi_torrent.orig_files],
            'files': [file['path'] for file in self.latest_files],
            'click': click,
        }
        return yaml.safe_dump(record, sort_keys=False, allow_unicode=True)

    def write_sidecars(self, sidecar_dir: Path) -> list[Path]:
        # a sidecar that cannot be built or written is logged and skipped, it never blocks the move; a name with a
        # directory part gets its directory, mode 777 as the folder is, and every file is 666, so Jellyfin and the
        # hand can change them as their own
        sidecar_paths: list[Path] = []
        try:
            sidecar_files = self.sidecar_files
        except Exception as exc:
            self.logger.error(f"Sidecars not built: {exc!r}")
            return sidecar_paths
        try:
            sidecar_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.logger.error(f"Sidecar folder not made: '{sidecar_dir}', {exc}")
            return sidecar_paths
        for name, content in sidecar_files.items():
            sidecar_path = sidecar_dir / name
            tmp_path = sidecar_path.parent / f'.{sidecar_path.name}.{os.getpid()}.tmp'
            try:
                if sidecar_path.parent != sidecar_dir:
                    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
                    sidecar_path.parent.chmod(0o777)
                tmp_path.write_text(content, encoding='utf-8')
                tmp_path.chmod(0o666)
                os.replace(tmp_path, sidecar_path)
            except OSError as exc:
                self.logger.error(f"Sidecar not written: '{sidecar_path}', {exc}")
                continue
            self.logger.info(f"Sidecar written: '{sidecar_path}'")
            sidecar_paths.append(sidecar_path)
        return sidecar_paths

    @property
    def is_jellyable(self) -> bool:
        return self._is_jellyable


class TorrentHandlorMovin(TorrentLabelHandlor):
    handler_type = 'movin'
    label = 'movin'
    _destin_dir: Path = Path('/ocean/video/movies/movin')
    _is_jellyable: bool = True
    jelly_library_name = 'movin'
    video_extensions: tuple[str, ...] = extensions.video_extensions
    subtitle_extensions: tuple[str, ...] = extensions.subtitle_extensions
    subtitle_languages: dict[str, str] = {'english': 'en', 'eng': 'en', 'en': 'en', 'danish': 'da', 'dan': 'da', 'da': 'da'}
    jellyfin_names: tuple[str, ...] = ('movie.nfo', 'folder.jpg', 'poster.jpg', 'backdrop.jpg', 'fanart.jpg', 'landscape.jpg',
                                       'logo.png', 'banner.jpg', 'thumb.jpg', 'clearart.png', 'disc.png')
    parked_prefix: str = 'release.'

    @cached_property
    def pattern_dir_name(self) -> str:
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
        return dir_name

    @property
    def is_in_pattern_dir(self) -> bool:
        paths = [file['path'] for file in self._delugapi_torrent.files]
        pattern_dir_name = self.pattern_dir_name
        return bool(paths) and all(path.startswith(f'{pattern_dir_name}/') for path in paths)

    @property
    def pattern_dir(self) -> Path | None:
        return self._destin_dir / self.pattern_dir_name

    @cached_property
    def rename_plan(self) -> tuple[str, str] | list[tuple[int, str]] | None:
        # decided by the daemon's file paths, the survey's structure_type is only logged beside;
        # a folder plan is (folder, new_folder) for rename_folder, a files plan [(index, new_path)] for rename_files
        try:
            structure_type = self._survey_data['torrent_data']['structure']['structure_type']
        except (KeyError, TypeError):
            structure_type = None
        files = self._delugapi_torrent.files
        paths = [file['path'] for file in files]
        root_parts = {path.split('/', 1)[0] for path in paths}
        if not paths:
            self.logger.info(f"No rename plan, torrent has no files (structure_type '{structure_type}')")
            return None
        if all('/' in path for path in paths) and len(root_parts) == 1:
            folder = root_parts.pop()
            pattern_dir_name = self.pattern_dir_name
            if self.is_in_pattern_dir:
                self.logger.info(f"No rename plan, files already in '{pattern_dir_name}/' (structure_type '{structure_type}')")
                return None
            rename_plan = (f'{folder}/', f'{pattern_dir_name}/')
        elif len(paths) == 1 and '/' not in paths[0]:
            pattern_dir_name = self.pattern_dir_name
            suffix = Path(paths[0]).suffix.lower()
            # a bare video file is wrapped straight into its final name, so it needs one rename
            new_name = f'{pattern_dir_name}{suffix}' if suffix in self.video_extensions else paths[0]
            rename_plan = [(files[0]['index'], f'{pattern_dir_name}/{new_name}')]
        else:
            self.logger.info(f"No rename plan, files not under one root folder (structure_type '{structure_type}')")
            return None
        self.logger.info(f"Rename plan: {rename_plan} (structure_type '{structure_type}')")
        return rename_plan

    def file_rename_plan(self, files: list[dict]) -> list[tuple[int, str]]:
        # the movie file, the English and Danish subtitles and the names Jellyfin's saver writes, renamed inside
        # the pattern folder; only the pairs whose path changes, so a re-fired event plans nothing
        pattern_dir_name = self.pattern_dir_name
        prefix = f'{pattern_dir_name}/'
        if not files:
            self.logger.info("No file rename plan, torrent has no files")
            return []
        if not all(file['path'].startswith(prefix) for file in files):
            self.logger.info(f"No file rename plan, files not all under '{prefix}'")
            return []
        # every path held now or planned stays taken, since deluge renames onto a held path unchecked
        taken_paths = {file['path'] for file in files}
        file_plan: dict[int, str] = {}

        video_files = [file for file in files if Path(file['path']).suffix.lower() in self.video_extensions]
        movie_file = max(video_files, key=lambda file: file.get('size', 0)) if video_files else None
        movie_stem = Path(movie_file['path']).stem if movie_file else None
        if movie_file:
            new_path = f"{prefix}{pattern_dir_name}{Path(movie_file['path']).suffix.lower()}"
            self._plan_file_rename(movie_file, new_path, 'movie file', taken_paths, file_plan)
        else:
            self.logger.info("File rename: no movie file among the files")

        en_sizes: set[int] = set()
        root_copies: list[dict] = []
        for file in files:
            path = file['path']
            file_path = Path(path)
            if file_path.suffix.lower() not in self.subtitle_extensions:
                continue
            if file_path.name.startswith(self.parked_prefix):
                self.logger.info(f"File rename: subtitle '{path}' skipped, already parked")
                continue
            is_at_root = '/' not in path[len(prefix):]
            stem = file_path.stem
            if is_at_root and stem == movie_stem:
                root_copies.append(file)
                continue
            # a name that begins with the movie's stem is read after it, so a title word such as Danish is no language
            tag = stem[len(movie_stem) + 1:] if movie_stem and stem.startswith(f'{movie_stem}.') else stem
            tokens = [token.strip().lower() for token in tag.split('.')]
            languages = {self.subtitle_languages[token] for token in tokens if token in self.subtitle_languages}
            if len(languages) != 1:
                reason = 'no English or Danish token' if not languages else 'both English and Danish tokens'
                self.logger.info(f"File rename: subtitle '{path}' skipped, {reason}")
                continue
            language = languages.pop()
            flags = ''
            if any(token in ('sdh', 'hi', 'cc') for token in tokens):
                flags += '.sdh'
            if 'forced' in tokens:
                flags += '.forced'
            new_path = f'{prefix}{pattern_dir_name}.{language}{flags}{file_path.suffix.lower()}'
            is_planned = self._plan_file_rename(file, new_path, f'{language}{flags} subtitle', taken_paths, file_plan)
            if is_planned and language == 'en' and 'size' in file:
                en_sizes.add(file['size'])

        site = self._browser_source_data.get('site') if self._browser_source_data else None
        for file in root_copies:
            path = file['path']
            file_path = Path(path)
            if file.get('size') in en_sizes:
                new_path = f'{prefix}{self.parked_prefix}{file_path.name}'
                self._plan_file_rename(file, new_path, 'untagged root copy, the size of an en subtitle', taken_paths, file_plan)
            elif site == 'yts':
                new_path = f'{prefix}{pattern_dir_name}.en{file_path.suffix.lower()}'
                self._plan_file_rename(file, new_path, 'untagged root copy, en by the yts convention', taken_paths, file_plan)
            else:
                self.logger.info(f"File rename: untagged root copy '{path}' skipped, no en subtitle of its size and site '{site}' is not yts")

        for file in files:
            path = file['path']
            name = Path(path).name
            if '/' not in path[len(prefix):] and name.lower() in self.jellyfin_names:
                new_path = f'{prefix}{self.parked_prefix}{name}'
                self._plan_file_rename(file, new_path, "a name Jellyfin's saver writes", taken_paths, file_plan)

        plan = list(file_plan.items())
        self.logger.info(f"File rename plan: {plan}")
        return plan

    def _plan_file_rename(self, file: dict, new_path: str, rule: str, taken_paths: set[str], file_plan: dict[int, str]) -> bool:
        path = file['path']
        if new_path == path:
            self.logger.info(f"File rename: '{path}' already named ({rule})")
            return True
        if new_path in taken_paths:
            self.logger.info(f"File rename: '{path}' skipped, '{new_path}' is taken ({rule})")
            return False
        taken_paths.add(new_path)
        file_plan[file['index']] = new_path
        self.logger.info(f"File rename: '{path}' -> '{new_path}' ({rule})")
        return True

    @property
    def destin_dir(self) -> Path:
        dest_dir = self._destin_dir
        if self.is_renamed:
            return dest_dir
        try:
            structure_type = self._survey_data['torrent_data']['structure']['structure_type']
        except (KeyError, TypeError):
            self.logger.warning("Could not determine structure_type from survey_data, nesting under pattern folder for safety")
            return self._destin_dir / self.pattern_dir_name
        if not structure_type == 'single_directory':
            dir_name = self.pattern_dir_name
            dest_dir = self._destin_dir / dir_name
        return dest_dir

    @property
    def sidecar_files(self) -> dict[str, str]:
        # the record and the survey, and movie.nfo at the folder's root, where Jellyfin reads it, for a movie record
        browser_source_data = self._browser_source_data
        media_type = browser_source_data.get('media_type') if browser_source_data else None
        media_title = browser_source_data.get('media_title') if browser_source_data else None
        has_id = bool(browser_source_data.get('imdb_id') or browser_source_data.get('tmdb_id')) if browser_source_data else False
        sidecar_files = super().sidecar_files
        if not browser_source_data:
            self.logger.info(f"Sidecars {list(sidecar_files)}, no movie.nfo, no browser-source record")
        elif media_type != 'movie':
            self.logger.info(f"Sidecars {list(sidecar_files)}, no movie.nfo, browser-source media_type '{media_type}' is not movie")
        elif not media_title:
            self.logger.info(f"Sidecars {list(sidecar_files)}, no movie.nfo, browser-source record has no media_title")
        elif not has_id:
            self.logger.info(f"Sidecars {list(sidecar_files)}, no movie.nfo, browser-source record has no imdb_id or tmdb_id")
        else:
            sidecar_files['movie.nfo'] = self.movie_nfo
            self.logger.info(f"Sidecars {list(sidecar_files)}")
        return sidecar_files

    @property
    def movie_nfo(self) -> str:
        # read by Jellyfin before its own lookup, then rewritten whole by its nfo saver
        browser_source_data = self._browser_source_data
        media_year = browser_source_data.get('media_year')
        imdb_id = browser_source_data.get('imdb_id')
        tmdb_id = browser_source_data.get('tmdb_id')
        movie = ET.Element('movie')
        ET.SubElement(movie, 'title').text = browser_source_data['media_title']
        if media_year is not None:
            ET.SubElement(movie, 'year').text = str(media_year)
        if imdb_id:
            ET.SubElement(movie, 'imdbid').text = str(imdb_id)
        if tmdb_id:
            ET.SubElement(movie, 'tmdbid').text = str(tmdb_id)
        if imdb_id:
            ET.SubElement(movie, 'uniqueid', type='imdb', default='true').text = str(imdb_id)
        if tmdb_id:
            ET.SubElement(movie, 'uniqueid', type='tmdb').text = str(tmdb_id)
        ET.indent(movie, space='  ')
        movie_xml = ET.tostring(movie, encoding='unicode')
        return f'<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n{movie_xml}\n'


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
