#!/usr/bin/env python3
"""
Torrent Structure Analyzer

Analyzes the file structure of torrents to determine if files are wrapped
in a top-level directory or scattered at the root level.
"""

import libtorrent as lt
import sys
import os
from pathlib import Path


def analyze_torrent_structure(torrent_path):
    """Analyze the file structure of a torrent"""
    try:
        info = lt.torrent_info(torrent_path)
        files = info.files()
        
        print(f"Analyzing: {info.name()}")
        print(f"Number of files: {info.num_files()}")
        print()
        
        if info.num_files() == 1:
            print("SINGLE FILE TORRENT:")
            print(f"  File: {files.file_path(0)}")
            print("  Structure: Single file (no directory wrapping)")
            return "single_file"
        
        # Multi-file torrent analysis
        print("MULTI-FILE TORRENT STRUCTURE:")
        
        # Get all file paths
        file_paths = []
        for i in range(files.num_files()):
            file_paths.append(files.file_path(i))
        
        # Analyze directory structure
        root_level_files = []
        subdirectories = set()
        
        for file_path in file_paths:
            path_parts = Path(file_path).parts
            
            if len(path_parts) == 1:
                # File at root level
                root_level_files.append(file_path)
            else:
                # File in subdirectory
                subdirectories.add(path_parts[0])
        
        print(f"  Files at root level: {len(root_level_files)}")
        print(f"  Top-level directories: {len(subdirectories)}")
        
        # Determine structure type
        if len(root_level_files) > 0 and len(subdirectories) > 0:
            structure_type = "mixed"
            print("  Structure Type: MIXED (files and directories at root)")
        elif len(root_level_files) > 0:
            structure_type = "root_files"
            print("  Structure Type: ROOT FILES (multiple files at root level)")
        elif len(subdirectories) == 1:
            structure_type = "single_directory"
            print("  Structure Type: SINGLE DIRECTORY (all files in one directory)")
        else:
            structure_type = "multiple_directories"
            print("  Structure Type: MULTIPLE DIRECTORIES (files spread across directories)")
        
        print()
        print("DETAILED BREAKDOWN:")
        
        if root_level_files:
            print(f"  Root level files ({len(root_level_files)}):")
            for file_path in root_level_files[:10]:  # Show first 10
                print(f"    {file_path}")
            if len(root_level_files) > 10:
                print(f"    ... and {len(root_level_files) - 10} more")
        
        if subdirectories:
            print(f"  Top-level directories ({len(subdirectories)}):")
            for directory in sorted(subdirectories):
                # Count files in this directory
                files_in_dir = sum(1 for fp in file_paths if fp.startswith(directory + '/'))
                print(f"    {directory}/ ({files_in_dir} files)")
        
        print()
        print("SAMPLE FILE PATHS:")
        for i, file_path in enumerate(file_paths[:5]):
            print(f"  {i+1}. {file_path}")
        if len(file_paths) > 5:
            print(f"  ... and {len(file_paths) - 5} more files")
        
        print()
        print("EXACT DOWNLOAD PATHS (what Execute plugin would create):")
        print("Base download path: /deluge/done")
        for i, file_path in enumerate(file_paths[:10]):
            full_path = f"/deluge/done/{file_path}"
            file_size = files.file_size(i)
            print(f"  {full_path} ({file_size:,} bytes)")
        if len(file_paths) > 10:
            print(f"  ... and {len(file_paths) - 10} more files")
        
        return structure_type
        
    except Exception as e:
        print(f"Error analyzing torrent: {e}")
        return "error"


def main():
    if len(sys.argv) != 2:
        print("Torrent Structure Analyzer")
        print("=" * 40)
        print("Usage: python3 torrent_structure_analyzer.py <torrent_file>")
        print()
        print("This script analyzes torrent file structure to determine:")
        print("  - Single file vs multi-file torrents")
        print("  - Whether multi-file torrents use a top-level directory")
        print("  - Mixed structures (files and dirs at root)")
        print()
        print("Possible structure types:")
        print("  - single_file: One file only")
        print("  - single_directory: All files in one top-level directory")
        print("  - multiple_directories: Files spread across multiple directories")
        print("  - root_files: Multiple files at root level (no directories)")
        print("  - mixed: Both files and directories at root level")
        sys.exit(1)
    
    torrent_file = sys.argv[1]
    
    if not os.path.exists(torrent_file):
        print(f"Error: File '{torrent_file}' not found")
        sys.exit(1)
    
    structure_type = analyze_torrent_structure(torrent_file)
    
    print("=" * 60)
    print("SUMMARY:")
    print(f"Structure Type: {structure_type.upper().replace('_', ' ')}")
    
    if structure_type == "single_file":
        print("This is a single-file torrent.")
    elif structure_type == "single_directory":
        print("All files are contained within a single top-level directory.")
    elif structure_type == "multiple_directories":
        print("Files are organized in multiple top-level directories.")
    elif structure_type == "root_files":
        print("Multiple files exist at the root level without directory wrapping.")
    elif structure_type == "mixed":
        print("WARNING: Mixed structure with both files and directories at root!")
        print("This can cause extraction conflicts and is generally poor practice.")


if __name__ == '__main__':
    main()
