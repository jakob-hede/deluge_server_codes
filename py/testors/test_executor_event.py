#!/usr/bin/env python3
import sys
import import_helpor  # noqa NEEDED!!!
from executin.logge import DelugapiTorrentorLoggor
from runs.executor import Executor, main as executor_main

'''
4a7c2c977504e01e60c08278289bc416a3a7572d
The.Lowdown.2025.S01E03.1080p.x265-ELiTE
tv-in
/ocean/video/tv/the.lowdown/s01
'''

block = '''
4aaee570dd5aa14b880899f61452bcc4e6d6da7f
A.Knight.of.the.Seven.Kingdoms.S01E04.1080p.x265-ELiTE
tv-in
/ocean/video/tv/a.knight.of.the.seven.kingdoms/s01
'''

class Testor:
    def __init__(self):
        super().__init__()
        self.logger = DelugapiTorrentorLoggor()
        self.event_name = 'exe_completed'
        self.torrent_id = ''
        self.torrent_name = ''
        self.base_sdir = ''
        self.label = ''

    def read_block(self):
        lines = block.strip().splitlines()
        if len(lines) != 4:
            self.logger.error("Block does not have exactly 4 lines ABORTING!!!")
            return
        self.torrent_id = lines.pop(0).strip()
        self.torrent_name = lines.pop(0).strip()
        self.label = lines.pop(0).strip()
        self.base_sdir = lines.pop(0).strip()

    def show_block(self):
        print(f"Event:         '{self.event_name}'")
        print(f"Torrent ID:    '{self.torrent_id}'")
        print(f"Torrent Name:  '{self.torrent_name}'")
        print(f"Base Save Dir: '{self.base_sdir}'")
        print(f"Label:         '{self.label}'")

    def executize(self):
        print("Testor.executize...")
        self.read_block()
        self.show_block()
        if not self.torrent_id:
            self.logger.error("torrent_id is empty ABORTING!!!")
            return
        sys.argv.append(self.event_name)
        sys.argv.append(self.torrent_id)
        sys.argv.append(self.torrent_name)
        sys.argv.append(self.base_sdir)
        executor_main()


    def executize_remove(self):
        print("Testor.executize...")

        # sys.argv.append('exe_status')
        # sys.argv.append('exe_added')

        # event_name = 'exe_added'
        event_name = 'exe_removed'
        torrent_id = '4a7c2c977504e01e60c08278289bc416a3a7572d'
        torrent_name = 'The.Lowdown.2025.S01E03.1080p.x265-ELiTE'
        base_sdir = '/ocean/video/tv/the.lowdown/s01'
        sys.argv.append(event_name)
        sys.argv.append(torrent_id)
        sys.argv.append(torrent_name)
        sys.argv.append(base_sdir)

        executor_main()

        # executor = Executor()
        # executor.test_basic()

        # # event_name = 'exe_completed'
        # event_name = 'exe_added'
        # torrent_id = '94941321a2d383ddf0b276f94c889b980715c072'
        # torrent_name = 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]'
        # # base_sdir = '/ocean/video/movies/movin'
        # base_sdir = '/ocean/test/area51'
        #
        # # print(f"Event: '{event_name}'")
        # # print(f"Torrent ID: '{torrent_id}'")
        # # print(f"Torrent Name: '{torrent_name}'")
        # # print(f"Base Save Dir: '{base_sdir}'")
        #
        # torrentor = Torrentor(torrent_id, torrent_name, base_sdir)
        # torrentor.process_event(event_name)


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
