"""The hook's voice over ntfy: one message per completed or removed event, one more only when the hook dies.

Speaks through the ntfying package of the ntfy_client clone, which testors/import_helpor.py puts on
sys.path (nested at /codes/ntfy_client on media-docker, the sibling clone on the dev box). Fail-open:
a missing clone, a missing dotenv, a bad token, a dead or slow server, each is one warning in the
log, and the hook goes on as it would have without a voice; a publish waits at most three seconds.
"""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from delugapi.torrent import DelugapiTorrent
    from .logge import Loggor
    from .torrenthandlor import TorrentLabelHandlor

video_root_dir = PurePosixPath('/ocean/video')


class HookAnnouncor:
    """Says what the hook did; collects the diversions the flow went on past; never raises."""

    def __init__(self, logger: Loggor):
        super().__init__()
        self.logger = logger
        self.stage: str = 'status'  # set by the flow as it goes, for a failed message
        self.label: str | None = None  # set by the flow once the status is read, for a failed message
        self._diversions: list[str] = []
        self._failure: str | None = None

    @property
    def diversions(self) -> list[str]:
        return list(self._diversions)

    @property
    def failure(self) -> str | None:
        """The last message's short failure reason; None after one that was sent."""
        return self._failure

    def say(self, kind: str, title: str, lines: list[str], *, priority: str | None = None,
            tags: tuple[str, ...] = ()) -> str | None:
        """One message, tags [kind, *tags], the sender added by ntfying; its id, or None."""
        self._failure = None
        try:
            return self._say(kind, title, lines, priority, tags)
        except Exception as exc:  # fail-open: the voice must never break the hook
            return self._fail(f'unexpected {exc!r}')

    def note(self, diversion: str) -> None:
        """A diversion for the message to come: something the flow did not expect and went on past."""
        self._diversions.append(diversion)
        self.logger.warning(f'Diversion noted: {diversion}')

    def completed(self, delugapi_torrent: DelugapiTorrent, label_handler: TorrentLabelHandlor | None = None, *,
                  browser_source_data: dict | None = None, destination: str | None = None,
                  refreshed: bool | None = None, not_moved: str | None = None) -> str | None:
        try:
            title = self._completed_title(delugapi_torrent, browser_source_data)
            lines = self._completed_lines(delugapi_torrent, label_handler, destination, refreshed, not_moved)
        except Exception as exc:  # fail-open: a message that cannot be built is not sent
            return self._fail(f'completed message not built: {exc!r}')
        tags = (delugapi_torrent.label,) if delugapi_torrent.label else ()
        lines, tags, priority = self._with_diversions(lines, tags)
        return self.say('completed', title, lines, priority=priority, tags=tags)

    def removed(self, torrent_name: str, folder: str, outcome: str | None, jellyfin_told: bool | None) -> str | None:
        """jellyfin_told: True told, False the call failed, None nothing deleted so nothing to tell."""
        try:
            lines = [f'folder {self._relative_to_video_root(folder)}', f'outcome {outcome or "unknown"}']
        except Exception as exc:  # fail-open: a message that cannot be built is not sent
            return self._fail(f'removed message not built: {exc!r}')
        if jellyfin_told is None:
            lines.append('jellyfin not told: nothing deleted')
        else:
            lines.append('jellyfin told' if jellyfin_told else 'jellyfin not told: call failed')
        lines, tags, priority = self._with_diversions(lines, ())
        return self.say('removed', f'removed: {torrent_name}', lines, priority=priority, tags=tags)

    def failed(self, stage: str, exc: BaseException, torrent_name: str) -> str | None:
        lines = [f'at {stage}', f'{type(exc).__name__}: {exc}']
        lines += [f'! {diversion}' for diversion in self._diversions]
        tags = (self.label,) if self.label else ()
        return self.say('failed', f'failed: {torrent_name}', lines, priority='high', tags=tags)

    # ---

    def _say(self, kind: str, title: str, lines: list[str], priority: str | None,
             tags: tuple[str, ...]) -> str | None:
        try:
            from ntfying.libs.client import PriorityEnum  # deferred: an absent clone is one warning, never a failed hook
            from ntfying.libs.emitting import NtfyAnnouncor
        except ImportError as exc:
            self._failure = 'ntfying not on the path'
            self.logger.warning(f'ntfy refused, no publish: ntfying not on the path: {exc!r}')
            return None
        ntfy_announcor = NtfyAnnouncor()
        message_id = ntfy_announcor.announce(
            '\n'.join(lines), title=title, tags=(kind, *tags),
            priority=PriorityEnum(priority) if priority else None,
        )
        if message_id is None:
            return self._fail(ntfy_announcor.failure or 'unknown')
        return message_id

    @staticmethod
    def _completed_title(delugapi_torrent: DelugapiTorrent, browser_source_data: dict | None) -> str:
        # the record names a movie only, as it names the movie folder; a series title would hide the episode
        record = browser_source_data or {}
        media_title = record.get('media_title') if record.get('media_type') == 'movie' else None
        if not media_title:
            return f'done: {delugapi_torrent.name}'
        media_year = record.get('media_year')
        if media_year is None:
            return f'done: {media_title}'
        return f'done: {media_title} ({media_year})'

    @staticmethod
    def _completed_lines(delugapi_torrent: DelugapiTorrent, label_handler: TorrentLabelHandlor | None,
                         destination: str | None, refreshed: bool | None, not_moved: str | None) -> list[str]:
        label = delugapi_torrent.label
        lines = [f'label {label}' if label else 'label none']
        paths = [file['path'] for file in delugapi_torrent.files]
        if label_handler is not None and label_handler.is_renamed:
            lines.append(f'folder {label_handler.pattern_dir_name}/')
        elif len(paths) == 1 and '/' not in paths[0]:
            lines.append('bare file')
        else:
            lines.append(f'folder {delugapi_torrent.name}/')
        if destination:
            lines.append(f'moved {HookAnnouncor._relative_to_video_root(destination)}')
        elif not_moved:
            lines.append(f'not moved: {not_moved}')
        elif label_handler is None:
            lines.append(f'not moved: no handler for label {label}' if label else 'not moved: no label')
        else:
            lines.append('not moved: unknown')
        if refreshed and label_handler is not None:
            lines.append(f'jellyfin {label_handler.jelly_library_name}')
        else:
            lines.append('jellyfin none')
        lines.append(f'size {(delugapi_torrent.total_wanted or 0) / 1e9:.1f} GB')
        return lines

    @staticmethod
    def _relative_to_video_root(path: str) -> PurePosixPath:
        posix_path = PurePosixPath(path)
        return posix_path.relative_to(video_root_dir) if posix_path.is_relative_to(video_root_dir) else posix_path

    def _with_diversions(self, lines: list[str], tags: tuple[str, ...]) -> tuple[list[str], tuple[str, ...], str | None]:
        """One `!` line per noted diversion; any of them adds the tag diverted and makes the priority high."""
        lines = lines + [f'! {diversion}' for diversion in self._diversions]
        if not self._diversions:
            return lines, tags, None
        return lines, (*tags, 'diverted'), 'high'

    def _fail(self, reason: str) -> None:
        self._failure = reason
        self.logger.warning(f'ntfy announce failed: {reason}')
        return None
