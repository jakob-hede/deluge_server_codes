#!/usr/bin/env python3
"""
Deluge Execute Plugin Argument Logger

This script logs all arguments passed by the Deluge Execute plugin
to understand how it handles different torrent structures.
"""

import sys
import os
import datetime
from pathlib import Path


def log_execute_args():
    """Log all arguments passed to this script by Deluge Execute plugin"""
    
    log_file = "/codes/copilot/execute_plugin_args.log"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Collect all information
    info = {
        "timestamp": timestamp,
        "argc": len(sys.argv),
        "args": sys.argv,
        "cwd": os.getcwd(),
        "env_vars": {}
    }
    
    # Capture relevant environment variables
    env_keys = ["TORRENT_ID", "TORRENT_NAME", "TORRENT_PATH", "TORRENT_LABEL"]
    for key in env_keys:
        if key in os.environ:
            info["env_vars"][key] = os.environ[key]
    
    # Expected Deluge Execute plugin arguments based on your example:
    # arg0: script name
    # arg1: torrent_id (hash)
    # arg2: torrent_name 
    # arg3: torrent_path
    
    print(f"=== Deluge Execute Plugin Args - {timestamp} ===")
    print(f"Total arguments: {len(sys.argv)}")
    print()
    
    for i, arg in enumerate(sys.argv):
        print(f"arg[{i}]: {repr(arg)}")
    
    print()
    print(f"Current working directory: {os.getcwd()}")
    
    if info["env_vars"]:
        print("Environment variables:")
        for key, value in info["env_vars"].items():
            print(f"  {key}: {repr(value)}")
    
    # Analyze the expected arguments
    if len(sys.argv) >= 4:
        torrent_id = sys.argv[1]
        torrent_name = sys.argv[2]  
        torrent_path = sys.argv[3]
        
        print()
        print("=== PARSED DELUGE ARGUMENTS ===")
        print(f"Torrent ID (hash): {torrent_id}")
        print(f"Torrent Name: {torrent_name}")
        print(f"Torrent Path: {torrent_path}")
        
        # Check if path exists and analyze it
        if os.path.exists(torrent_path):
            path_obj = Path(torrent_path)
            print(f"Path exists: Yes")
            print(f"Is file: {path_obj.is_file()}")
            print(f"Is directory: {path_obj.is_dir()}")
            
            if path_obj.is_dir():
                print("Directory contents:")
                try:
                    contents = list(path_obj.iterdir())
                    for item in contents[:10]:  # Show first 10 items
                        item_type = "DIR" if item.is_dir() else "FILE"
                        size = item.stat().st_size if item.is_file() else 0
                        print(f"  [{item_type}] {item.name} ({size} bytes)")
                    if len(contents) > 10:
                        print(f"  ... and {len(contents) - 10} more items")
                except Exception as e:
                    print(f"  Error listing directory: {e}")
            else:
                # Single file
                try:
                    size = path_obj.stat().st_size
                    print(f"File size: {size} bytes")
                except Exception as e:
                    print(f"Error getting file info: {e}")
        else:
            print(f"Path exists: No")
    
    # Write to log file
    try:
        with open(log_file, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Arguments ({len(sys.argv)}):\n")
            for i, arg in enumerate(sys.argv):
                f.write(f"  [{i}] {repr(arg)}\n")
            f.write(f"CWD: {os.getcwd()}\n")
            if info["env_vars"]:
                f.write("Environment:\n")
                for key, value in info["env_vars"].items():
                    f.write(f"  {key}: {repr(value)}\n")
            f.write("\n")
        print(f"\nLogged to: {log_file}")
    except Exception as e:
        print(f"Error writing to log: {e}")


def main():
    print("Deluge Execute Plugin Argument Logger")
    print("=" * 50)
    
    log_execute_args()
    
    # Also try to find the corresponding .torrent file and analyze its structure
    if len(sys.argv) >= 4:
        torrent_id = sys.argv[1]
        
        # Look for torrent file
        torrent_file_pattern = f"/deluge/torrents/*{torrent_id[:8]}*.torrent"
        print(f"\nSearching for torrent file matching: {torrent_id[:8]}")
        
        import glob
        matching_torrents = glob.glob(f"/deluge/torrents/*.torrent")
        
        for torrent_file in matching_torrents:
            # Try to match by reading the torrent and comparing info hash
            try:
                import libtorrent as lt
                info = lt.torrent_info(torrent_file)
                if str(info.info_hash()) == torrent_id:
                    print(f"Found matching torrent file: {torrent_file}")
                    
                    # Quick structure analysis
                    if info.num_files() == 1:
                        print("Structure: Single file")
                    else:
                        print(f"Structure: Multi-file ({info.num_files()} files)")
                        
                        # Check if wrapped in directory
                        files = info.files()
                        first_file = files.file_path(0)
                        if '/' in first_file:
                            print("Files are in subdirectory(ies)")
                        else:
                            print("Files are at root level")
                    break
            except Exception as e:
                continue


if __name__ == '__main__':
    main()
