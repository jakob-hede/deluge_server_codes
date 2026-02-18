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

    def _request(self, method: str, path: str) -> requests.Response:
        url = f"{self.server_url}{path}"
        headers = {"X-Emby-Token": self.api_key}
        response = requests.request(method, url, headers=headers, timeout=30)
        response.raise_for_status()
        return response

    def refresh_library(self, library_name: str):
        self.logger.exclaim(f"Refreshing Jellyfin library '{library_name}'...")
        library_id = self.fetch_library_name_to_id(library_name)
        self.logger.info(f"Library name '{library_name}' corresponds to library ID '{library_id}'")
        self._request("POST", f"/Items/{library_id}/Refresh")
        self.logger.info(f"Jellyfin library '{library_name}' refresh triggered successfully")

    def fetch_library_name_to_id(self, library_name: str) -> str:
        self.logger.exclaim(f"Fetching Jellyfin library ID for '{library_name}'")
        response = self._request("GET", "/Library/VirtualFolders")
        for folder in response.json():
            if folder["Name"] == library_name:
                library_id = folder["ItemId"]
                self.logger.info(f"Found library '{library_name}' with ID '{library_id}'")
                return library_id
        raise ValueError(f"Jellyfin library '{library_name}' not found")
