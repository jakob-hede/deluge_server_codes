"""naming — the name a human thinks in, for the title of a phone notification, alike at both ends of the chain.

One text in two repos: magnetics' ``src/magneting/libs/naming.py`` for the click, deluge_server_codes'
``py/executin/naming.py`` for the hook. A change is made in both or in neither; ``md5sum`` over the two
prints one hash, the discipline of the testors' import helpers. Pure: no I/O, no logging, the standard
library only, 3.12 syntax.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

MEDIA_TYPE_MOVIE = 'movie'
MEDIA_TYPES_EPISODIC = ('series', 'episode')
# the file extensions a trimmed name drops, a closed set: a short last word of a dotted name is no extension
FILE_EXTENSIONS = ('mkv', 'mp4', 'm4v', 'avi', 'mov', 'wmv', 'ts', 'webm', 'iso', 'srt', 'sub', 'ass', 'zip', 'rar',
                   '7z', 'nfo', 'txt')


class HumanNamor:
    """The click record's title when the lookup gave one, else the release name trimmed of its bracket soup."""

    # magnetics' label_hintor.TvLabelRulor single-episode pattern, copied: this text cannot import the hintor
    episode_re: re.Pattern[str] = re.compile(r'\bS\d{1,2}E\d{1,3}(?!\d)(?!-E?\d|E\d)', re.IGNORECASE)
    bracket_re: re.Pattern[str] = re.compile(r'\[[^\]]*\]')
    extension_re: re.Pattern[str] = re.compile(rf"\.(?:{'|'.join(FILE_EXTENSIONS)})$", re.IGNORECASE)
    # a dot that is not a decimal point: kept in 5.1 and 13.1.0, a space in E04.1080p and in Name.2020
    word_dot_re: re.Pattern[str] = re.compile(r'\.(?!(?<=\d\.)\d(?!\d))')
    space_re: re.Pattern[str] = re.compile(r'\s+')
    max_length = 60

    @classmethod
    def human_name(cls, record: Any, fallback: str | None) -> str:
        """``record`` is a mapping or an object carrying media_title, media_year and media_type, or None.

        A movie with a title is ``<title> (<year>)``, the year dropped when unknown; a series or an episode
        with a title is ``<title> SxxEyy`` when the fallback carries an SxxEyy, else ``<title>``; anything
        else is the fallback trimmed.
        """
        media_title = cls._field(record, 'media_title')
        media_type = cls._field(record, 'media_type')
        if media_title and media_type == MEDIA_TYPE_MOVIE:
            media_year = cls._field(record, 'media_year')
            return f'{media_title} ({media_year})' if media_year else str(media_title)
        if media_title and media_type in MEDIA_TYPES_EPISODIC:
            episode_match = cls.episode_re.search(fallback or '')
            return f'{media_title} {episode_match.group(0).upper()}' if episode_match else str(media_title)
        return cls.trimmed(fallback)

    @classmethod
    def trimmed(cls, name: str | None) -> str:
        """A trailing extension of FILE_EXTENSIONS dropped, every ``[...]`` group removed, in a name without spaces
        every dot but a decimal point turned to a space, spaces collapsed, cut at 60."""
        name = name or ''
        trimmed = cls.bracket_re.sub(' ', cls.extension_re.sub('', name))
        if ' ' not in cls.bracket_re.sub('', name).strip():
            trimmed = cls.word_dot_re.sub(' ', trimmed)
        trimmed = cls.space_re.sub(' ', trimmed).strip()[:cls.max_length].rstrip()
        return trimmed or name[:cls.max_length]

    @staticmethod
    def _field(record: Any, key: str) -> Any:
        if record is None:
            return None
        if isinstance(record, Mapping):
            return record.get(key)
        return getattr(record, key, None)
