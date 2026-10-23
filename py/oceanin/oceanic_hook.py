from __future__ import annotations

from collections.abc import Callable, Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from executin.logge import Loggor, OceanorLoggor

if TYPE_CHECKING:
    from delugapi.torrent import DelugapiTorrent
    from executin.announcor import HookAnnouncor
    from executin.torrenthandlor import TorrentLabelHandlor
    from executin.torrentor import Torrentor
    from oceanin.stagor import Stagor


class OceanicHook:
    """
    Oceanic's hook, which the runnor, oceanor.py, hands every oce_ event, the two logging to oceanic_action.log, and
    the one gate: the plugin spawns for every hearing it has. A ticked delete acts: oce_deleted and oce_delete_failed
    clean the payload's folder in the movin library when it holds the torrent's record, tell Jellyfin, and say so in
    one DELETED card. The added path acts: oce_added sets the label the click's hint names and writes the survey when
    the daemon's copy of the torrent is there, oce_metadata_received writes it when it is not yet, and
    oce_metadata_failed says so in one FAILED card, all through the old Torrentor, its own lines in torrentor.log and
    the outcome here; a hybrid's v1 hash, when the daemon files it under its v2, comes with oce_added to find the
    click's record by. The completion chain acts: a
    torrent Deluge has moved into completed/ is staged on the libraries' disk, renamed there, given its sidecars,
    moved into its library and refreshed, one act per run, each run woken by the daemon's event for the act before,
    oce_storage_moved, oce_folder_renamed and oce_file_renamed, and its failures, oce_storage_moved_failed and
    oce_file_rename_failed, carded; where it stands is the torrent's stage.yml under /deluge/staging. A hybrid, which
    Deluge 2.2.0 cannot track, is carded once at its metadata, or at its raw finish, oce_torrent_finished, and left
    alone. Every other event only logs, one line with its details: oce_removed, which every remove ends in, and
    oce_finished, Deluge's own finish. Only collections.abc, pathlib, typing and the loggor are imported here: shutil,
    whose compression modules weigh most of a megabyte, yaml and fcntl, the Torrentor with twisted and the daemon's
    client, the stage, the handlors, the announcor, the naming, the Jellyfin communicator and the video suffixes are
    imported inside the methods that act, when they act, so a plain remove costs the interpreter and a log line.
    """

    # movin alone, by the operator's word of 2026-10-23: Jellyfin's other movie libraries, instream, kidstuff and
    # structured_movies, hold nothing the daemon still seeds and are cleaned by other avenues; nothing outside the
    # tuple is cleaned, and Jellyfin's deleted call takes the path alone
    movie_libraries: ClassVar[tuple[Path, ...]] = (
        Path('/ocean/video/movies/movin'),
    )
    # libtorrent's error when the torrent's folder kept what Jellyfin and the sidecars put there, the normal end
    folder_kept_error: ClassVar[str] = 'Directory not empty'
    # Deluge's move_completed folder, where the completion chain is entered; the staging folder on the libraries' own
    # disk, outside every Jellyfin library and dot-ignored besides, one folder per torrent, where the renames run, so
    # the last move into the library is a rename and the folder appears whole
    completed_dir: ClassVar[Path] = Path('/deluge/completed')
    staging_root: ClassVar[Path] = Path('/ocean/video/.staging')

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
        self._torrentor: Torrentor | None = None
        self._stagor: Stagor | None = None
        self.chain_stage: str = 'entered'  # set as the chain goes, for a failed card

    @property
    def announcor(self) -> HookAnnouncor:
        if self._announcor is None:
            from executin.announcor import HookAnnouncor  # deferred: the voice is loaded on the acting path only, or when the hook dies
            self._announcor = HookAnnouncor(self.loggor)
        return self._announcor

    @property
    def torrentor(self) -> Torrentor:
        torrentor = self._torrentor
        if torrentor is None:
            from executin.torrentor import Torrentor  # deferred: twisted and the daemon's client load on the added path only
            torrentor = Torrentor(self.torrent_id, self.torrent_name, self.base_sdir)
            self._torrentor = torrentor
        return torrentor

    def process_event(self, event_name: str, *extras: str) -> bool | None:
        if event_name == 'oce_removed':
            return self.on_removed()
        elif event_name == 'oce_deleted':
            return self.on_deleted()
        elif event_name == 'oce_delete_failed':
            return self.on_delete_failed(*extras)
        elif event_name == 'oce_added':
            return self.on_added(*extras)
        elif event_name == 'oce_finished':
            return self.on_finished(*extras)
        elif event_name == 'oce_torrent_finished':
            return self.on_torrent_finished(*extras)
        elif event_name == 'oce_folder_renamed':
            return self.on_folder_renamed(*extras)
        elif event_name == 'oce_file_renamed':
            return self.on_file_renamed(*extras)
        elif event_name == 'oce_metadata_received':
            return self.on_metadata_received(*extras)
        elif event_name == 'oce_metadata_failed':
            return self.on_metadata_failed(*extras)
        elif event_name == 'oce_storage_moved':
            return self.on_storage_moved(*extras)
        elif event_name == 'oce_storage_moved_failed':
            return self.on_storage_moved_failed(*extras)
        elif event_name == 'oce_file_rename_failed':
            return self.on_file_rename_failed(*extras)
        self.loggor.error(f"Unknown event: '{event_name}' for torrent '{self.torrent_name}' ({self.torrent_id})")
        return None

    def on_removed(self) -> bool:
        # every remove ends here, ticked or not; what a ticked one did to the disk is the delete events' to tell
        self.loggor.info(f"Torrent '{self.torrent_name}' removed, id '{self.torrent_id}', location '{self.base_sdir}'")
        return True

    # --- the added path: the label, the survey, and a magnet whose metadata never came

    def on_added(self, *details: str) -> bool:
        # the details: none, or a hybrid's v1 hash when the daemon files it under its v2, the click's record being named
        # by the v1. The label first, then the survey: a prefetched magnet, added as a file, has its copy written in
        # the same daemon call as this event, a bare magnet only once its metadata comes, under the daemon's name from
        # then on. No card: the click has its own
        self.log_hearing('oce_added', details)
        if details:
            self.torrentor.alternate_ids = (details[0],)
            self.loggor.info(f"Browser-source record of '{self.torrent_name}' looked for by '{self.torrent_id}', "
                             f"then by '{details[0]}'")
            self.keep_alternate(details[0])
        self.label_by_hint()
        torrent_file = self.torrentor.torrent_file_for(self.torrent_name)
        if torrent_file is None:
            self.loggor.info(f"No torrent file for '{self.torrent_name}' in '{self.torrentor.torrents_dir}' yet, "
                             f"the survey waits for oce_metadata_received")
            return True
        return self.write_survey(torrent_file, 'oce_added')

    def on_metadata_received(self, *details: str) -> bool:
        # the details: deluge_handled, or deluge_missed for a hybrid, whose alerts Deluge's handlers look up by the
        # other hash. The name is the daemon's, which names the copy Deluge, or the plugin's repair, has just written.
        # No daemon call and no label, the label was set on oce_added. False when the survey should have been written
        # and was not
        self.log_hearing('oce_metadata_received', details)
        is_written = self.ensure_metadata_survey()
        if details and details[0] == 'deluge_missed':
            self.unhandle('metadata_received')
        return is_written

    def ensure_metadata_survey(self) -> bool:
        survey_file = self.torrentor.survey_file
        if survey_file.exists():
            self.loggor.info(f"Survey of '{self.torrent_name}' already there, '{survey_file}', nothing written")
            return True
        torrent_file = self.torrentor.torrent_file_for(self.torrent_name)
        if torrent_file is None:
            self.loggor.warning(f"No torrent file for '{self.torrent_name}' in '{self.torrentor.torrents_dir}', "
                                f"no survey written, left for the completion")
            return False
        return self.write_survey(torrent_file, 'oce_metadata_received')

    def on_metadata_failed(self, *details: str) -> bool:
        # the details: the error's text. A magnet whose metadata never came never becomes a torrent file, so no survey
        # and no payload: a diversion, by the operator's word, one FAILED card, high
        from executin.naming import HumanNamor

        self.log_hearing('oce_metadata_failed', details)
        error = details[0] if details else ''
        announcor = self.announcor
        lines = [f'metadata failed: {announcor.bold(error or "no error text")}', f'hash {announcor.bold(self.torrent_id)}']
        announced = announcor.say('failed', f'FAILED: {HumanNamor.human_name(None, self.torrent_name)}', lines,
                                  priority='high')
        if announced:
            self.loggor.info(f'Announced {announced}')
        return True

    def label_by_hint(self) -> None:
        # the Torrentor runs the reactor itself here, so its outcome is read off it; a death is a line, and the survey
        # goes on, the two being independent
        torrentor = self.torrentor
        try:
            torrentor.label_by_hint()
        except Exception as exc:
            self.loggor.error(f"Label of '{self.torrent_name}': died: {type(exc).__name__}: {exc}")
            return
        self.loggor.info(f"Label of '{self.torrent_name}': {torrentor.label_outcome or 'no outcome kept'}")

    def write_survey(self, torrent_file: Path, event_name: str) -> bool:
        self.torrentor.survey_write(torrent_file, event_name)
        self.loggor.info(f"Survey of '{self.torrent_name}' written on {event_name}, '{self.torrentor.survey_file}' "
                         f"from '{torrent_file}'")
        return True

    # --- the completion chain, its events: each run does one act and ends, the daemon's next event waking the next

    def on_finished(self, *details: str) -> bool:
        # Deluge's own finish, emitted once its move_completed has landed; the chain is entered on that move's alert
        return self.log_hearing('oce_finished', details)

    def on_torrent_finished(self, *details: str) -> bool:
        # the details: deluge_handled, Deluge's own handler moving the torrent into completed/, which enters the chain;
        # or deluge_missed, a hybrid, which Deluge cannot track: carded once and left alone. Posted too for every
        # complete torrent at a daemon start, which its stage, or Deluge's word, makes a log line
        self.log_hearing('oce_torrent_finished', details)
        if details and details[0] == 'deluge_missed':
            self.unhandle('torrent_finished')
        return True

    def on_folder_renamed(self, *details: str) -> bool:
        # the details: the folder's old name and its new
        self.log_hearing('oce_folder_renamed', details)
        return self.run_chain('oce_folder_renamed', self.link_renamed, 'oce_folder_renamed')

    def on_file_renamed(self, *details: str) -> bool:
        # the details: the file's index and its new name
        self.log_hearing('oce_file_renamed', details)
        return self.run_chain('oce_file_renamed', self.link_renamed, 'oce_file_renamed')

    def on_storage_moved(self, *details: str) -> bool:
        # the details: the path the storage moved to: completed/ enters the chain, the torrent's staging folder and
        # its library wake the links that wait on them
        self.log_hearing('oce_storage_moved', details)
        return self.run_chain('oce_storage_moved', self.link_moved, Path(details[0]) if details else None)

    def on_storage_moved_failed(self, *details: str) -> bool:
        # the details: the error's text, and the file's path when the error had one. A chain torrent's failure is a
        # FAILED card, the chain stopped when it was moving; a torrent with no stage is not the chain's, and a hybrid
        # left unhandled is left alone, a log line each
        self.log_hearing('oce_storage_moved_failed', details)
        if self.is_off_daemon():
            return True
        error = details[0] if details else ''
        with self.stagor.held():
            stage = self.stagor.read()
            if stage.get('stage') in (None, 'unhandled'):
                return self.not_chains('oce_storage_moved_failed', stage)
            return self.fail(stage, f'storage move failed: {self.announcor.bold(error or "no error text")}')

    def on_file_rename_failed(self, *details: str) -> bool:
        # the details: the file's index and the error's text. Inside the renames, noted and the move as the files
        # stand; at any other stage of a chain torrent a FAILED card; with no stage, not the chain's, or a hybrid
        # left unhandled, a log line
        self.log_hearing('oce_file_rename_failed', details)
        if self.is_off_daemon():
            return True
        error = details[1] if len(details) > 1 else ''
        with self.stagor.held():
            stage = self.stagor.read()
            if stage.get('stage') in ('renaming', 'renaming_files'):
                return self.react_link(self.link_rename_failed, stage, error)
            if stage.get('stage') in (None, 'unhandled'):
                return self.not_chains('oce_file_rename_failed', stage)
            return self.fail(stage, f'rename failed: {self.announcor.bold(error or "no error text")}')

    def log_hearing(self, event_name: str, details: tuple[str, ...]) -> bool:
        self.loggor.info(f"Torrent '{self.torrent_name}' {event_name}, id '{self.torrent_id}', "
                         f"location '{self.base_sdir}', details {list(details)}")
        return True

    def on_deleted(self) -> bool:
        return self.clean_payload('oce_deleted')

    def on_delete_failed(self, error: str = '') -> bool:
        return self.clean_payload('oce_delete_failed', error)

    def clean_payload(self, event_name: str, error: str | None = None, *,
                      libraries: tuple[Path, ...] | None = None) -> bool:
        """
        A ticked delete's aftercare, the folder's record and the disk its witnesses: the payload's folder found, held
        to the movie libraries, asked for this torrent's record, scanned once for a video, removed when none is left,
        Jellyfin told, one card. True when the folder is gone, with the delete or by the hook; False when it is kept,
        with its card, or refused, which is a log line and no card.
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

        # the folder must hold this torrent's record before anything in it is removed; a folder gone with the delete
        # has nothing left to ask, and nothing left to remove
        torrent_record = self.torrent_record(folder)
        if torrent_record is None and folder.exists():
            return self.keep_unrecorded(folder)
        record = torrent_record.get('click') if torrent_record else None
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

    def torrent_record(self, folder: Path, alternates: tuple[str, ...] = ()) -> dict | None:
        """
        The folder's record of this torrent, which says the folder is its: .oceanmeta/<id>.yml, then an alternate's,
        then any record there whose hashes name it, a hybrid's filed under its other hash; then a legacy provenance.yml
        whose infohash is it. None when the folder holds none. Its click record names the card; read before anything
        is removed, fail-open.
        """
        ids = (self.torrent_id, *alternates)
        oceanmeta_dir = folder / '.oceanmeta'
        for torrent_id in ids:
            record = self.read_record(oceanmeta_dir / f'{torrent_id}.yml')
            if record is not None:
                return record
        for record_path in sorted(oceanmeta_dir.glob('*.yml')):
            if record_path.name.endswith('.survey.yml'):
                continue
            record = self.read_record(record_path)
            if record is not None and any(str(name).lower() in ids for name in record.get('hashes') or []):
                return record
        legacy_record = self.read_record(folder / 'provenance.yml')
        if legacy_record is not None and str(legacy_record.get('infohash', '')).lower() in ids:
            return legacy_record
        return None

    @staticmethod
    def read_record(record_path: Path) -> dict | None:
        try:
            import yaml

            record = yaml.safe_load(record_path.read_text())
        except Exception:
            return None
        return record if isinstance(record, dict) else None

    def keep_unrecorded(self, folder: Path) -> bool:
        # a folder that does not say it is this torrent's is never emptied by it: kept, and loudly, since the operator
        # ticked a delete in his library and nothing happened
        self.loggor.info(f"no record of this torrent in '{folder}', kept for the hand")
        self.remove_outcome = 'kept: no record of this torrent in the folder'
        self.stage = 'card'
        announced = self.announcor.deleted(str(folder), self.remove_outcome, None, self.torrent_id, is_kept=True)
        if announced:
            self.loggor.info(f'Announced {announced}')
        return False

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

    # --- the completion chain, its runs: the stage read, decided on, acted on and written under one lock, in one run
    # of the reactor, the hook's process having none of its own and a reactor not being restartable

    def is_off_daemon(self) -> bool:
        # off the daemon a chain run would rename and move the real torrent, and card it: left to the daemon's hook
        from executin.commons import Commons

        if Commons.singleton.is_at_daemon:
            return False
        self.loggor.warning(f"Not at daemon, the chain of '{self.torrent_name}' is left to the daemon's hook")
        return True

    def run_chain(self, event_name: str, link: Callable[..., Generator[Any, Any, bool]], *args: Any) -> bool:
        if self.is_off_daemon():
            return True
        with self.stagor.held():
            stage = self.stagor.read()
            if stage.get('stage') in ('done', 'unhandled', 'failed'):
                return self.not_chains(event_name, stage)
            return self.react_link(link, stage, *args)

    def react_link(self, link: Callable[..., Generator[Any, Any, bool]], *args: Any) -> bool:
        from twisted.internet import defer

        outcome: dict[str, Any] = {}

        @defer.inlineCallbacks
        def reactize() -> Generator[Any, Any, None]:
            try:
                outcome['result'] = yield from link(*args)
            except Exception as exc:
                outcome['error'] = exc

        self.react(reactize)
        error = outcome.get('error')
        if error is not None:
            # the chain raises nothing it can report: the death is announced at its stage, and raised on for the exit
            self.announcor.failed(self.chain_stage, error, self.torrent_name)
            raise error
        return outcome.get('result', True)

    def react(self, reactize: Callable[[], Any]) -> None:
        # the reactor run, Torrentor.label_by_hint's own; the testor runs the generator without one
        from delugapi import DelugApi

        DelugApi.delugapi_wrap(reactize)

    def transact(self, transaction: Any) -> Any:
        # one transaction with the daemon, its outcome in transaction.response; the testor answers it for the daemon
        from executin.commons import Commons

        return Commons.singleton.api_client.api.transactize(transaction)

    def read_status(self) -> Generator[Any, Any, DelugapiTorrent]:
        from delugapi.transaction import DelugApiStatusTransaction

        transaction = DelugApiStatusTransaction(torrent_id=self.torrent_id)
        yield self.transact(transaction)
        current = transaction.delugapi_torrent_from_status()
        if current is None:
            raise RuntimeError(f'no status for {self.torrent_id} from the daemon: {transaction.response.error}')
        return current

    def dispatch(self, transaction: Any, act: str) -> Generator[Any, Any, str | None]:
        # one act of the daemon's, logged; the error's text, or None
        yield self.transact(transaction)
        error = transaction.response.error
        if error:
            self.loggor.error(f"Chain of '{self.torrent_name}': {act} failed: {error}")
            return str(error)
        self.loggor.info(f"Chain of '{self.torrent_name}': dispatched {act}")
        return None

    # --- the completion chain, its links, in the chain's order; each a generator the reactor runs, each re-fire
    # with a stage it does not expect a log line

    def link_moved(self, stage: dict[str, Any], path: Path | None) -> Generator[Any, Any, bool]:
        if path == self.completed_dir:
            return (yield from self.link_entry(stage))
        if path == self.staging_dir and stage.get('stage') == 'staging':
            return (yield from self.act_rename(stage))
        if stage.get('stage') == 'moving' and path is not None and path == Path(stage.get('destination') or '/'):
            return (yield from self.act_library(stage))
        return self.not_chains('oce_storage_moved', stage)

    def link_entry(self, stage: dict[str, Any]) -> Generator[Any, Any, bool]:
        # link 1: Deluge's own move_completed has landed in completed/; a torrent left unlabelled there enters again
        # when the hand labels it and moves it into completed/ once more
        from delugapi.transaction import DelugApiMoveTransaction

        self.chain_stage = 'entered'
        if stage.get('stage') not in (None, 'unlabelled'):
            return self.not_chains('oce_storage_moved', stage)
        current = yield from self.read_status()
        if not current.label:
            return self.unlabel(stage, current, 'no label')
        notes: list[str] = []
        self.ensure_chain_survey(current, notes)
        view, handlor = self.handlor_view({**stage, 'label': current.label, 'release_name': current.name}, current)
        if handlor is None:
            return self.unlabel(stage, current, f'no handler for label {self.announcor.bold(current.label)}')
        stage = self.stagor.write(stage='staging', entry='storage_moved', deluge='handled', label=current.label,
                                  destination=str(handlor.destin_dir),
                                  pattern_dir_name=getattr(handlor, 'pattern_dir_name', None),
                                  release_name=current.name, notes=notes)
        if Path(current.download_location) == self.staging_dir:
            return (yield from self.act_rename(stage, current))
        error = yield from self.dispatch(DelugApiMoveTransaction(self.torrent_id, str(self.staging_dir)),
                                         f"the staging move to '{self.staging_dir}'")
        if error:
            return self.fail(stage, f'staging move failed: {self.announcor.bold(error)}')
        return True

    def act_rename(self, stage: dict[str, Any], current: DelugapiTorrent | None = None) -> Generator[Any, Any, bool]:
        # link 2: in staging, on the libraries' disk, the rename the handlor plans, or straight to the move
        from delugapi.transaction import DelugApiRenameFilesTransaction, DelugApiRenameFolderTransaction

        self.chain_stage = 'staging'
        if current is None:
            current = yield from self.read_status()
        view, handlor = self.held_handlor_view(stage, current)
        rename_plan = handlor.rename_plan
        if rename_plan is None and handlor.is_in_pattern_dir:
            # arrived in its pattern folder: no rename, the file renames inside it all the same, as on_completed had
            return (yield from self.act_files(stage, current, 'already'))
        if rename_plan is None:
            # the TV handlors' case, no rename planned
            return (yield from self.act_move(stage, current, 'as_released'))
        stage = self.stagor.write(stage='renaming', rename_plan=rename_plan)
        # a folder plan is a (folder, new_folder) tuple, a files plan a list of (index, new_path), as on_completed had
        if isinstance(rename_plan, tuple):
            transaction = DelugApiRenameFolderTransaction(self.torrent_id, *rename_plan)
        else:
            transaction = DelugApiRenameFilesTransaction(self.torrent_id, rename_plan)
        error = yield from self.dispatch(transaction, f'the rename by plan {rename_plan}')
        if error:
            stage = self.note(stage, 'folder rename failed, moved as not renamed')
            return (yield from self.act_move(stage, current, 'as_released'))
        return True

    def link_renamed(self, stage: dict[str, Any], event_name: str) -> Generator[Any, Any, bool]:
        # link 3: a folder renamed in one event; a bare file wrapped, or the file renames, one event per file, the runs
        # side by side taking the lock in turn, each counting what the daemon reports done
        self.chain_stage = 'renaming'
        rename_plan = stage.get('rename_plan')
        at = stage.get('stage')
        if event_name == 'oce_folder_renamed' and at == 'renaming' and isinstance(rename_plan, tuple):
            current = yield from self.read_status()
            new_folder = rename_plan[1]
            if not all(file['path'].startswith(new_folder) for file in current.files):
                stage = self.note(stage, 'folder rename not reported, moved as not renamed')
                return (yield from self.act_move(stage, current, 'as_released'))
            return (yield from self.act_files(stage, current))
        if event_name == 'oce_file_renamed' and at == 'renaming' and isinstance(rename_plan, list):
            current = yield from self.read_status()
            if not self.is_plan_done(rename_plan, current, 'renames'):
                return True
            return (yield from self.act_files(stage, current))
        if event_name == 'oce_file_renamed' and at == 'renaming_files':
            current = yield from self.read_status()
            if not self.is_plan_done(stage.get('file_plan') or [], current, 'file renames'):
                return True
            return (yield from self.act_move(stage, current, stage.get('naming') or 'renamed'))
        return self.not_chains(event_name, stage)

    def act_files(self, stage: dict[str, Any], current: DelugapiTorrent,
                  naming: str = 'renamed') -> Generator[Any, Any, bool]:
        # the file renames inside the pattern folder, renamed or arrived so, or straight to the move when none is
        # planned; the naming kept in the stage for the move and the card
        from delugapi.transaction import DelugApiRenameFilesTransaction

        view, handlor = self.held_handlor_view(stage, current, naming)
        file_plan = handlor.file_rename_plan(handlor.latest_files)
        if not file_plan:
            return (yield from self.act_move(stage, current, naming))
        stage = self.stagor.write(stage='renaming_files', file_plan=file_plan, naming=naming)
        error = yield from self.dispatch(DelugApiRenameFilesTransaction(self.torrent_id, file_plan),
                                         f'the file renames by plan {file_plan}')
        if error:
            stage = self.note(stage, 'file renames failed, moved as named')
            return (yield from self.act_move(stage, current, naming))
        return True

    def link_rename_failed(self, stage: dict[str, Any], error: str) -> Generator[Any, Any, bool]:
        # a rename libtorrent refused: noted, and the move as the files stand
        self.chain_stage = 'renaming'
        at = stage.get('stage')
        if at not in ('renaming', 'renaming_files'):
            return self.not_chains('oce_file_rename_failed', stage)
        stage = self.note(stage, f'rename failed: {self.announcor.bold(error or "no error text")}')
        current = yield from self.read_status()
        naming = 'as_released' if at == 'renaming' else stage.get('naming') or 'renamed'
        return (yield from self.act_move(stage, current, naming))

    def act_move(self, stage: dict[str, Any], current: DelugapiTorrent, naming: str) -> Generator[Any, Any, bool]:
        # link 4: the sidecars into the destination before the media, then the move into the library, a rename on
        # the libraries' own disk; the destination the handlor gives now, the renames done or not
        from delugapi.transaction import DelugApiMoveTransaction

        self.chain_stage = 'moving'
        view, handlor = self.held_handlor_view(stage, current, naming)
        destination = handlor.destin_dir
        pattern_dir = handlor.pattern_dir
        if pattern_dir is not None and pattern_dir.exists():
            stage = self.note(stage, f'pattern folder {self.announcor.bold(f"{pattern_dir.name}/")} already existed, '
                                     f'its files not replaced')
        # the record names the torrent by every hash it is known by and says how the chain met it; the survey rides
        # beside it as it came
        handlor.record_alternates = tuple(stage.get('alternate_ids') or ())
        handlor.record_entry = stage.get('entry')
        survey_file = self.torrentor.survey_file
        handlor.survey_text = survey_file.read_text() if survey_file.exists() else None
        sidecar_dir = handlor.sidecar_dir
        if sidecar_dir is not None and not handlor.write_sidecars(sidecar_dir):
            stage = self.note(stage, 'no sidecar written')
        destination.mkdir(parents=True, exist_ok=True)
        stage = self.stagor.write(stage='moving', destination=str(destination), naming=naming)
        if Path(current.download_location) == destination:
            stage = self.note(stage, 'already at the destination')
            return (yield from self.act_library(stage, current))
        error = yield from self.dispatch(DelugApiMoveTransaction(self.torrent_id, str(destination)),
                                         f"the move to '{destination}'")
        if error:
            return self.fail(stage, f'move failed: {self.announcor.bold(error)}')
        return True

    def act_library(self, stage: dict[str, Any], current: DelugapiTorrent | None = None) -> Generator[Any, Any, bool]:
        # link 5: in the library, the Jellyfin refresh last, the empty staging folder removed, the card
        self.chain_stage = 'refresh'
        if current is None:
            current = yield from self.read_status()
        view, handlor = self.held_handlor_view(stage, current, stage.get('naming'))
        destination = stage['destination']
        refreshed = None
        if handlor.is_jellyable:
            try:
                self.torrentor.jellyfin_refresh(handlor, destination)
                refreshed = True
            except Exception as exc:
                stage = self.note(stage, f'jellyfin refresh failed: {self.announcor.exception_text(exc)}')
        self.remove_staging_dir()
        stage = self.stagor.write(stage='done')
        self.chain_stage = 'card'
        for note in stage.get('notes') or []:
            self.announcor.note(note)
        announced = self.announcor.completed(view, handlor, browser_source_data=self.media_facts(),
                                             destination=destination, refreshed=refreshed,
                                             already_named=stage.get('naming') == 'already', staged=True)
        if announced:
            self.loggor.info(f'Announced {announced}')
        return True

    # --- the completion chain, its helpers

    @property
    def stagor(self) -> Stagor:
        stagor = self._stagor
        if stagor is None:
            from oceanin.stagor import Stagor  # deferred: yaml and fcntl load with the chain

            stagor = Stagor(self.torrent_id)
            self._stagor = stagor
        return stagor

    @property
    def staging_dir(self) -> Path:
        return self.staging_root / self.torrent_id

    def media_facts(self, stage: dict[str, Any] | None = None) -> dict:
        # the torrent's media facts, today the click's browser-source record alone, by its id or the alternate the
        # stage kept from oce_added: the one place a later, earlier lookup, at survey time on the server side, writes
        # the same keys for a torrent the browser gave none
        torrentor = self.torrentor
        if stage and stage.get('alternate_ids'):
            torrentor.alternate_ids = tuple(stage['alternate_ids'])
        return torrentor.browser_source_file_read_data()

    def keep_alternate(self, alternate_id: str) -> None:
        # the alternate kept for the chain at completion, which no event brings again; on the daemon only, a record
        from executin.commons import Commons

        if not Commons.singleton.is_at_daemon:
            return
        with self.stagor.held():
            self.stagor.write(alternate_ids=[alternate_id])

    def handlor_view(self, stage: dict[str, Any], current: DelugapiTorrent,
                     naming: str | None = None) -> tuple[DelugapiTorrent, TorrentLabelHandlor | None]:
        # the handlor rebuilt per link, cheap and stateless, over the torrent as it was at the entry, its release name
        # and its original files, so every name it derives stays put through Deluge's renames; the daemon's files now
        # are its current ones, and its naming the stage's
        import copy

        from executin.torrenthandlor import TorrentLabelHandlor

        view = copy.copy(current)
        view.name = stage.get('release_name') or current.name
        view.files = current.orig_files or current.files
        handlor = TorrentLabelHandlor.factory(stage.get('label') or current.label, delugapi_torrent=view,
                                              survey_data=self.torrentor.survey_file_read_data(),
                                              browser_source_data=self.media_facts(stage))
        if handlor is None:
            return view, None
        handlor.current_files = current.files
        pattern_dir_name = stage.get('pattern_dir_name')
        if pattern_dir_name and hasattr(type(handlor), 'pattern_dir_name'):
            handlor.pattern_dir_name = pattern_dir_name
        handlor.is_renamed = naming in ('renamed', 'already')
        return view, handlor

    def held_handlor_view(self, stage: dict[str, Any], current: DelugapiTorrent,
                          naming: str | None = None) -> tuple[DelugapiTorrent, TorrentLabelHandlor]:
        view, handlor = self.handlor_view(stage, current, naming)
        if handlor is None:
            raise RuntimeError(f"no handler for label '{stage.get('label')}' inside the chain")
        return view, handlor

    def ensure_chain_survey(self, current: DelugapiTorrent, notes: list[str]) -> None:
        # the survey, written on the added path in both add shapes, written here if a miss left none, or noted
        torrentor = self.torrentor
        if torrentor.survey_file.exists():
            return
        torrent_file = torrentor.torrent_file_for(current.name, self.torrent_name)
        if torrent_file is None:
            self.loggor.warning(f"No torrent file for '{current.name}' in '{torrentor.torrents_dir}', no survey")
            notes.append('survey missing, no torrent file to write it from')
            return
        self.write_survey(torrent_file, 'oce_storage_moved')

    def is_plan_done(self, plan: list[tuple[int, str]], current: DelugapiTorrent, what: str) -> bool:
        paths = {file['index']: file['path'] for file in current.files}
        done = sum(paths.get(index) == path for index, path in plan)
        if done < len(plan):
            self.loggor.info(f"Chain of '{self.torrent_name}': {what} {done}/{len(plan)} done, "
                             f"the next event looks again")
            return False
        self.loggor.info(f"Chain of '{self.torrent_name}': {what} {done}/{len(plan)} done")
        return True

    def note(self, stage: dict[str, Any], diversion: str) -> dict[str, Any]:
        # a diversion kept in the stage for the card at the chain's end, in the announcor's words
        self.loggor.warning(f'Diversion noted for the card: {diversion}')
        return self.stagor.write(notes=[*(stage.get('notes') or []), diversion])

    def not_chains(self, what: str, stage: dict[str, Any]) -> bool:
        self.loggor.info(f"Chain of '{self.torrent_name}': {what} at stage '{stage.get('stage', 'none')}', "
                         f"nothing to do")
        return True

    def remove_staging_dir(self) -> None:
        # the torrent's staging folder, empty once libtorrent has moved the payload into the library
        try:
            self.staging_dir.rmdir()
        except FileNotFoundError:
            return
        except OSError as exc:
            self.loggor.warning(f"Staging folder '{self.staging_dir}' not removed: {exc}")
            return
        self.loggor.info(f"Staging folder '{self.staging_dir}' removed")

    def unlabel(self, stage: dict[str, Any], current: DelugapiTorrent, reason: str) -> bool:
        # no label, or one no handlor knows: stage unlabelled, so the hand's trigger, a label and a move into
        # completed/, enters it again; one card only for a click that came through the chain, its browser-source
        # record the mark, by its id or the alternate; any other torrent is not the chain's business, a log line
        self.stagor.write(stage='unlabelled', entry='storage_moved', deluge='handled', label=current.label or None,
                          release_name=current.name)
        record = self.media_facts(stage)
        if not record:
            self.loggor.info(f"Chain of '{self.torrent_name}': {reason}, in '{current.download_location}', no "
                             f"browser-source record, not the chain's, no card")
            return True
        view = self.handlor_view({**stage, 'release_name': current.name}, current)[0]
        announced = self.announcor.completed(view, None, browser_source_data=record,
                                             not_moved=f'{reason}, in {self.announcor.bold(current.download_location)}')
        if announced:
            self.loggor.info(f'Announced {announced}')
        return True

    def fail(self, stage: dict[str, Any], text: str) -> bool:
        # a failure the daemon reported for a chain torrent: one FAILED card in announcor.failed's shape, the hash
        # last; stage failed when the chain was under way, any other stage kept as it stood
        from executin.naming import HumanNamor

        at = stage.get('stage', self.chain_stage)
        if at in ('entered', 'staging', 'renaming', 'renaming_files', 'moving'):
            self.stagor.write(stage='failed')
        announcor = self.announcor
        lines = [f'at {announcor.bold(at)}: {text}', *(f'! {note}' for note in stage.get('notes') or []),
                 f'hash {announcor.bold(self.torrent_id)}']
        label = stage.get('label')
        name = HumanNamor.human_name(self.media_facts(stage), self.torrent_name)
        announced = announcor.say('failed', f'FAILED: {name}', lines, priority='high', tags=(label,) if label else ())
        if announced:
            self.loggor.info(f'Announced {announced}')
        return False

    def unhandle(self, entry: str) -> None:
        # a hybrid, which Deluge 2.2.0 cannot track, its handlers looking it up by the other hash: one high card, the
        # first at its metadata, a hybrid older than that at its finish, then stage unhandled, every later event a
        # log line; nothing is acted on until Deluge is patched
        from executin.naming import HumanNamor

        if self.is_off_daemon():
            return
        with self.stagor.held():
            stage = self.stagor.read()
            if stage.get('stage'):
                self.not_chains(f'oce_{entry}', stage)
                return
            announcor = self.announcor
            name = HumanNamor.human_name(self.media_facts(stage), self.torrent_name)
            hash_line = f'hash {announcor.bold(self.torrent_id)}'
            if entry == 'metadata_received':
                announced = announcor.say('failed', f'UNHANDLED: {name}',
                                          ['hybrid torrent, Deluge cannot track it',
                                           f'left in {announcor.bold(Path(self.base_sdir).name)}',
                                           'remove it, or wait for the Deluge patch', hash_line], priority='high')
            else:
                announced = announcor.say('completed', f'COMPLETED: {name}',
                                          [f'not handled: hybrid torrent, left in {announcor.bold(self.base_sdir)} '
                                           f'until Deluge is patched', hash_line],
                                          priority='high', tags=('warning', 'diverted'))
            self.stagor.write(stage='unhandled', entry=entry, deluge='missed', release_name=self.torrent_name)
            if announced:
                self.loggor.info(f'Announced {announced}')
