class TorrentInfo:
    def __init__(self, tid: str, name: str, progress: float, state: str,
                 download_payload_rate: int, upload_payload_rate: int,
                 total_downloaded: int, total_uploaded: int, eta: int):
        self.tid = tid
        self.name = name
        self.progress = progress
        self.state = state
        self.download_payload_rate = download_payload_rate
        self.upload_payload_rate = upload_payload_rate
        self.total_downloaded = total_downloaded
        self.total_uploaded = total_uploaded
        self.eta = eta

    # def __str__(self) -> str:
    #     txt = (f'TorrentInfo(id={self.id}, name={self.name}, progress={self.progress}, '
    #            f'state={self.state}, download_payload_rate={self.download_payload_rate}, '
    #            f'upload_payload_rate={self.upload_payload_rate}, total_downloaded={self.total_downloaded}, '
    #            f'total_uploaded={self.total_uploaded}, eta={self.eta})')
    #     return txt

    def __str__(self) -> str:
        txt = f'TorrentInfo(id={self.tid}, name="{self.name}"'
        return txt


    @classmethod
    def from_dict(cls, status_dict: dict) -> 'TorrentInfo':
        tid: str
        data: dict
        tid, data = next(iter(status_dict.items()))
        name = data.get('name', '')
        progress = data.get('progress', 0.0)
        state = data.get('state', '')
        download_payload_rate = data.get('download_payload_rate', 0)
        upload_payload_rate = data.get('upload_payload_rate', 0)
        total_downloaded = data.get('all_time_download', 0)


'''
{'94941321a2d383ddf0b276f94c889b980715c072': {'name': 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]', 'hash': '94941321a2d383ddf0b276f94c889b980715c072', 'files': ({'index': 0, 'path': 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]/The.Naked.Gun.2025.1080p.WEBRip.x264.AAC5.1-[YTS.MX].mp4', 'size': 1685846390, 'offset': 0}, {'index': 1, 'path': 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]/The.Naked.Gun.2025.1080p.WEBRip.x264.AAC5.1-[YTS.MX].srt', 'size': 115469, 'offset': 1685846390}, {'index': 2, 'path': 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]/YTSYifyUP... (TOR).txt', 'size': 604, 'offset': 1685961859}, {'index': 3, 'path': 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]/www.YTS.MX.jpg', 'size': 53226, 'offset': 1685962463}, {'index': 4, 'path': 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]/Subs/English (CC).eng.srt', 'size': 115469, 'offset': 1686015689}, {'index': 5, 'path': 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]/Subs/Français (Canada).fre.srt', 'size': 85688, 'offset': 1686131158}), 'download_location': '/ocean/test/area51', 'save_path': '/ocean/test/area51', 'orig_files': ({'index': 0, 'path': 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]/The.Naked.Gun.2025.1080p.WEBRip.x264.AAC5.1-[YTS.MX].mp4', 'size': 1685846390, 'offset': 0}, {'index': 1, 'path': 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]/The.Naked.Gun.2025.1080p.WEBRip.x264.AAC5.1-[YTS.MX].srt', 'size': 115469, 'offset': 1685846390}, {'index': 2, 'path': 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]/YTSYifyUP... (TOR).txt', 'size': 604, 'offset': 1685961859}, {'index': 3, 'path': 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]/www.YTS.MX.jpg', 'size': 53226, 'offset': 1685962463}, {'index': 4, 'path': 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]/Subs/English (CC).eng.srt', 'size': 115469, 'offset': 1686015689}, {'index': 5, 'path': 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]/Subs/Français (Canada).fre.srt', 'size': 85688, 'offset': 1686131158}), 'move_completed_path': '/ocean/video/movies/movin', 'label': 'ocean-movin'}}
'''