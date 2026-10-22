"""The hook's voice over ntfy: one message per completed or deleted event, one more only when the hook dies.

Written for a human reading ntfy's web app, in the click's voice at the magnetics end: the title is the agenda
word in capitals and the name a human thinks in (naming.HumanNamor, one text at both ends), the first body line
the outcome, then each diversion on its own `!` line, then the details, the hash last; the body is Markdown,
every object in it (a label, a library place, a folder, the hash, a stage, an exception with its type) set in
bold and every word plain; the first tag an emoji name, so the kind reads before the words.

Speaks through the ntfying package of the ntfy_client clone, which testors/import_helpor.py puts on
sys.path (nested at /codes/ntfy_client on media-docker, the sibling clone on the dev box). Fail-open:
a missing clone, a missing dotenv, a bad token, a dead or slow server, each is one warning in the
log, and the hook goes on as it would have without a voice; a publish waits at most three seconds.
"""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING, ClassVar

from .naming import HumanNamor

if TYPE_CHECKING:
    from delugapi.torrent import DelugapiTorrent
    from .logge import Loggor
    from .torrenthandlor import TorrentLabelHandlor

video_root_dir = PurePosixPath('/ocean/video')


class HookAnnouncor:
    """Says what the hook did; collects the diversions the flow went on past; never raises."""

    # ntfy shows a tag that is an emoji shortcode as that emoji before the title
    kind_tags: ClassVar[dict[str, str]] = {'completed': 'white_check_mark', 'deleted': 'wastebasket', 'failed': 'x'}

    def __init__(self, logger: Loggor):
        super().__init__()
        self.logger = logger
        self.stage: str = 'status'  # set by the flow as it goes, for a failed message
        self.label: str | None = None  # set by the flow once the status is read, for a failed message
        self.record: dict | None = None  # the click record once the flow has read it, to name a failed message
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
        """One message, tags [the kind's emoji, *tags], the sender added by ntfying; its id, or None."""
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
                  refreshed: bool | None = None, not_moved: str | None = None,
                  already_named: bool = False) -> str | None:
        """already_named: the torrent arrived in its pattern folder, so no rename was asked for."""
        try:
            title = f'COMPLETED: {HumanNamor.human_name(browser_source_data, delugapi_torrent.name)}'
            outcome_lines = self._completed_outcome_lines(delugapi_torrent.label, label_handler, destination,
                                                          refreshed, not_moved)
            detail_lines = self._completed_detail_lines(delugapi_torrent, label_handler, already_named)
        except Exception as exc:  # fail-open: a message that cannot be built is not sent
            return self._fail(f'completed message not built: {exc!r}')
        tags, priority = self._diverted((delugapi_torrent.label,) if delugapi_torrent.label else ())
        return self.say('completed', title, [*outcome_lines, *self._diversion_lines, *detail_lines],
                        priority=priority, tags=tags)

    def deleted(self, folder: str, outcome: str | None, jellyfin_told: bool | None, torrent_id: str, *,
                record: dict | None = None, is_kept: bool = False) -> str | None:
        """record: the click record from the folder's provenance.yml, None when there was none to read.
        jellyfin_told: True told, False the call failed, None nothing deleted so nothing to tell.
        is_kept: a video survived the ticked delete, the one anomaly, so the card is warned and high always."""
        try:
            title = f'DELETED: {HumanNamor.human_name(record, PurePosixPath(folder).name)}'
            outcome_line = outcome or 'outcome unknown'
            if jellyfin_told is not None:
                outcome_line += ', jellyfin told' if jellyfin_told else ', jellyfin not told: call failed'
            detail_lines = [f'folder {self.bold(f"{self._relative_to_video_root(folder)}/")}',
                            f'hash {self.bold(torrent_id)}']
        except Exception as exc:  # fail-open: a message that cannot be built is not sent
            return self._fail(f'deleted message not built: {exc!r}')
        tags, priority = self._diverted((), is_alarmed=is_kept)
        return self.say('deleted', title, [outcome_line, *self._diversion_lines, *detail_lines],
                        priority=priority, tags=tags)

    def failed(self, stage: str, exc: BaseException, torrent_name: str) -> str | None:
        try:
            title = f'FAILED: {HumanNamor.human_name(self.record, torrent_name)}'
            lines = [f'at {self.bold(stage)}: {self.exception_text(exc)}', *self._diversion_lines]
        except Exception as build_exc:  # fail-open: called while the hook dies, it must not replace the death
            return self._fail(f'failed message not built: {build_exc!r}')
        tags = (self.label,) if self.label else ()
        return self.say('failed', title, lines, priority='high', tags=tags)

    @staticmethod
    def bold(obj: object) -> str:
        """An object set in bold for the Markdown body; a backslash, an asterisk or a backtick inside it is escaped,
        so the span holds and the object reads as it is."""
        text = str(obj)
        for char in '\\*`':
            text = text.replace(char, '\\' + char)
        return f'**{text}**'

    @classmethod
    def exception_text(cls, exc: BaseException) -> str:
        """The exception as one object, ``Type: text`` in bold, the text cut to its first line and 200 characters."""
        text = str(exc).partition('\n')[0][:200]
        return cls.bold(f'{type(exc).__name__}: {text}' if text else type(exc).__name__)

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
            '\n'.join(lines), title=title, tags=(self.kind_tags.get(kind, kind), *tags),
            priority=PriorityEnum(priority) if priority else None, markdown=True,
        )
        if message_id is None:
            return self._fail(ntfy_announcor.failure or 'unknown')
        return message_id

    @staticmethod
    def _completed_outcome_lines(label: str | None, label_handler: TorrentLabelHandlor | None,
                                 destination: str | None, refreshed: bool | None, not_moved: str | None) -> list[str]:
        if destination:
            lines = [f'in {HookAnnouncor.bold(HookAnnouncor._relative_to_video_root(destination))}']
        elif not_moved:
            lines = [f'not moved: {not_moved}']
        elif label_handler is None:
            lines = [f'not moved: no handler for label {HookAnnouncor.bold(label)}' if label else 'not moved: no label']
        else:
            lines = ['not moved: unknown']
        lines.append('jellyfin refreshed' if refreshed and label_handler is not None else 'jellyfin not refreshed')
        return lines

    @staticmethod
    def _completed_detail_lines(delugapi_torrent: DelugapiTorrent, label_handler: TorrentLabelHandlor | None,
                                already_named: bool) -> list[str]:
        # the torrent's files as the status read them before any rename, so a single path at the root is a bare file
        paths = [file['path'] for file in delugapi_torrent.files]
        is_bare = len(paths) == 1 and '/' not in paths[0]
        # the line names its object: the pattern folder it became, or the release as it came, a folder with its slash
        bold = HookAnnouncor.bold
        if label_handler is not None and already_named:
            folder_line = f'already {bold(f"{label_handler.pattern_dir_name}/")}'
        elif label_handler is not None and label_handler.is_renamed:
            folder_line = f"{'wrapped into' if is_bare else 'renamed to'} {bold(f'{label_handler.pattern_dir_name}/')}"
        else:
            folder_line = f"as released: {bold(HumanNamor.trimmed(delugapi_torrent.name) + ('' if is_bare else '/'))}"
        return [folder_line, f'{(delugapi_torrent.total_wanted or 0) / 1e9:.1f} GB', f'hash {bold(delugapi_torrent.tid)}']

    @staticmethod
    def _relative_to_video_root(path: str) -> PurePosixPath:
        posix_path = PurePosixPath(path)
        return posix_path.relative_to(video_root_dir) if posix_path.is_relative_to(video_root_dir) else posix_path

    @property
    def _diversion_lines(self) -> list[str]:
        return [f'! {diversion}' for diversion in self._diversions]

    def _diverted(self, tags: tuple[str, ...], *, is_alarmed: bool = False) -> tuple[tuple[str, ...], str | None]:
        """Any noted diversion, or a caller's alarm, adds the tags warning and diverted and makes the priority high."""
        if not self._diversions and not is_alarmed:
            return tags, None
        return (*tags, 'warning', 'diverted'), 'high'

    def _fail(self, reason: str) -> None:
        self._failure = reason
        self.logger.warning(f'ntfy announce failed: {reason}')
        return None
