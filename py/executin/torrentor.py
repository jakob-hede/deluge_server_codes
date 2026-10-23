from pathlib import Path

import yaml
from twisted.internet.defer import Deferred

from .announcor import HookAnnouncor
from .commons import Commons
from .jellyfin_communicator import JellyfinCommunicator
from .logge import DelugapiTorrentorLoggor
from .torrenthandlor import TorrentLabelHandlor
from .torrentparsor import TorrentParsor

from delugapi.response import DelugApiResponse
from delugapi import DelugApi

from typing import Generator, Any
from twisted.internet import defer

from delugapi import DelugapiClient
from delugapi.transaction import DelugApiStatusTransaction, DelugApiLabelTransaction

type deferred_response = Generator[Any, Any, dict | None]


class Torrentor:
    """
    The one place the Oceanic hook reads the daemon's copy of a torrent, the survey and the click's browser-source
    record, writes the survey, sets the label the record hints through the daemon, and asks Jellyfin for a refresh;
    every daemon call goes through DelugApi.delugapi_wrap. Execute's hook, which drove the old added and completed
    paths through it, is retired, and the hook in py/oceanin/ calls these methods where it acts.
    """

    torrents_dir: Path = Commons.singleton.deluge_root_dir / 'torrents'
    surveys_dir: Path = Commons.singleton.deluge_root_dir / 'surveys'
    browser_source_dir: Path = Commons.singleton.deluge_root_dir / 'browser-source'

    def __init__(self, torrent_id, torrent_name, base_sdir):
        self.torrent_id: str = torrent_id
        self.torrent_name: str = torrent_name
        self.base_sdir: str = base_sdir
        self.logger = DelugapiTorrentorLoggor()
        self.reaction_response: DelugApiResponse = None
        self.label_outcome: str | None = None  # what label_by_hint did, for a caller that never sees its Deferred
        # the torrent's other hashes, a hybrid's v1 when the daemon files it under its v2, to find the click's record by
        self.alternate_ids: tuple[str, ...] = ()
        self.announcor = HookAnnouncor(self.logger)  # the one voice of whichever hook this process runs

    @property
    def survey_file(self) -> Path:
        return self.surveys_dir / f'{self.torrent_id}.yml'

    def survey_file_write_data(self, data: dict):
        survey_yaml = yaml.dump(data, sort_keys=False)
        if not self.surveys_dir.exists():
            self.surveys_dir.mkdir(parents=True, exist_ok=True)
        self.survey_file.write_text(survey_yaml)

    def survey_file_read_data(self) -> dict:
        if not self.survey_file.exists():
            print(f"Error: Survey file '{self.survey_file}' not found")
            return {}
        survey_yaml = self.survey_file.read_text()
        data: dict = yaml.safe_load(survey_yaml)
        return data

    def torrent_file_for(self, *names: str) -> Path | None:
        # the daemon names its copy of the torrent by the torrent's name when the metadata arrives,
        # which for a magnet is often not the name the added event carried
        looked_for: list[str] = []
        for name in names:
            if not name or name in looked_for:
                continue
            looked_for.append(name)
            torrent_file = self.torrents_dir / f'{name}.torrent'
            if torrent_file.exists():
                return torrent_file
        return None

    def survey_write(self, torrent_file: Path, event_name: str) -> dict:
        survey_data: dict = {}
        execute_args_data: dict = {
            'torrent_id': self.torrent_id,
            'torrent_name': self.torrent_name,
            'added_base_dir': self.base_sdir,
            'timestamp': Commons.singleton.timestamp(),
            'event': event_name,
            'torrent_file': str(torrent_file),
        }
        survey_data['execute_args'] = execute_args_data
        parsor = TorrentParsor(torrent_file)
        torrent_data = parsor.parse()
        survey_data['torrent_data'] = torrent_data
        self.survey_file_write_data(survey_data)
        return survey_data

    @property
    def browser_source_file(self) -> Path:
        # the click's record is named by the magnet's hash: the torrent id's first, then each alternate's
        candidates = [self.browser_source_dir / f'{torrent_id}.yml'
                      for torrent_id in (self.torrent_id, *self.alternate_ids)]
        return next((candidate for candidate in candidates if candidate.exists()), candidates[0])

    def browser_source_file_read_data(self) -> dict:
        if not self.browser_source_file.exists():
            print(f"Error: Browser-source file '{self.browser_source_file}' not found")
            return {}
        browser_source_yaml = self.browser_source_file.read_text()
        data: dict = yaml.safe_load(browser_source_yaml)
        return data

    def label_by_hint(self) -> Deferred | None:
        """Set the label the click's browser-source hint names, unless a hand-set label is there, and read it back.
        The Deferred when a reactor runs, as under the Twistor; None when this method ran the reactor itself, so the
        outcome is kept in label_outcome too."""
        api_client: DelugapiClient = Commons.singleton.api_client

        @defer.inlineCallbacks
        def reactize() -> deferred_response:
            print('reactize')
            transaction = None
            reply = {}
            browser_source_data = self.browser_source_file_read_data()
            label_hint = browser_source_data.get('label_hint') if browser_source_data else None
            if not browser_source_data:
                self.logger.info(f"No browser-source file '{self.browser_source_file}', skipping label")
                self.label_outcome = 'skipped, no browser-source file'
            elif label_hint not in ('movin', 'tv-in', 'tv-arc'):
                self.logger.info(f"Browser-source label_hint '{label_hint}' is not a label, skipping label")
                self.label_outcome = f"skipped, the hint '{label_hint}' is not a label"
            else:
                self.logger.info(f"Browser-source label_hint '{label_hint}' from '{self.browser_source_file}'")
                transaction = DelugApiStatusTransaction(torrent_id=self.torrent_id)
                reply = yield api_client.api.transactize(transaction)
                delugapi_torrent = transaction.delugapi_torrent_from_status()
                print(f' - delugapi_torrent: {delugapi_torrent}')
                self.logger.remark(transaction.pressence)

                if delugapi_torrent is None:
                    self.logger.warning(f"No status for torrent '{self.torrent_id}', skipping label")
                    self.label_outcome = f"skipped '{label_hint}', no status from the daemon"
                elif delugapi_torrent.label:
                    self.logger.info(
                        f'Label "{delugapi_torrent.label}" already set, hand-set label wins, skipping "{label_hint}"')
                    self.label_outcome = f"kept the hand-set '{delugapi_torrent.label}', skipped '{label_hint}'"
                else:
                    self.logger.info(f'Setting label "{label_hint}" for "{delugapi_torrent.title}"')
                    transaction = DelugApiLabelTransaction(torrent_id=self.torrent_id, label=label_hint)
                    reply = yield api_client.api.transactize(transaction)
                    transaction_response = transaction.response
                    print(f"transaction_response: {transaction_response}")
                    if transaction_response.error:
                        self.logger.error(f"Error setting label: {transaction_response.error}")
                    else:
                        self.logger.remark(f"Dispatched label '{label_hint}' for {delugapi_torrent.name}")

                    transaction = DelugApiStatusTransaction(torrent_id=self.torrent_id)
                    reply = yield api_client.api.transactize(transaction)
                    updated_torrent = transaction.delugapi_torrent_from_status()
                    current_label = updated_torrent.label if updated_torrent else None
                    self.logger.info(f"Current label: '{current_label}'")
                    set_text = (f"error setting '{label_hint}': {transaction_response.error}"
                                if transaction_response.error else f"set '{label_hint}'")
                    self.label_outcome = f"{set_text}, read back '{current_label}'"

            if transaction is not None:
                self.reaction_response.result = transaction.response.result
                self.reaction_response.error = transaction.response.error
            return reply

        @defer.inlineCallbacks
        def recorded_reactize() -> deferred_response:
            # a caller whose reactor this method ran never sees the Deferred, so a death is kept for it, and raised on
            try:
                reply = yield reactize()
            except Exception as exc:
                self.label_outcome = f'died: {type(exc).__name__}: {exc}'
                self.logger.error(f'Label step {self.label_outcome}')
                raise
            return reply

        self.label_outcome = None
        self.reaction_response = DelugApiResponse()
        return DelugApi.delugapi_wrap(recorded_reactize)

    def jellyfin_refresh(self, label_handler: TorrentLabelHandlor, destination: str) -> None:
        label = label_handler.label
        library_name = label_handler.jelly_library_name
        title = label_handler.title
        self.logger.exclaim(f'jellyfin_refresh: "{label}" "{library_name}" "{destination}"')
        communicator = JellyfinCommunicator()
        communicator.refresh_library(library_name, title=title)
