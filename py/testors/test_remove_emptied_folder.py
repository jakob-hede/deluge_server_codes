#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
import tempfile
from pathlib import Path
import executin.torrentor as torrentor_module
from executin.announcor import HookAnnouncor
from executin.torrentor import Torrentor


class Testor:
    # what Jellyfin, the sidecars and a remove with data leave behind in a movie folder
    leftovers: list[str] = ['backdrop.jpg', 'folder.jpg', 'landscape.jpg', 'logo.png', 'movie.nfo', 'provenance.yml',
                            'Subs/English.srt']

    def __init__(self):
        super().__init__()
        self.torrentor = Torrentor('0123456789abcdef0123456789abcdef01234567', 'the.florist.2026', '/ocean/video/movies/movin')
        self.base: Path = Path()
        self.library: Path = Path()
        self.all_as_expected = True

    def lay_out(self, folder: Path, paths: list[str]) -> Path:
        for path in paths:
            file = folder / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b'magnetics')
        return folder

    def judge(self, folder: Path, expected: bool, exists_expected: dict[Path, bool], outcome: str,
              leftovers: int | None = None, diversions: tuple[str, ...] = (), top: int = 3):
        result = self.torrentor.remove_emptied_folder(folder, self.library, top=top)
        is_as_expected = result == expected
        print(f"result: {result}  expected {expected}")
        for path, expected_exists in exists_expected.items():
            exists = path.exists() or path.is_symlink()
            is_as_expected = is_as_expected and exists == expected_exists
            print(f"exists '{path.relative_to(self.base)}': {exists}  expected {expected_exists}")
        # what the removed message will say: the outcome in the log line's words, the count, the diversions
        print(f"outcome: {self.torrentor.remove_outcome!r}  expected {outcome!r}")
        print(f"leftovers: {self.torrentor.remove_leftovers}  expected {leftovers}")
        print(f"diversions: {self.torrentor.announcor.diversions}  expected {list(diversions)}")
        is_as_expected = (is_as_expected
                          and self.torrentor.remove_outcome == outcome
                          and self.torrentor.remove_leftovers == leftovers
                          and self.torrentor.announcor.diversions == list(diversions))
        print(f"as expected: {is_as_expected}")
        self.all_as_expected = self.all_as_expected and is_as_expected

    def case_leftovers_only(self):
        folder = self.lay_out(self.library / 'the.florist.2026', self.leftovers)
        self.judge(folder, True, {folder: False, self.library: True}, 'deleted with 7 files', 7)

    def case_video_at_root(self):
        folder = self.lay_out(self.library / 'the.florist.2026', self.leftovers + ['the.florist.2026.mkv'])
        self.judge(folder, False, {folder: True}, 'kept, video still present after 3 rounds')

    def case_video_in_subs(self):
        folder = self.lay_out(self.library / 'the.florist.2026', self.leftovers + ['Subs/clip.MKV'])
        self.judge(folder, False, {folder: True}, 'kept, video still present after 3 rounds')

    def case_library_itself(self):
        self.lay_out(self.library, self.leftovers)
        self.judge(self.library, False, {self.library / 'movie.nfo': True}, 'refused: it is the library itself')

    def case_outside_library(self):
        folder = self.lay_out(self.base / 'elsewhere' / 'the.florist.2026', self.leftovers)
        self.judge(folder, False, {folder: True}, f'refused: its download location is outside **{self.library}**')

    def case_not_existing(self):
        self.library.mkdir(parents=True, exist_ok=True)
        folder = self.library / 'the.florist.2026'
        self.judge(folder, False, {folder: False}, 'refused: it does not exist')

    def case_symlink_to_outside(self):
        outside = self.lay_out(self.base / 'outside' / 'the.florist.2026', self.leftovers)
        self.library.mkdir(parents=True, exist_ok=True)
        folder = self.library / 'the.florist.2026'
        folder.symlink_to(outside, target_is_directory=True)
        self.judge(folder, False, {folder: True, outside / 'movie.nfo': True}, 'refused: it is a symlink')

    def case_not_a_directory(self):
        folder = self.lay_out(self.library, ['the.florist.2026']) / 'the.florist.2026'
        self.judge(folder, False, {folder: True}, 'refused: it is not a directory')

    def case_video_vanishes(self):
        folder = self.lay_out(self.library / 'the.florist.2026', self.leftovers + ['the.florist.2026.mkv'])
        video = folder / 'the.florist.2026.mkv'
        sleep_calls: list[float] = []

        # stands in for libtorrent's disk thread: the video is gone after the second round's sleep
        def sleeper(seconds: float):
            sleep_calls.append(seconds)
            if len(sleep_calls) == 2:
                video.unlink()

        real_sleep = torrentor_module.sleep
        torrentor_module.sleep = sleeper
        try:
            self.judge(folder, True, {folder: False}, 'deleted with 7 files', 7, top=5)
        finally:
            torrentor_module.sleep = real_sleep
        print(f"sleeps: {len(sleep_calls)}")

    def case_folder_vanishes(self):
        folder = self.lay_out(self.library / 'the.florist.2026', self.leftovers + ['the.florist.2026.mkv'])

        # stands in for a hand deleting the whole folder during the wait
        def sleeper(seconds: float):
            if folder.exists():
                torrentor_module.shutil.rmtree(folder)

        real_sleep = torrentor_module.sleep
        torrentor_module.sleep = sleeper
        try:
            self.judge(folder, False, {folder: False}, 'gone already')
        finally:
            torrentor_module.sleep = real_sleep

    def case_deletion_fails(self):
        folder = self.lay_out(self.library / 'the.florist.2026', self.leftovers)

        # stands in for a deletion the filesystem refuses half way, whoever runs the testor
        def failing_rmtree(path, *args, **kwargs):
            raise PermissionError(13, 'Permission denied', str(Path(path) / 'Subs'))

        real_rmtree = torrentor_module.shutil.rmtree
        torrentor_module.shutil.rmtree = failing_rmtree
        try:
            self.judge(folder, False, {folder: True},
                       f"error: **[Errno 13] Permission denied: '{folder / 'Subs'}'**",
                       diversions=("deletion failed, **the.florist.2026/** left for the operator's hand",))
        finally:
            torrentor_module.shutil.rmtree = real_rmtree

    def case_double_wrapped(self):
        parent = self.library / 'moonrise.kingdom.2012'
        folder = self.lay_out(parent / 'Moonrise Kingdom (2012) Criterion (2160p)', self.leftovers)
        self.judge(folder, True, {folder: False, parent: True}, 'deleted with 7 files', 7,
                   diversions=("parent **moonrise.kingdom.2012/** holds no video, left for the operator's hand",))

    def case_climbing_path(self):
        self.lay_out(self.library / 'the.florist.2026', self.leftovers)
        (self.base / 'downloads').mkdir()
        folder = self.base / 'downloads' / '..' / 'movin' / 'the.florist.2026'
        self.judge(folder, False, {self.library / 'the.florist.2026': True}, 'refused: its path climbs with **..**')

    def case_inner_symlink_to_outside_video(self):
        outside = self.lay_out(self.base / 'outside', ['other.mkv'])
        folder = self.lay_out(self.library / 'the.florist.2026', self.leftovers)
        (folder / 'linked').symlink_to(outside, target_is_directory=True)
        self.judge(folder, True, {folder: False, outside / 'other.mkv': True}, 'deleted with 8 files', 8)

    def executize(self):
        print("Testor.executize...")
        cases = [
            ('leftovers only', self.case_leftovers_only),
            ('a video at the root', self.case_video_at_root),
            ('a video only inside Subs/', self.case_video_in_subs),
            ('the library itself', self.case_library_itself),
            ('a folder outside the library', self.case_outside_library),
            ('a folder that does not exist', self.case_not_existing),
            ('a symlink in the library to a folder outside', self.case_symlink_to_outside),
            ('a video that vanishes after two rounds', self.case_video_vanishes),
            ('the double-wrapped shape, the inner folder emptied', self.case_double_wrapped),
            ('a path climbing into the library with ..', self.case_climbing_path),
            ('leftovers and a symlink to a folder outside holding a video', self.case_inner_symlink_to_outside_video),
            ('a file where the folder should be', self.case_not_a_directory),
            ('the folder vanishes during the wait', self.case_folder_vanishes),
            ('the deletion fails', self.case_deletion_fails),
        ]
        for case_name, case in cases:
            print(f"--- {case_name}")
            # a fresh voice per case, so each case's diversions are its own
            self.torrentor.announcor = HookAnnouncor(self.torrentor.logger)
            with tempfile.TemporaryDirectory(prefix='test_remove_emptied_folder_') as temp_dir:
                self.base = Path(temp_dir)
                self.library = self.base / 'movin'
                case()
        print(f"all as expected: {self.all_as_expected}")


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
