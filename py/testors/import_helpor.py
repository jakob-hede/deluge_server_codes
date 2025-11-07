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


fix_imports()

