import sys
from pathlib import Path


def fix_imports():
    """
    If there is no syspath ending with `needle`, add it.
    Find the dir `/needle` by traversing up from this file's location.
    """
    needle = 'py'

    for path in sys.path:
        # print(f' - "{path}"')
        if path.endswith(f'/{needle}'):
            print(f'import_helpor: Found ".../{needle}" in sys.path, no need to modify.')
            return

    # print(f"'...{needle}/' not found in sys.path, attempting to add it...")

    this_file = Path(__file__).resolve()
    for parent_dir in this_file.parents:
        # print(f' - parent dir: "{parent_dir}"')
        if parent_dir.name == needle:
            py_dir = parent_dir
            if str(py_dir) not in sys.path:
                sys.path.insert(0, str(py_dir))
                # sys.path.append(str(py_dir))
                print(f'import_helpor: Inserted "{py_dir}" in sys.path')
            else:
                print(f'import_helpor: "{py_dir}" already in sys.path')
            break


def fix_ntfying_imports():
    """
    Put the ntfying package's `src` dir on sys.path, right after the `py` dir, for the hook's announcor.
    The ntfy_client repo is cloned once per host: on media-docker nested in this repo's clone and ignored
    by it (`/codes/ntfy_client/src` in the container), on the dev box beside this repo's clone. The first
    of the two that exists is added; with neither, the announcor refuses with one warning, the hook goes on.
    """
    needle = 'py'

    this_file = Path(__file__).resolve()
    for parent_dir in this_file.parents:
        if parent_dir.name == needle:
            py_dir = parent_dir
            for ntfying_dir in (py_dir.parent / 'ntfy_client' / 'src', py_dir.parent.parent / 'ntfy_client' / 'src'):
                if not ntfying_dir.is_dir():
                    continue
                if str(ntfying_dir) not in sys.path:
                    index = sys.path.index(str(py_dir)) + 1 if str(py_dir) in sys.path else len(sys.path)
                    sys.path.insert(index, str(ntfying_dir))
                    print(f'import_helpor: Inserted "{ntfying_dir}" in sys.path')
                else:
                    print(f'import_helpor: "{ntfying_dir}" already in sys.path')
                break
            break


fix_imports()
fix_ntfying_imports()

