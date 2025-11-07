#!/usr/bin/env python3
"""
Deluge Execute Plugin Behavior Analyzer

Analyzes how Deluge Execute plugin should behave with different torrent structures.
"""

import libtorrent as lt
import sys
import os
from pathlib import Path


def analyze_execute_behavior(torrent_path):
    """Analyze how Deluge Execute plugin would behave with this torrent"""
    try:
        info = lt.torrent_info(torrent_path)
        files = info.files()
        
        print(f"Analyzing Execute plugin behavior for: {info.name()}")
        print(f"Torrent ID (info_hash): {info.info_hash()}")
        print(f"Number of files: {info.num_files()}")
        print()
        
        # Determine what Deluge would pass as the "path" argument
        if info.num_files() == 1:
            # Single file torrent
            file_path = files.file_path(0)
            print("=== SINGLE FILE TORRENT ===")
            print(f"Execute plugin would receive:")
            print(f"  arg[1] (torrent_id): {info.info_hash()}")
            print(f"  arg[2] (torrent_name): {info.name()}")
            print(f"  arg[3] (torrent_path): /deluge/done/{file_path}")
            print()
            print("The path points to the actual file.")
            
        else:
            # Multi-file torrent
            print("=== MULTI-FILE TORRENT ===")
            
            # Get all file paths
            file_paths = []
            for i in range(files.num_files()):
                file_paths.append(files.file_path(i))
            
            # Analyze structure
            root_level_files = []
            subdirectories = set()
            
            for file_path in file_paths:
                path_parts = Path(file_path).parts
                if len(path_parts) == 1:
                    root_level_files.append(file_path)
                else:
                    subdirectories.add(path_parts[0])
            
            print(f"Files at root: {len(root_level_files)}")
            print(f"Subdirectories: {len(subdirectories)}")
            
            if len(subdirectories) == 1 and len(root_level_files) == 0:
                # All files in single directory
                directory_name = list(subdirectories)[0]
                print(f"Structure: Single directory ({directory_name})")
                print(f"Execute plugin would receive:")
                print(f"  arg[1] (torrent_id): {info.info_hash()}")
                print(f"  arg[2] (torrent_name): {info.name()}")
                print(f"  arg[3] (torrent_path): /deluge/done/{directory_name}")
                print()
                print("The path points to the directory containing all files.")
                
            elif len(root_level_files) > 0 and len(subdirectories) == 0:
                # Multiple files at root level
                print("Structure: Multiple files at root level")
                print(f"Execute plugin would receive:")
                print(f"  arg[1] (torrent_id): {info.info_hash()}")
                print(f"  arg[2] (torrent_name): {info.name()}")
                print(f"  arg[3] (torrent_path): /deluge/done")
                print()
                print("The path points to the download directory.")
                print("Individual files would be:")
                for file_path in file_paths:
                    print(f"  /deluge/done/{file_path}")
                    
            elif len(subdirectories) > 1:
                # Multiple directories
                print("Structure: Multiple directories")
                print(f"Execute plugin would receive:")
                print(f"  arg[1] (torrent_id): {info.info_hash()}")
                print(f"  arg[2] (torrent_name): {info.name()}")
                print(f"  arg[3] (torrent_path): /deluge/done")
                print()
                print("The path points to the download directory.")
                print("Subdirectories would be:")
                for directory in sorted(subdirectories):
                    print(f"  /deluge/done/{directory}/")
                    
            else:
                # Mixed structure
                print("Structure: Mixed (files and directories at root)")
                print(f"Execute plugin would receive:")
                print(f"  arg[1] (torrent_id): {info.info_hash()}")
                print(f"  arg[2] (torrent_name): {info.name()}")
                print(f"  arg[3] (torrent_path): /deluge/done")
                print()
                print("The path points to the download directory.")
                print("Items would be:")
                for file_path in root_level_files:
                    print(f"  /deluge/done/{file_path} (file)")
                for directory in sorted(subdirectories):
                    print(f"  /deluge/done/{directory}/ (directory)")
        
        print()
        print("=== KEY INSIGHTS ===")
        print("• Execute plugin ALWAYS passes exactly 3 arguments after script name")
        print("• You will NEVER receive multiple filenames as separate arguments")
        print("• For single files: path points to the file")
        print("• For single-directory torrents: path points to the directory") 
        print("• For complex structures: path points to download root")
        print("• Your script must handle directory traversal if needed")
        
        return True
        
    except Exception as e:
        print(f"Error analyzing torrent: {e}")
        return False


def main():
    if len(sys.argv) != 2:
        print("Deluge Execute Plugin Behavior Analyzer")
        print("=" * 45)
        print("Usage: python3 execute_behavior_analyzer.py <torrent_file>")
        print()
        print("This script analyzes how the Deluge Execute plugin would")
        print("behave with different torrent file structures.")
        sys.exit(1)
    
    torrent_file = sys.argv[1]
    
    if not os.path.exists(torrent_file):
        print(f"Error: File '{torrent_file}' not found")
        sys.exit(1)
    
    success = analyze_execute_behavior(torrent_file)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
