# Torrent File Analysis Tools

This directory contains tools for analyzing and extracting information from .torrent files using the LinuxServer Deluge container.

## Available Tools

### torrent_info.py
A comprehensive Python script that extracts detailed information from .torrent files.

**Features:**
- Basic torrent information (name, size, number of files)
- Hash information (info hash)
- Metadata (creation date, creator, comments)
- Complete tracker list
- Detailed file listing with sizes
- Web seed information
- Private torrent detection

**Usage:**
```bash
# From within the Deluge container
docker exec deluge python3 /codes/copilot/torrent_info.py /path/to/file.torrent

# Example with a torrent file in the torrents directory
docker exec deluge python3 /codes/copilot/torrent_info.py /deluge/torrents/example.torrent
```

## Information Extractable from .torrent Files

### Core Metadata
- **announce**: Primary tracker URL
- **announce-list**: List of backup trackers  
- **info**: Dictionary containing file/directory information
- **creation date**: When the torrent was created (Unix timestamp)
- **created by**: The program that created the torrent
- **comment**: Optional comment about the torrent

### File Information
- **name**: Name of the file or top-level directory
- **length**: Size of files in bytes
- **piece length**: Size of each piece (typically 16KB to 4MB)
- **pieces**: SHA1 hashes of each piece (for integrity verification)
- **files**: List of files (for multi-file torrents) with relative paths and sizes
- **info_hash**: Unique 20-byte SHA1 hash identifier

### Optional Fields
- **encoding**: Character encoding used
- **nodes**: DHT bootstrap nodes for trackerless torrents
- **url-list**: Web seed URLs for HTTP/FTP downloading
- **private**: Flag indicating if torrent is private (no DHT/PEX)

### Advanced Information
- **piece layers**: For BitTorrent v2 (hybrid torrents)
- **file tree**: v2 format file organization
- **meta version**: BitTorrent protocol version

## LinuxServer Deluge Container Tools

The `lscr.io/linuxserver/deluge` container includes:

- **libtorrent-rasterbar 2.0.11**: Core C++ library
- **Python 3.12 bindings**: Full Python API access
- **Deluge's built-in modules**: 
  - `deluge.maketorrent`: Create torrents
  - `deluge.core.torrent`: Torrent management
  - `deluge._libtorrent`: LibTorrent wrapper

### Python libtorrent Capabilities

The container's Python environment provides access to:

```python
import libtorrent as lt

# Key classes and methods:
info = lt.torrent_info(torrent_path)
info.name()           # Torrent name
info.total_size()     # Total size in bytes
info.num_files()      # Number of files
info.files()          # File list object
info.trackers()       # Tracker list
info.creation_date()  # Creation timestamp
info.creator()        # Creator string
info.comment()        # Comment
info.info_hash()      # Info hash
info.priv()          # Private flag
```

## Examples

### Quick Info Check
```bash
docker exec deluge python3 /codes/copilot/torrent_info.py /deluge/torrents/movie.torrent
```

### Batch Analysis
```bash
# Analyze all torrents in the torrents directory
docker exec deluge find /deluge/torrents -name "*.torrent" -exec python3 /codes/copilot/torrent_info.py {} \;
```

### Integration with Deluge
Since the `/codes` directory is mounted, these tools are accessible from within the Deluge container and can be used in:
- Execute plugin scripts
- Custom Deluge plugins
- Automated torrent processing workflows
- Post-download scripts

## Notes

- The tools work with both BitTorrent v1 and v2 torrent files
- Large file lists are truncated in display (first 50 files shown)
- All size values are displayed in human-readable format
- Error handling includes file existence and format validation
- Compatible with the specific libtorrent version in the LinuxServer container
