#!/usr/bin/env python3
import sys

sys.path.append('/codes/py')

from executin.torrentor import Torrentor


class Testor:
    def __init__(self):
        super().__init__()

    def executize(self):
        print("Testor.executize...")
        # event_name = 'exe_completed'
        event_name = 'exe_added'
        torrent_id = '94941321a2d383ddf0b276f94c889b980715c072'
        torrent_name = 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]'
        # base_sdir = '/ocean/video/movies/movin'
        base_sdir = '/ocean/test/area51'

        # print(f"Event: '{event_name}'")
        # print(f"Torrent ID: '{torrent_id}'")
        # print(f"Torrent Name: '{torrent_name}'")
        # print(f"Base Save Dir: '{base_sdir}'")

        torrentor = Torrentor(torrent_id, torrent_name, base_sdir)
        torrentor.process_event(event_name)


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()

'''
 - 0: '/codes/py/executor.py'
 - 1: 'exe_added'
 - 2: '8178b09bde84d46c945b7b601b8bc3c0a959569e'
 - 3: 'Friendship (2025) [1080p] [WEBRip] [5.1] [YTS.MX]'
 - 4: '/deluge/downloads'
'''
