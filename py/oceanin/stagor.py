from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    type RenamePlan = tuple[str, str] | list[tuple[int, str]]


class Stagor:
    """
    Where one torrent's completion chain stands: /deluge/staging/<hash>/stage.yml, written by each link of the chain
    as it ends, and stage.lock beside it, held exclusive around every link's read, decision, act and write, so the
    hook runs the daemon wakes side by side, a folder's file renames among them, take their turns. The directory stays
    after the chain is done, the guard against a repeated torrent_finished at a daemon start. yaml and fcntl are
    imported where they act.
    """

    file_name: ClassVar[str] = 'stage.yml'
    lock_name: ClassVar[str] = 'stage.lock'
    # in the chain's order, then the two ends outside it: no label to act on, a failure
    stages: ClassVar[tuple[str, ...]] = ('entered', 'staging', 'renaming', 'renaming_files', 'moving', 'done',
                                         'unlabelled', 'failed')
    # naming: how the folder came by its name, renamed by the chain, already in its pattern folder, or as released;
    # alternate_ids: a hybrid's v1 hash when the daemon files it under its v2, kept from oce_added to find the click's
    # record by
    keys: ClassVar[tuple[str, ...]] = ('stage', 'entry', 'label', 'destination', 'pattern_dir_name',
                                       'release_name', 'naming', 'alternate_ids', 'rename_plan', 'file_plan', 'notes',
                                       'started', 'updated')
    namings: ClassVar[tuple[str, ...]] = ('renamed', 'already', 'as_released')
    plan_keys: ClassVar[tuple[str, ...]] = ('rename_plan', 'file_plan')

    def __init__(self, torrent_id: str, staging_dir: Path | None = None):
        super().__init__()
        self.torrent_id = torrent_id
        self.staging_dir = self.default_staging_dir() if staging_dir is None else staging_dir

    @staticmethod
    def default_staging_dir() -> Path:
        from executin.commons import Commons

        return Commons.singleton.deluge_root_dir / 'staging'

    @property
    def stage_dir(self) -> Path:
        return self.staging_dir / self.torrent_id

    @property
    def stage_file(self) -> Path:
        return self.stage_dir / self.file_name

    @property
    def lock_file(self) -> Path:
        return self.stage_dir / self.lock_name

    @property
    def exists(self) -> bool:
        return self.stage_file.exists()

    @contextmanager
    def held(self) -> Iterator[Stagor]:
        # the lock is the file's, flocked: released by the kernel when the process ends, a crashed link included
        import fcntl

        self.stage_dir.mkdir(parents=True, exist_ok=True)
        with open(self.lock_file, 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield self
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def read(self) -> dict[str, Any]:
        """The stage as it stands, its plans in the handlor's shapes; {} when the chain has not entered."""
        import yaml

        if not self.exists:
            return {}
        data = yaml.safe_load(self.stage_file.read_text()) or {}
        return {key: self.plan_out(value) if key in self.plan_keys else value for key, value in data.items()}

    def write(self, **changes: Any) -> dict[str, Any]:
        """The stage with the changes made, started and updated stamped, written whole in one rename; returned."""
        import yaml

        unknown = [key for key in changes if key not in self.keys]
        if unknown:
            raise ValueError(f'stage keys {unknown} are not among {list(self.keys)}')
        if 'stage' in changes and changes['stage'] not in self.stages:
            raise ValueError(f"stage '{changes['stage']}' is not among {list(self.stages)}")
        stamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
        data = {**self.read(), **changes}
        data.setdefault('started', stamp)
        data['updated'] = stamp
        record = {key: self.plan_in(data[key]) if key in self.plan_keys else data[key]
                  for key in self.keys if key in data}
        self.stage_dir.mkdir(parents=True, exist_ok=True)
        tmp_file = self.stage_dir / f'.{self.file_name}.{os.getpid()}.tmp'
        tmp_file.write_text(yaml.safe_dump(record, sort_keys=False, allow_unicode=True))
        os.replace(tmp_file, self.stage_file)
        return data

    @staticmethod
    def plan_in(plan: RenamePlan | None) -> dict[str, str] | list[list[int | str]] | None:
        # a folder plan, the handlor's (folder, new_folder) tuple, as a mapping; a files plan, its [(index, new path)]
        # list, as pairs; so the file reads plainly and yaml's safe dump, which has no tuple, takes both
        if isinstance(plan, tuple):
            folder, new_folder = plan
            return {'folder': folder, 'new_folder': new_folder}
        if plan is None:
            return None
        return [[index, path] for index, path in plan]

    @staticmethod
    def plan_out(record: Any) -> RenamePlan | None:
        if isinstance(record, dict):
            return record['folder'], record['new_folder']
        if record is None:
            return None
        return [(int(index), str(path)) for index, path in record]
