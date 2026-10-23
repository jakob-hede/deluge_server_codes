#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
import os
import re
import subprocess
import sys
from pathlib import Path

# the child imports Commons, which is built once at import, and prints the three addresses; the type of the port too
CHILD = '\n'.join((
    'import import_helpor',
    'from executin.commons import Commons',
    'commons = Commons.singleton',
    "print('addresses', repr(commons.deluged_host), repr(commons.deluged_port), type(commons.deluged_port).__name__,",
    '      repr(commons.jellyfin_url))',
))
NAMES = ('MAGNETICS_DELUGED_HOST', 'MAGNETICS_DELUGED_PORT', 'MAGNETICS_JELLYFIN_URL')


class Testor:
    # a DelugApi prints its password when it is built; the child's output is filtered as every capture here
    password_line = re.compile(r'^(DelugApi [^,]*,[^,]*,[^,]*),.*$', re.MULTILINE)
    defaults = "addresses '10.4.9.12' 58846 int 'http://10.4.9.11:8096'"

    def __init__(self):
        super().__init__()
        self.all_as_expected = True

    def run_child(self, environ: dict[str, str]) -> tuple[int, str, str]:
        # the testor's own environment, every MAGNETICS_ variable of ours struck, then the case's
        env = {name: value for name, value in os.environ.items() if name not in NAMES}
        env.update(environ)
        completed = subprocess.run([sys.executable, '-c', CHILD], cwd=Path(__file__).resolve().parent, env=env,
                                   capture_output=True, text=True, timeout=60)
        stdout = self.password_line.sub(r'\1, <REDACTED>', completed.stdout)
        stderr = self.password_line.sub(r'\1, <REDACTED>', completed.stderr)
        return completed.returncode, stdout, stderr

    def judge(self, case: str, environ: dict[str, str], expected: str, *, is_raising: bool = False):
        print(f'--- {case}')
        print(f'environment: {environ}')
        returncode, stdout, stderr = self.run_child(environ)
        if is_raising:
            got = stderr.strip().splitlines()[-1] if stderr.strip() else ''
            is_as_expected = returncode != 0 and got == expected
        else:
            got = next((line for line in stdout.splitlines() if line.startswith('addresses ')), '')
            is_as_expected = returncode == 0 and got == expected
            if returncode:
                print(f'stderr: {stderr.strip().splitlines()[-1:]}')
        print(f'exit: {returncode}  expected {"non-zero" if is_raising else 0}')
        print(f'got:      {got}')
        print(f'expected: {expected}')
        print(f'as expected: {is_as_expected}')
        self.all_as_expected = self.all_as_expected and is_as_expected

    def executize(self) -> int:
        self.judge('no variables: the three defaults, the live box\'s', {}, self.defaults)
        self.judge('all three set: the three overrides, the port an int',
                   {'MAGNETICS_DELUGED_HOST': '10.4.9.99', 'MAGNETICS_DELUGED_PORT': '58847',
                    'MAGNETICS_JELLYFIN_URL': 'http://10.4.9.98:8097'},
                   "addresses '10.4.9.99' 58847 int 'http://10.4.9.98:8097'")
        self.judge('a port that is not an integer: ValueError naming the variable and the value',
                   {'MAGNETICS_DELUGED_PORT': 'not-a-port'},
                   "ValueError: Commons; MAGNETICS_DELUGED_PORT 'not-a-port' is not an integer", is_raising=True)
        self.judge('empty strings: counted as unset, the defaults',
                   {name: '' for name in NAMES}, self.defaults)
        self.judge('a trailing slash on the URL: stripped',
                   {'MAGNETICS_JELLYFIN_URL': 'http://10.4.9.98:8097/'},
                   "addresses '10.4.9.12' 58846 int 'http://10.4.9.98:8097'")
        print('ALL AS EXPECTED' if self.all_as_expected else 'NOT ALL AS EXPECTED')
        return 0 if self.all_as_expected else 1


def main():
    testor = Testor()
    raise SystemExit(testor.executize())


if __name__ == '__main__':
    main()
