import requests

from executin.logge import DelugapiTorrentorLoggor
from salaisuudet.secrets import Secretor


class JellyfinCommunicator:
    def __init__(self):
        self.logger = DelugapiTorrentorLoggor()
        self.app_name = Secretor.jellyfin_app_name
        self.api_key = Secretor.jellyfin_api_key

        server_url_ronja = 'http://10.4.9.11:8096'
        self.server_url = server_url_ronja

        self.logger.exclaim(f"JellyfinCommunicator initialized with app name '{self.app_name}'")

    def _request(self, method: str, path: str, params: dict | None = None, json: dict | None = None) -> requests.Response:
        url = f"{self.server_url}{path}"
        headers = {"X-Emby-Token": self.api_key}
        response = requests.request(method, url, headers=headers, params=params, json=json, timeout=30)
        response.raise_for_status()
        return response

    def refresh_library(self, library_name: str, title: str = '') -> None:
        self.logger.exclaim(f"Refreshing Jellyfin library '{library_name}'...")
        library_id = self.fetch_library_name_to_id(library_name)
        self.logger.info(f"Library name '{library_name}' corresponds to library ID '{library_id}'")
        self._request("POST", f"/Items/{library_id}/Refresh", params={
            "metadataRefreshMode": "FullRefresh",
            "imageRefreshMode": "FullRefresh",
            "replaceAllMetadata": "false",
            "replaceAllImages": "false",
        })
        self.logger.info(f"Jellyfin library '{library_name}' refresh triggered successfully")
        self.notify_clients_refresh(library_name, title)

    def notify_clients_refresh(self, library_name: str, title: str = '') -> None:
        """Send a toast message to all active Jellyfin sessions."""
        response = self._request("GET", "/Sessions")
        sessions = response.json()
        controllable = [s for s in sessions if s.get("SupportsRemoteControl", False)]
        self.logger.debug(f"Found {len(controllable)}/{len(sessions)} controllable sessions")
        notified = 0
        for session in controllable:
            session_id = session["Id"]
            try:
                txt = f"'{library_name}' library has been refreshed"
                if title:
                    txt += f" due to '{title}'"
                self._request("POST", f"/Sessions/{session_id}/Message", json={
                    "Header": "Library Updated",
                    "Text": f'{txt}',
                })
                notified += 1
                self.logger.remark(f"Sent toast to session #{notified}  '{session_id}'")
                self.logger.debug(f"info: {session}")
            except requests.HTTPError:
                self.logger.debug(f"Could not notify session '{session_id}', skipping")
        self.logger.info(f"Notified {notified}/{len(controllable)} controllable client sessions")

    def fetch_library_name_to_id(self, library_name: str) -> str:
        self.logger.exclaim(f"Fetching Jellyfin library ID for '{library_name}'")
        response = self._request("GET", "/Library/VirtualFolders")
        for folder in response.json():
            if folder["Name"] == library_name:
                library_id = folder["ItemId"]
                self.logger.info(f"Found library '{library_name}' with ID '{library_id}'")
                return library_id
        raise ValueError(f"Jellyfin library '{library_name}' not found")
