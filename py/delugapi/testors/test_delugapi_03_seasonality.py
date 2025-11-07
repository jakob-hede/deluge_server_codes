#!/usr/bin/env python3
from pathlib import Path
import import_helpor  # noqa NEEDED!!!


class Testor:
    def __init__(self):
        super().__init__()

    def executize(self):
        print("Testor.executize...")
        # self.commonize()
        self.seasonalitize()

    def commonize(self):
        from executin.commons import Commons
        deluge_root_dir: Path = Commons.singleton.deluge_root_dir
        print(f"Deluge Root Dir: '{deluge_root_dir}'")

    def seasonalitize(self):
        print("Testor.seasonalitize...")
        """Test the DelugAPI client."""
        from delugapi import DelugapiClient
        client = DelugapiClient()

        # Test torrents
        print("=== Testing get_torrents_json ===")
        response = client.test3_seasonality()
        print(f"\nFINAL response: {response}")


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
