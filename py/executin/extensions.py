"""extensions — the file suffixes the hooks sort a torrent's files by, lowercase with their dot.

Light by design: nothing imported, so Oceanic's hook reads the video suffixes without loading the movie handler,
whose module brings in yaml and the Deluge client. TorrentHandlorMovin reads both tuples from here.
"""

video_extensions: tuple[str, ...] = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.m4v', '.ts')
subtitle_extensions: tuple[str, ...] = ('.srt', '.ass', '.ssa', '.vtt', '.sub')
