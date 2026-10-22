from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from executin.logge import Loggor, OceanorLoggor

if TYPE_CHECKING:
    from executin.announcor import HookAnnouncor


class OceanicHook:
    """
    Oceanic's hook, which the runnor, oceanor.py, hands every oce_ event, the two logging to oceanic_action.log. A
    ticked delete acts: oce_deleted and oce_delete_failed clean the payload's folder in the movin library, tell
    Jellyfin, and say so in one DELETED card; oce_removed, which every remove ends in, only logs. Only pathlib and
    the loggor are imported here: shutil, whose
    compression modules weigh most of a megabyte, yaml, the announcor, the Jellyfin communicator and the video
    suffixes are imported inside the methods that act, when they act, so a plain remove costs the interpreter and a
    log line.
    """

    # movin alone, by the operator's word of 2026-10-23: Jellyfin's other movie libraries, instream, kidstuff and
    # structured_movies, hold nothing the daemon still seeds and are cleaned by other avenues; nothing outside the
    # tuple is cleaned, and Jellyfin's deleted call takes the path alone
    movie_libraries: ClassVar[tuple[Path, ...]] = (
        Path('/ocean/video/movies/movin'),
    )
    # libtorrent's error when the torrent's folder kept what Jellyfin and the sidecars put there, the normal end
    folder_kept_error: ClassVar[str] = 'Directory not empty'

    def __init__(self, torrent_id: str, torrent_name: str, base_sdir: str, loggor: Loggor | None = None):
        super().__init__()
        self.torrent_id = torrent_id
        self.torrent_name = torrent_name
        self.base_sdir = base_sdir
        self.loggor = loggor or OceanorLoggor()
        self.stage: str = 'folder'  # set as the acting path goes, for a failed card
        # the acting path's outcome, kept at every exit of clean_payload for the card and the testor
        self.remove_outcome: str | None = None
        self.remove_leftovers: int | None = None
        self._announcor: HookAnnouncor | None = None

    @property
    def announcor(self) -> HookAnnouncor:
        if self._announcor is None:
            from executin.announcor import HookAnnouncor  # deferred: the voice is loaded on the acting path only, or when the hook dies
            self._announcor = HookAnnouncor(self.loggor)
        return self._announcor

    def process_event(self, event_name: str, *extras: str) -> bool | None:
        if event_name == 'oce_removed':
            return self.on_removed()
        elif event_name == 'oce_deleted':
            return self.on_deleted()
        elif event_name == 'oce_delete_failed':
            return self.on_delete_failed(*extras)
        self.loggor.error(f"Unknown event: '{event_name}' for torrent '{self.torrent_name}' ({self.torrent_id})")
        return None

    def on_removed(self) -> bool:
        # every remove ends here, ticked or not; what a ticked one did to the disk is the delete events' to tell
        self.loggor.info(f"Torrent '{self.torrent_name}' removed, id '{self.torrent_id}', location '{self.base_sdir}'")
        return True

    def on_deleted(self) -> bool:
        return self.clean_payload('oce_deleted')

    def on_delete_failed(self, error: str = '') -> bool:
        return self.clean_payload('oce_delete_failed', error)

    def clean_payload(self, event_name: str, error: str | None = None, *,
                      libraries: tuple[Path, ...] | None = None) -> bool:
        """
        A ticked delete's aftercare, the disk its one witness: the payload's folder found, held to the movie
        libraries, scanned once for a video, removed when none is left, Jellyfin told, one card. True when the folder
        is gone, with the delete or by the hook; False when it is kept, or refused, which is a log line and no card.
        """
        self.remove_outcome = None
        self.remove_leftovers = None
        self.stage = 'folder'
        error_text = '' if error is None else f", error '{error}'"
        self.loggor.info(f"Torrent '{self.torrent_name}' {event_name}, id '{self.torrent_id}', "
                         f"location '{self.base_sdir}'{error_text}")
        libraries = self.movie_libraries if libraries is None else libraries
        try:
            folder = self.payload_folder(libraries)
            if folder is None:
                return False
            self.stage = 'library'
            library = self.library_of(folder, libraries)
            if library is None:
                return False
            return self.clean_folder(event_name, error, folder, library)
        except Exception as exc:
            # the hook raises nothing it can report: the death is announced at its stage, and raised on for the plugin
            self.announcor.failed(self.stage, exc, self.torrent_name)
            raise

    def payload_folder(self, libraries: tuple[Path, ...] | None = None) -> Path | None:
        """
        The folder the payload lay in, read off the disk: <location>/<name>, a folder torrent's, which a rename-wrapped
        bare file is too. A directory, or, located in the library itself, a path the delete took with it. Anything else
        is refused here: a file, or a folder gone from a location that is not the library, such as another library or
        a double-wrapped torrent's outer folder, left for the operator's hand.
        """
        libraries = self.movie_libraries if libraries is None else libraries
        location = Path(self.base_sdir)
        candidate = location / self.torrent_name
        if candidate.is_dir():
            return candidate
        if candidate.exists() or candidate.is_symlink():
            return self._refuse_removal(candidate, 'it is not a folder')
        if location.resolve() not in [library.resolve() for library in libraries]:
            return self._refuse_removal(candidate, f'it is gone, and its location {{}} is not the library '
                                                   f'{self._library_names(libraries)}', location)
        return candidate

    def library_of(self, folder: Path, libraries: tuple[Path, ...] | None = None) -> Path | None:
        """
        The one library the folder lies strictly below, resolved, or None after its refusal: a path climbing with ..,
        the library itself, a download location outside the library, a symlink, not a directory, or resolving outside
        its library. A folder that is not there is no refusal: the delete may have taken it.
        """
        libraries = self.movie_libraries if libraries is None else libraries
        resolved_libraries = [library.resolve() for library in libraries]
        if '..' in folder.parts:
            return self._refuse_removal(folder, 'its path climbs with {}', '..')
        resolved_folder = folder.resolve()
        if resolved_folder in resolved_libraries:
            return self._refuse_removal(folder, 'it is the library itself')
        resolved_parent = folder.parent.resolve()
        matches = [library for library in resolved_libraries if resolved_parent.is_relative_to(library)]
        if len(matches) != 1:
            return self._refuse_removal(folder, f'its download location is outside the library '
                                                f'{self._library_names(libraries)}')
        library = matches[0]
        if folder.is_symlink():
            return self._refuse_removal(folder, 'it is a symlink')
        if not folder.exists():
            return library
        if not folder.is_dir():
            return self._refuse_removal(folder, 'it is not a directory')
        if resolved_folder == library or not resolved_folder.is_relative_to(library):
            return self._refuse_removal(folder, 'it resolves to {}, not below {}', resolved_folder, library)
        return library

    def clean_folder(self, event_name: str, error: str | None, folder: Path, library: Path) -> bool:
        from executin.extensions import video_extensions

        record = self.click_record(folder)
        self.announcor.record = record
        self.stage = 'scan'
        is_gone = False
        is_kept = False
        if not folder.exists():
            self.loggor.info(f"'{folder}' is gone with the delete, nothing to remove")
            self.remove_outcome = 'gone with the delete'
            is_gone = True
        else:
            # libtorrent posts the alert once its delete has run, so the disk is read once, for the video and the rest
            paths = list(folder.rglob('*'))
            videos = sorted(path for path in paths if path.suffix.lower() in video_extensions and path.is_file())
            if videos:
                # a video that survived a ticked delete is the anomaly: its card goes warned and high, always
                is_kept = True
                first_video = videos[0].relative_to(folder)
                self.loggor.info(f"Video still in '{folder}', {len(videos)} video, first '{first_video}', kept")
                self.remove_outcome = f'kept: video still present, {self.announcor.bold(first_video)}'
                if event_name == 'oce_delete_failed' and error != self.folder_kept_error:
                    self.announcor.note(f'the delete failed: {self.announcor.bold(error or "no error text")}')
            else:
                self.stage = 'removal'
                is_gone = self.remove_folder(folder, library, paths, video_extensions)
        jellyfin_told = None
        if is_gone:
            self.stage = 'jellyfin'
            jellyfin_told = self.tell_jellyfin(folder)
        self.stage = 'card'
        announced = self.announcor.deleted(str(folder), self.remove_outcome, jellyfin_told, self.torrent_id,
                                           record=record, is_kept=is_kept)
        if announced:
            self.loggor.info(f'Announced {announced}')
        return is_gone

    def remove_folder(self, folder: Path, library: Path, paths: list[Path], video_extensions: tuple[str, ...]) -> bool:
        import shutil

        left = sorted(str(path.relative_to(folder)) for path in paths)
        # the card counts files, a real directory is not one; a symlink is, rmtree removes it as a link
        left_file_count = sum(1 for path in paths if path.is_symlink() or not path.is_dir())
        self.loggor.info(f"Deleting '{folder}' with what is left: {left}")
        try:
            shutil.rmtree(folder)
        except OSError as e:
            self.loggor.error(f"Error deleting '{folder}': {e}")
            self.remove_outcome = f'error: {self.announcor.bold(e)}'
            self.announcor.note(f"deletion failed, {self.announcor.bold(f'{folder.name}/')} left for the operator's hand")
            return False
        self.loggor.remark(f"Deleted '{folder}'")
        self.remove_outcome = f'deleted with {left_file_count} files'
        self.remove_leftovers = left_file_count

        # a double-wrapped folder's parent is below the library too, it is left for the operator's hand
        parent = folder.parent
        if parent.resolve() != library:
            parent_videos = [path for path in parent.rglob('*') if path.suffix.lower() in video_extensions and path.is_file()]
            if not parent_videos:
                self.loggor.warning(f"Parent '{parent}' holds no video, left for the operator's hand")
                self.announcor.note(f"parent {self.announcor.bold(f'{parent.name}/')} holds no video, left for the operator's hand")
        return True

    def click_record(self, folder: Path) -> dict | None:
        # the click record in the folder's provenance names the card; read before anything is removed, fail-open
        try:
            import yaml

            provenance = yaml.safe_load((folder / 'provenance.yml').read_text())
        except Exception:
            return None
        return provenance.get('click') if isinstance(provenance, dict) else None

    def tell_jellyfin(self, folder: Path) -> bool:
        # Jellyfin is told the one path, never asked to delete an item, which deletes the files too; fail-open
        try:
            from executin.jellyfin_communicator import JellyfinCommunicator

            JellyfinCommunicator().report_media_deleted(str(folder))
        except Exception as exc:
            self.announcor.note(f'jellyfin not told: {self.announcor.exception_text(exc)}')
            return False
        return True

    def _refuse_removal(self, folder: Path, reason: str, *objects: object) -> None:
        # each {} of the reason holds an object, quoted in the log, in bold in the outcome; a refusal sends no card,
        # Oceanic speaking of nothing outside its library
        log_reason = reason.format(*(f"'{obj}'" for obj in objects))
        self.loggor.info(f"Not removing '{folder}', {log_reason}")
        self.remove_outcome = f'refused: {reason.format(*(self.announcor.bold(obj) for obj in objects))}'
        return None

    @staticmethod
    def _library_names(libraries: tuple[Path, ...]) -> str:
        # plain words in a refusal, so naming the library loads no voice
        return ', '.join(library.name for library in libraries)
