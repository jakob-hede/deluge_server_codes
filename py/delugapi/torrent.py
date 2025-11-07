from __future__ import annotations
import re


class DelugapiTorrent:
    def __init__(self,
                 tid: str,
                 name: str = '',
                 files: list[dict] = None,
                 orig_files: list[dict] = None,
                 download_location: str = '',
                 save_path: str = '',
                 move_completed_path: str = '',
                 label: str = '',
                 ):
        self.tid = tid
        self.name = name
        self.files = files or []
        self.orig_files = orig_files or []
        self.download_location = download_location
        self.save_path = save_path
        self.move_completed_path = move_completed_path
        self.label = label

    def __str__(self) -> str:
        txt = f'<DelugapiTorrent: id={self.tid}, title="{self.title}">'
        return txt

    @classmethod
    def from_dict(cls, status_dict: dict) -> DelugapiTorrent:
        tid: str
        data: dict
        tid, data = next(iter(status_dict.items()))
        name: str = data.get('name', '')
        t_hash: str = data.get('hash', '')
        if tid != t_hash:
            raise ValueError(f"tid '{tid}' does not match hash '{t_hash}'")
        files: list[dict] = data.get('files', [])
        orig_files: list[dict] = data.get('orig_files', [])
        download_location: str = data.get('download_location', '')
        save_path: str = data.get('save_path', '')
        move_completed_path: str = data.get('move_completed_path', '')
        label: str = data.get('label', '')
        instance = cls(
            tid=tid,
            name=name,
            files=files,
            orig_files=orig_files,
            download_location=download_location,
            save_path=save_path,
            move_completed_path=move_completed_path,
            label=label,
        )
        return instance

    @property
    def title(self) -> str:
        # Derive a title from the torrent name, e.g., remove file extensions or extra info
        title = self.name
        # keep until occurrence of [,(
        for sep in ['[', '(', '{']:
            if sep in title:
                title = title.split(sep, 1)[0]
        if not title:
            # Reverse the name
            title = self.name

        # keep until occurrence of '.19xx' or '.20xx' or  ' 19xx ' or ' 20xx
        # (e.g., year)'
        match = re.search(r'[\s.](19|20)\d{2}[\s.]', title)

        # # keep until occurrence of .19xx or .20xx
        # match = re.search(r'\.(19|20)\d{2}', title)
        if match:
            title = title[:match.start()]
        if not title:
            # Reverse the title
            title = title

        # keep until occurrence of .SxxExx. or .Sxx.EE. or .SxxExx- or .Sxx.EE-
        match = re.search(r'[sS]\d{2}[eE.-]\d{2}', title, re.IGNORECASE)
        if match:
            title = title[:match.start()]
        if not title:
            # Reverse title
            title = title
        # replace whitespace with one dot
        # split by whitespace and join by dot
        title = '.'.join(title.split())
        # title = re.sub(r'[\s_]+', ' ', title).strip() ???
        # collapse multiple dots to one
        title = re.sub(r'\.+', '.', title)
        # remove surrounding dots
        title = title.strip('.').strip()
        if not title:
            # Give up, use the original name lower
            title = self.name.lower()
        # Remove common file extensions
        for ext in ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mpg', '.mpeg', '.ts']:
            if title.lower().endswith(ext):
                title = title[: -len(ext)]
        return title

    @property
    def is_title_conform(self) -> bool:
        title = self.title
        if not title:
            return False
        # Check if title contains only alphanumeric characters, dots, hyphens, underscores
        pattern = r'^[a-zA-Z0-9._-]+$'
        return bool(re.match(pattern, title))

    @property
    def season_episode_code(self) -> str:
        # Derive a season_episode_code from the torrent name, e.g., s01e01
        match = re.search(r'[sS]\d{2}[eE]\d{2}', self.name, re.IGNORECASE)
        if match:
            seasonpisode = match.group(0).lower()  # Convert to lowercase
            return seasonpisode
        return ''

    @property
    def is_season_episode_code_conform(self) -> bool:
        seasonpisode = self.season_episode_code
        if not seasonpisode:
            return False
        # Check if seasonpisode matches the pattern s##e##
        pattern = r'^[s]\d{2}e\d{2}$'
        return bool(re.match(pattern, seasonpisode))

    @property
    def season_code(self) -> str:
        if self.is_season_episode_code_conform:
            return self.season_episode_code[:3]
        return ''

    @property
    def is_season_code_conform(self) -> bool:
        # Check if season_code matches the pattern s##
        pattern = r'^[s]\d{2}$'
        return bool(re.match(pattern, self.season_code))
