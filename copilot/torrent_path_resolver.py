#!/usr/bin/env python3
"""
Torrent Path Resolver

Demonstrates how to get exact file paths from torrent info,
regardless of torrent structure type.
"""

import libtorrent as lt
import sys
import os
from pathlib import Path


def resolve_exact_paths(torrent_path, download_base="/deluge/done"):
    """
    Get exact file paths that would be created after download,
    regardless of torrent structure type.
    """
    try:
        info = lt.torrent_info(torrent_path)
        files = info.files()
        
        print(f"Resolving paths for: {info.name()}")
        print(f"Torrent ID: {info.info_hash()}")
        print(f"Download base: {download_base}")
        print()
        
        # Get all file paths with their exact download locations
        file_manifest = []
        
        for i in range(files.num_files()):
            relative_path = files.file_path(i)
            file_size = files.file_size(i)
            absolute_path = os.path.join(download_base, relative_path)
            
            file_info = {
                'index': i,
                'relative_path': relative_path,
                'absolute_path': absolute_path,
                'size': file_size,
                'directory': os.path.dirname(absolute_path),
                'filename': os.path.basename(absolute_path)
            }
            file_manifest.append(file_info)
        
        # Display the manifest
        print(f"COMPLETE FILE MANIFEST ({len(file_manifest)} files):")
        print("-" * 80)
        
        for file_info in file_manifest:
            print(f"[{file_info['index']:3d}] {file_info['absolute_path']}")
            print(f"      Size: {file_info['size']:,} bytes")
            print(f"      Dir:  {file_info['directory']}")
            print(f"      File: {file_info['filename']}")
            print()
        
        # Analyze what Execute plugin would receive vs what files actually exist
        print("=" * 80)
        print("EXECUTE PLUGIN ANALYSIS:")
        
        if info.num_files() == 1:
            # Single file
            single_file = file_manifest[0]
            execute_path = single_file['absolute_path']
            print(f"Structure: Single file")
            print(f"Execute would receive: {execute_path}")
            print(f"This points to: THE ACTUAL FILE")
            
        else:
            # Multi-file - determine what Execute would pass
            
            # Check structure type
            root_files = [f for f in file_manifest if len(Path(f['relative_path']).parts) == 1]
            directories = set(Path(f['relative_path']).parts[0] for f in file_manifest if len(Path(f['relative_path']).parts) > 1)
            
            if len(directories) == 1 and len(root_files) == 0:
                # Single directory
                directory_name = list(directories)[0]
                execute_path = os.path.join(download_base, directory_name)
                print(f"Structure: Single directory")
                print(f"Execute would receive: {execute_path}")
                print(f"This points to: DIRECTORY containing all files")
                
            else:
                # Multiple items at root
                execute_path = download_base
                print(f"Structure: Multiple items at root")
                print(f"Execute would receive: {execute_path}")
                print(f"This points to: DOWNLOAD DIRECTORY (not specific files)")
        
        print()
        print("HOW TO RESOLVE ALL FILES IN EXECUTE SCRIPT:")
        print("=" * 50)
        
        if info.num_files() == 1:
            print("# Single file - path points to the file")
            print("file_path = sys.argv[3]")
            print("process_file(file_path)")
            
        else:
            print("# Multi-file - you have two options:")
            print()
            print("# OPTION 1: Use torrent info to get exact paths")
            print("torrent_id = sys.argv[1]")
            print("# Find corresponding .torrent file and read manifest")
            print("# (like this script does)")
            print()
            print("# OPTION 2: Scan the provided directory")
            print("torrent_path = sys.argv[3]")
            print("if os.path.isdir(torrent_path):")
            print("    for root, dirs, files in os.walk(torrent_path):")
            print("        for file in files:")
            print("            file_path = os.path.join(root, file)")
            print("            process_file(file_path)")
        
        print()
        print("TORRENT FILE PATHS ARE ALWAYS PREDICTABLE!")
        print("• The .torrent file contains the complete file manifest")
        print("• Paths are relative to download directory")
        print("• File structure is deterministic")
        print("• You can always calculate exact absolute paths")
        
        return file_manifest
        
    except Exception as e:
        print(f"Error resolving paths: {e}")
        return None


def demonstrate_with_execute_simulation(torrent_path):
    """Simulate what an Execute plugin script would receive and how to handle it"""
    
    try:
        info = lt.torrent_info(torrent_path)
        files = info.files()
        
        # Simulate Execute plugin arguments
        mock_torrent_id = str(info.info_hash())
        mock_torrent_name = info.name()
        
        # Determine what Execute would pass as path
        if info.num_files() == 1:
            mock_torrent_path = f"/deluge/done/{files.file_path(0)}"
        else:
            # Check if single directory
            file_paths = [files.file_path(i) for i in range(files.num_files())]
            directories = set(Path(fp).parts[0] for fp in file_paths if len(Path(fp).parts) > 1)
            root_files = [fp for fp in file_paths if len(Path(fp).parts) == 1]
            
            if len(directories) == 1 and len(root_files) == 0:
                # Single directory
                directory_name = list(directories)[0]
                mock_torrent_path = f"/deluge/done/{directory_name}"
            else:
                # Multiple items at root
                mock_torrent_path = "/deluge/done"
        
        print()
        print("EXECUTE PLUGIN SIMULATION:")
        print("=" * 40)
        print("Your script would be called with:")
        print(f"  python3 my_script.py \\")
        print(f"    '{mock_torrent_id}' \\")
        print(f"    '{mock_torrent_name}' \\")
        print(f"    '{mock_torrent_path}'")
        
        print()
        print("From these arguments, you can:")
        print("1. Use the torrent_id to find the .torrent file")
        print("2. Read the .torrent file to get complete file manifest")
        print("3. Calculate exact paths to all files")
        print("4. Process each file individually")
        
    except Exception as e:
        print(f"Error in simulation: {e}")


def main():
    if len(sys.argv) not in [2, 3]:
        print("Torrent Path Resolver")
        print("=" * 30)
        print("Usage: python3 torrent_path_resolver.py <torrent_file> [download_base]")
        print()
        print("This script shows how to resolve exact file paths from torrent info,")
        print("regardless of torrent structure type.")
        print()
        print("Arguments:")
        print("  torrent_file    : Path to .torrent file")
        print("  download_base   : Base download directory (default: /deluge/done)")
        sys.exit(1)
    
    torrent_file = sys.argv[1]
    download_base = sys.argv[2] if len(sys.argv) > 2 else "/deluge/done"
    
    if not os.path.exists(torrent_file):
        print(f"Error: File '{torrent_file}' not found")
        sys.exit(1)
    
    # Resolve all paths
    file_manifest = resolve_exact_paths(torrent_file, download_base)
    
    if file_manifest:
        # Show Execute plugin simulation
        demonstrate_with_execute_simulation(torrent_file)


if __name__ == '__main__':
    main()
