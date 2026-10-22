#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
from executin.jellyfin_communicator import JellyfinCommunicator


class EmptyResponse:
    def json(self) -> list:
        return []


class RecordingCommunicator(JellyfinCommunicator):
    # records method, path and params only, never the headers that carry the api key
    def __init__(self):
        super().__init__()
        self.recorded_calls: list[tuple[str, str, dict | None]] = []

    def fetch_library_name_to_id(self, library_name: str) -> str:
        return 'movin-library-id'

    def _request(self, method: str, path: str, params: dict | None = None, json: dict | None = None) -> EmptyResponse:
        self.recorded_calls.append((method, path, params))
        return EmptyResponse()


class Testor:
    def __init__(self):
        super().__init__()

    def executize(self):
        print("Testor.executize...")
        communicator = RecordingCommunicator()
        communicator.refresh_library('movin', title='x')
        for method, path, params in communicator.recorded_calls:
            print(f"recorded: {method} {path} params={params}")
        expected_params = {
            'metadataRefreshMode': 'Default',
            'imageRefreshMode': 'Default',
            'replaceAllMetadata': 'false',
            'replaceAllImages': 'false',
        }
        method, path, params = communicator.recorded_calls[0]
        is_refresh_as_expected = method == 'POST' and path == '/Items/movin-library-id/Refresh' and params == expected_params
        is_sessions_only = [call[:2] for call in communicator.recorded_calls[1:]] == [('GET', '/Sessions')]
        print(f"refresh call as expected: {is_refresh_as_expected}")
        print(f"then only GET /Sessions, no toast sent: {is_sessions_only}")
        print(f"all as expected: {is_refresh_as_expected and is_sessions_only}")


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
