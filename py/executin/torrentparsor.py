from pathlib import Path
import libtorrent as lt  # noqa
import os
import datetime
from typing import List, Dict, Optional
from enum import Enum


class TorrentStructureType(Enum):
    """Enum for different torrent structure types"""
    SINGLE_FILE = "single_file"
    SINGLE_DIRECTORY = "single_directory"
    MULTIPLE_DIRECTORIES = "multiple_directories"
    ROOT_FILES = "root_files"
    MIXED = "mixed"


class TorrentParsor:
    """Enhanced torrent file parser with comprehensive analysis capabilities"""
    
    def __init__(self, torrent_file: Path):
        self.torrent_file: Path = torrent_file
        self._torrent_info: Optional[lt.torrent_info] = None
        self._files: Optional[lt.file_storage] = None
        super().__init__()

    @property
    def torrent_info(self) -> lt.torrent_info:
        """Lazy load torrent info to avoid repeated file reads"""
        if self._torrent_info is None:
            self._torrent_info = lt.torrent_info(str(self.torrent_file))
        return self._torrent_info

    @property
    def files(self) -> lt.file_storage:
        """Get the file storage object"""
        if self._files is None:
            self._files = self.torrent_info.files()
        return self._files

    @property
    def name(self) -> str:
        """Get torrent name"""
        return self.torrent_info.name()

    @property
    def info_hash(self) -> str:
        """Get torrent info hash"""
        return str(self.torrent_info.info_hash())

    @property
    def total_size(self) -> int:
        """Get total size in bytes"""
        return self.torrent_info.total_size()

    @property
    def num_files(self) -> int:
        """Get number of files"""
        return self.torrent_info.num_files()

    @property
    def piece_length(self) -> int:
        """Get piece length in bytes"""
        return self.torrent_info.piece_length()

    @property
    def num_pieces(self) -> int:
        """Get number of pieces"""
        return self.torrent_info.num_pieces()

    @property
    def creation_date(self) -> Optional[datetime.datetime]:
        """Get creation date as datetime object"""
        timestamp = self.torrent_info.creation_date()
        return datetime.datetime.fromtimestamp(timestamp) if timestamp else None

    @property
    def creator(self) -> Optional[str]:
        """Get creator string"""
        creator = self.torrent_info.creator()
        return creator if creator else None

    @property
    def comment(self) -> Optional[str]:
        """Get comment string"""
        comment = self.torrent_info.comment()
        return comment if comment else None

    @property
    def is_private(self) -> bool:
        """Check if torrent is private"""
        return self.torrent_info.priv()

    @property
    def trackers(self) -> List[Dict[str, any]]:
        """Get list of trackers with their details"""
        tracker_list = []
        for tracker in list(self.torrent_info.trackers()):
            tracker_info = {
                'url': tracker.url,
                'tier': getattr(tracker, 'tier', 0)
            }
            tracker_list.append(tracker_info)
        return tracker_list

    def format_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def get_structure_type(self) -> TorrentStructureType:
        """Analyze and return the torrent structure type"""
        if self.num_files == 1:
            return TorrentStructureType.SINGLE_FILE

        # Analyze multi-file structure
        root_level_files = []
        subdirectories = set()

        for i in range(self.num_files):
            file_path = self.files.file_path(i)
            path_parts = Path(file_path).parts

            if len(path_parts) == 1:
                root_level_files.append(file_path)
            else:
                subdirectories.add(path_parts[0])

        if len(root_level_files) > 0 and len(subdirectories) > 0:
            return TorrentStructureType.MIXED
        elif len(root_level_files) > 0:
            return TorrentStructureType.ROOT_FILES
        elif len(subdirectories) == 1:
            return TorrentStructureType.SINGLE_DIRECTORY
        else:
            return TorrentStructureType.MULTIPLE_DIRECTORIES

    def get_file_manifest(self, download_base: str = "/deluge/completed") -> List[Dict[str, any]]:
        """Get complete file manifest with absolute paths"""
        file_manifest = []

        for i in range(self.num_files):
            relative_path = self.files.file_path(i)
            file_size = self.files.file_size(i)
            absolute_path = os.path.join(download_base, relative_path)

            file_info = {
                'index': i,
                'relative_path': relative_path,
                'absolute_path': absolute_path,
                'size': file_size,
                'size_formatted': self.format_size(file_size),
                'directory': os.path.dirname(absolute_path),
                'filename': os.path.basename(absolute_path)
            }
            file_manifest.append(file_info)

        return file_manifest

    def predict_execute_path(self, download_base: str = "/deluge/completed") -> str:
        """Predict what path the Execute plugin would provide"""
        structure_type = self.get_structure_type()

        if structure_type == TorrentStructureType.SINGLE_FILE:
            return os.path.join(download_base, self.files.file_path(0))
        elif structure_type == TorrentStructureType.SINGLE_DIRECTORY:
            # Find the single directory name
            first_file_path = self.files.file_path(0)
            directory_name = Path(first_file_path).parts[0]
            return os.path.join(download_base, directory_name)
        else:
            # Multiple items at root or mixed structure
            return download_base

    def get_structure_analysis(self) -> Dict[str, any]:
        """Get detailed structure analysis"""
        structure_type = self.get_structure_type()
        analysis = {
            'structure_type': structure_type.value,
            'is_single_file': structure_type == TorrentStructureType.SINGLE_FILE,
            'is_well_structured': structure_type in [TorrentStructureType.SINGLE_FILE, TorrentStructureType.SINGLE_DIRECTORY],
            'has_root_files': structure_type in [TorrentStructureType.ROOT_FILES, TorrentStructureType.MIXED],
            'num_files': self.num_files,
            'total_size': self.total_size,
            'total_size_formatted': self.format_size(self.total_size)
        }

        if structure_type != TorrentStructureType.SINGLE_FILE:
            root_files = []
            directories = set()

            for i in range(self.num_files):
                file_path = self.files.file_path(i)
                path_parts = Path(file_path).parts

                if len(path_parts) == 1:
                    root_files.append(file_path)
                else:
                    directories.add(path_parts[0])

            analysis.update({
                'root_files_count': len(root_files),
                'directories_count': len(directories),
                'root_files': root_files[:10],  # Limit to first 10
                'directories': sorted(list(directories))
            })

        return analysis

    def parse(self) -> Dict[str, any]:
        """Parse torrent file and return comprehensive information"""
        file_manifest = self.get_file_manifest()
        structure_analysis = self.get_structure_analysis()

        data = {
            # Basic info (keeping your original structure)
            'name': self.name,
            'info_hash': self.info_hash,
            'num_files': self.num_files,
            'files': [
                {
                    'index': i,
                    'path': self.files.file_path(i),
                    'size': self.files.file_size(i)
                }
                for i in range(self.num_files)
            ],
            
            # Enhanced analysis
            'total_size': self.total_size,
            'total_size_formatted': self.format_size(self.total_size),
            'piece_length': self.piece_length,
            'num_pieces': self.num_pieces,
            'creation_date': self.creation_date.isoformat() if self.creation_date else None,
            'creator': self.creator,
            'comment': self.comment,
            'is_private': self.is_private,
            'trackers': self.trackers,
            'structure': structure_analysis,
            'file_manifest': file_manifest,
            'predicted_execute_path': self.predict_execute_path()
        }

        return data

    def __str__(self) -> str:
        """String representation of the torrent"""
        return f"TorrentParsor({self.name}, {self.num_files} files, {self.format_size(self.total_size)})"

    def __repr__(self) -> str:
        """Detailed representation"""
        return f"TorrentParsor(file={self.torrent_file}, hash={self.info_hash})"

