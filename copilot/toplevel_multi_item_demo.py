#!/usr/bin/env python3
"""
Mock Toplevel-Multi-Item Torrent Demonstration

This demonstrates what Execute plugin arguments would look like 
for different "toplevel-multi-item" torrent structures.
"""

def demonstrate_toplevel_multi_item_scenarios():
    """Show what Execute plugin would pass for different toplevel-multi-item structures"""
    
    print("TOPLEVEL-MULTI-ITEM TORRENT SCENARIOS")
    print("=" * 50)
    print()
    
    scenarios = [
        {
            "name": "Multiple Files at Root",
            "description": "Album with individual tracks at root level",
            "files": [
                "01 - Track One.mp3",
                "02 - Track Two.mp3", 
                "03 - Track Three.mp3",
                "cover.jpg",
                "album.nfo"
            ]
        },
        {
            "name": "Multiple Directories at Root", 
            "description": "TV series with season directories",
            "files": [
                "Season 1/Episode 01.mkv",
                "Season 1/Episode 02.mkv",
                "Season 2/Episode 01.mkv", 
                "Season 2/Episode 02.mkv",
                "Season 3/Episode 01.mkv"
            ]
        },
        {
            "name": "Mixed Files and Directories",
            "description": "Software package with mixed structure",
            "files": [
                "README.txt",
                "LICENSE",
                "installer.exe",
                "docs/manual.pdf",
                "docs/changelog.txt",
                "src/main.cpp",
                "src/utils.h"
            ]
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"SCENARIO {i}: {scenario['name']}")
        print(f"Description: {scenario['description']}")
        print()
        
        # Mock torrent details
        mock_hash = f"abc123{i:02d}de45f67890abcdef12345678"
        mock_name = scenario['name'].replace(' ', '_').lower()
        
        print("Files in torrent:")
        for file_path in scenario['files']:
            print(f"  {file_path}")
        print()
        
        print("Execute plugin would receive:")
        print(f"  arg[0] (script): /codes/my_script.py")
        print(f"  arg[1] (torrent_id): {mock_hash}")
        print(f"  arg[2] (torrent_name): {mock_name}")
        print(f"  arg[3] (torrent_path): /deluge/done")
        print()
        
        print("After download, the structure would be:")
        for file_path in scenario['files']:
            print(f"  /deluge/done/{file_path}")
        print()
        
        print("Key points:")
        print("• You get /deluge/done as the path (not individual files)")
        print("• You must scan the directory to find all downloaded content")
        print("• Files/dirs are scattered - no single container directory")
        print("• This structure can cause conflicts if download dir has other content")
        print()
        print("-" * 60)
        print()


def show_execute_handling_code():
    """Show how to handle toplevel-multi-item in Execute plugin script"""
    
    print("HANDLING TOPLEVEL-MULTI-ITEM IN EXECUTE SCRIPTS")
    print("=" * 50)
    print()
    
    code = '''#!/usr/bin/env python3
import sys
import os
from pathlib import Path

def handle_execute_completion():
    if len(sys.argv) != 4:
        print("Error: Expected 3 arguments from Execute plugin")
        return
    
    torrent_id = sys.argv[1]
    torrent_name = sys.argv[2] 
    torrent_path = sys.argv[3]
    
    path_obj = Path(torrent_path)
    
    if path_obj.is_file():
        # Single file torrent
        print(f"Processing single file: {torrent_path}")
        process_single_file(torrent_path)
        
    elif path_obj.is_dir():
        # Could be single-directory or toplevel-multi-item
        contents = list(path_obj.iterdir())
        
        # Check if this looks like a single-directory torrent
        # (one subdirectory with same/similar name as torrent)
        potential_single_dir = None
        for item in contents:
            if item.is_dir() and item.name in torrent_name:
                potential_single_dir = item
                break
        
        if potential_single_dir and len(contents) == 1:
            # Likely single-directory torrent
            print(f"Processing single-directory torrent: {potential_single_dir}")
            process_directory(potential_single_dir)
        else:
            # Likely toplevel-multi-item torrent
            print(f"Processing toplevel-multi-item torrent in: {torrent_path}")
            print(f"Found {len(contents)} items:")
            
            for item in contents:
                item_type = "DIR" if item.is_dir() else "FILE"
                print(f"  [{item_type}] {item.name}")
                
            # Process each item
            for item in contents:
                if item.is_file():
                    process_single_file(item)
                elif item.is_dir():
                    process_directory(item)

def process_single_file(file_path):
    print(f"Processing file: {file_path}")
    # Your file processing logic here
    
def process_directory(dir_path):
    print(f"Processing directory: {dir_path}")
    # Your directory processing logic here
    # You can recursively scan for files if needed

if __name__ == '__main__':
    handle_execute_completion()
'''
    
    print("Sample Execute plugin script to handle all torrent structures:")
    print()
    print(code)


def main():
    demonstrate_toplevel_multi_item_scenarios()
    show_execute_handling_code()


if __name__ == '__main__':
    main()
