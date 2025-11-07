#!/usr/bin/env python3
"""
Torrent File Information Extractor

This script extracts and displays detailed information from .torrent files
using the libtorrent library available in the LinuxServer Deluge container.

Usage:
    python3 torrent_info.py <torrent_file>
    
Example:
    python3 torrent_info.py /path/to/file.torrent
"""

import libtorrent as lt
import sys
import os
import datetime


def format_size(bytes_size):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def extract_torrent_info(torrent_path):
    """Extract comprehensive information from a .torrent file"""
    try:
        # Load torrent file
        info = lt.torrent_info(torrent_path)
        
        print(f"{'='*60}")
        print(f"TORRENT FILE INFORMATION")
        print(f"{'='*60}")
        print(f"File: {os.path.basename(torrent_path)}")
        print(f"Path: {torrent_path}")
        print()
        
        # Basic Information
        print("BASIC INFORMATION:")
        print(f"  Name: {info.name()}")
        print(f"  Total Size: {format_size(info.total_size())} ({info.total_size():,} bytes)")
        print(f"  Number of Files: {info.num_files()}")
        print(f"  Piece Length: {format_size(info.piece_length())} ({info.piece_length():,} bytes)")
        print(f"  Number of Pieces: {info.num_pieces()}")
        print()
        
        # Hash Information
        print("HASH INFORMATION:")
        print(f"  Info Hash: {info.info_hash()}")
        print(f"  Info Hash (hex): {str(info.info_hash())}")
        print()
        
        # Metadata
        print("METADATA:")
        if info.creation_date():
            creation_date = datetime.datetime.fromtimestamp(info.creation_date())
            print(f"  Creation Date: {creation_date.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("  Creation Date: Not specified")
            
        if info.creator():
            print(f"  Created By: {info.creator()}")
        else:
            print("  Created By: Not specified")
            
        if info.comment():
            print(f"  Comment: {info.comment()}")
        else:
            print("  Comment: None")
        print()
        
        # Tracker Information
        trackers = list(info.trackers())
        print(f"TRACKERS ({len(trackers)}):")
        if trackers:
            for i, tracker in enumerate(trackers, 1):
                print(f"  {i:2d}. {tracker.url}")
                if hasattr(tracker, 'tier') and tracker.tier > 0:
                    print(f"      Tier: {tracker.tier}")
        else:
            print("  No trackers found")
        print()
        
        # File Information
        files = info.files()
        print(f"FILES ({info.num_files()}):")
        if info.num_files() > 0:
            total_displayed = 0
            max_display = 50  # Limit display for very large torrents
            
            for i in range(files.num_files()):
                if total_displayed >= max_display:
                    remaining = info.num_files() - total_displayed
                    print(f"  ... and {remaining} more files")
                    break
                    
                file_path = files.file_path(i)
                file_size = files.file_size(i)
                print(f"  {file_path}")
                print(f"    Size: {format_size(file_size)} ({file_size:,} bytes)")
                total_displayed += 1
        else:
            print("  No files found")
        print()
        
        # Additional Information
        print("ADDITIONAL INFORMATION:")
        print(f"  Private Torrent: {'Yes' if info.priv() else 'No'}")
        
        # Web seeds
        web_seeds = []
        try:
            # Note: web_seeds() method might not be available in all versions
            if hasattr(info, 'web_seeds'):
                web_seeds = list(info.web_seeds())
        except Exception as e:
            # Silently handle any web_seeds errors
            pass
            
        if web_seeds:
            print(f"  Web Seeds ({len(web_seeds)}):")
            for seed in web_seeds:
                print(f"    {seed}")
        else:
            print("  Web Seeds: None")
            
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"Error reading torrent file '{torrent_path}': {e}")
        return False
    
    return True


def main():
    if len(sys.argv) != 2:
        print("Torrent File Information Extractor")
        print("=" * 40)
        print("Usage: python3 torrent_info.py <torrent_file>")
        print()
        print("This script extracts and displays comprehensive information")
        print("from .torrent files including:")
        print("  - Basic torrent information (name, size, files)")
        print("  - Hash information")
        print("  - Metadata (creation date, creator, comments)")
        print("  - Tracker URLs")
        print("  - File listing with sizes")
        print("  - Additional properties")
        print()
        print("Example:")
        print("  python3 torrent_info.py /deluge/torrents/example.torrent")
        sys.exit(1)
    
    torrent_file = sys.argv[1]
    
    if not os.path.exists(torrent_file):
        print(f"Error: File '{torrent_file}' not found")
        sys.exit(1)
    
    if not torrent_file.lower().endswith('.torrent'):
        print(f"Warning: File '{torrent_file}' doesn't have .torrent extension")
    
    success = extract_torrent_info(torrent_file)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
