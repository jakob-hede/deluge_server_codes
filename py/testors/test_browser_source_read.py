#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
from executin.torrentor import Torrentor


class Testor:
    def __init__(self):
        super().__init__()

    def executize(self):
        print("Testor.executize...")
        torrent_id = 'e128a283a6f8b0143f48bbbff276b6602b785280'
        base_sdir = '/deluge/downloads'

        torrentor = Torrentor(torrent_id, 'x', base_sdir)
        print(f"browser_source_file: '{torrentor.browser_source_file}'")
        data = torrentor.browser_source_file_read_data()
        print(f"label_hint: '{data.get('label_hint')}'  label_hint_via: '{data.get('label_hint_via')}'")
        print(f"keys: {list(data)}")

        absent_torrentor = Torrentor('0' * 40, 'x', base_sdir)
        absent_data = absent_torrentor.browser_source_file_read_data()
        print(f"absent: {absent_data}")


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
