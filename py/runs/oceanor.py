#!/usr/bin/env python3
#
# Oceanic's runnor, the one entry under py/runs/. The shim oceanic_plugin/oceanic.sh runs it as
#   oceanor.py oce_<event> <torrent id> <torrent name> <location> [<detail>...]
# and it hands the event to the hook, OceanicHook.process_event, the two logging to oceanic_action.log. Nothing
# here speaks to the daemon, the removal trio's torrents having left it and every other event only logged: from
# executin only the loggor, nothing from delugapi or twisted.
#

import sys
import import_helpor  # noqa NEEDED!!!
from executin.logge import OceanorLoggor
from oceanin.oceanic_hook import OceanicHook


class Oceanor:
    def __init__(self, argv: list[str] | None = None):
        super().__init__()
        self.loggor = OceanorLoggor()
        self.args: list[str] = list(sys.argv[1:] if argv is None else argv)

    def oceanize(self) -> int:
        if len(self.args) < 4:
            self.loggor.error(f'Oceanor.oceanize takes 4 or more arguments, got {len(self.args)}, nothing run: '
                              f'{self.args}')
            return 1
        event_name, torrent_id, torrent_name, base_sdir, *detail = self.args
        self.loggor.debug(f'Oceanor.oceanize: "{event_name}", "{torrent_id}", "{torrent_name}", "{base_sdir}", '
                          f'detail {detail}')
        try:
            result = OceanicHook(torrent_id, torrent_name, base_sdir, self.loggor).process_event(event_name, *detail)
        except Exception as exc:
            # raised on, so the plugin's callback sees the exit code and logs the traceback
            self.loggor.error(f'Oceanor.oceanize "{event_name}" raised {type(exc).__name__}: {exc}')
            raise
        self.loggor.info(f'Oceanor.oceanize "{event_name}" returned {result!r}')
        return 0


def main():
    raise SystemExit(Oceanor().oceanize())


if __name__ == '__main__':
    main()
