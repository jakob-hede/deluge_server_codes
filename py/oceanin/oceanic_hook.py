from __future__ import annotations

from executin.logge import Loggor, OceanorLoggor


class OceanicHook:
    """
    Oceanic's hook, which oceanor.py hands every oce_ event. Only the loggor is imported here: whatever is heavy,
    yaml, the announcor, the Jellyfin communicator, is imported inside the method that acts, when it acts, so a
    plain remove costs the interpreter and a log line.
    """

    def __init__(self, torrent_id: str, torrent_name: str, base_sdir: str, loggor: Loggor | None = None):
        super().__init__()
        self.torrent_id = torrent_id
        self.torrent_name = torrent_name
        self.base_sdir = base_sdir
        self.loggor = loggor or OceanorLoggor()

    def process_event(self, event_name: str, *extras: str) -> bool | None:
        if event_name == 'oce_removed':
            return self.on_dummy_removed()
        elif event_name == 'oce_deleted':
            return self.on_dummy_deleted()
        elif event_name == 'oce_delete_failed':
            return self.on_dummy_delete_failed(*extras)
        self.loggor.error(f"Unknown event: '{event_name}' for torrent '{self.torrent_name}' ({self.torrent_id})")
        return None

    def on_dummy_removed(self) -> bool:
        self.loggor.info(f"Torrent '{self.torrent_name}' has been DUMMY oce_removed.. id '{self.torrent_id}' "
                         f"location '{self.base_sdir}'")
        return True

    def on_dummy_deleted(self) -> bool:
        self.loggor.info(f"Torrent '{self.torrent_name}' has been DUMMY oce_deleted.. id '{self.torrent_id}' "
                         f"location '{self.base_sdir}'")
        return True

    def on_dummy_delete_failed(self, error: str = '') -> bool:
        self.loggor.info(f"Torrent '{self.torrent_name}' has been DUMMY oce_delete_failed.. id '{self.torrent_id}' "
                         f"location '{self.base_sdir}' error '{error}'")
        return True
