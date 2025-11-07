"""
Deluge Daemon API Client

A proper implementation for communicating with Deluge daemon using its native RPC protocol.
This works with both local daemon and web UI, depending on configuration.
"""

import json
import base64
import socket
# import requests
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import logging
import subprocess
from subprocess import CompletedProcess

from Salaisuudet.secrets import Secretor


class DelugeRPCError(Exception):
    """Exception raised for Deluge RPC errors"""
    pass


class DelugeConsoleAPI:

    def __init__(self):
        self.console_bin = '/usr/bin/deluge-console'
        mediator = Secretor.mediator
        self.user = mediator['username']
        self.password = mediator['password']
        # self.user = 'sermin'
        # self.password = 'xyz'
        self.ip = '127.0.0.1'
        self.port = '58846'

    def run_command(self, command: str) -> CompletedProcess:
        """Run deluge-console command and return output"""
        try:
            cp = subprocess.run(
                [
                    self.console_bin,
                    '-d', self.ip,
                    '-p', self.port,
                    '-U', self.user,
                    '-P', self.password,
                    command
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            # if result.returncode != 0:
            #     raise DelugeRPCError(f"Console command failed: {result.stderr}")


        except subprocess.TimeoutExpired:
            raise DelugeRPCError("Console command timed out")
        except FileNotFoundError:
            raise DelugeRPCError(f"deluge-console not found at {self.console_bin}")

        return cp

    def info(self, torrent_id: str = None) -> str:
        """Get torrent info"""
        cmd = "info" if torrent_id is None else f"info {torrent_id}"
        cp = self.run_command(cmd)
        txt = cp.stdout.strip()
        return txt

    # def _run_console_command(self, command: str) -> str:
    #     """Run deluge-console command and return output"""
    #
    #     try:
    #         result = subprocess.run(
    #             [self.console_path, command],
    #             capture_output=True,
    #             text=True,
    #             timeout=30
    #         )
    #
    #         if result.returncode != 0:
    #             raise DelugeRPCError(f"Console command failed: {result.stderr}")
    #
    #         return result.stdout.strip()
    #
    #     except subprocess.TimeoutExpired:
    #         raise DelugeRPCError("Console command timed out")
    #     except FileNotFoundError:
    #         raise DelugeRPCError(f"deluge-console not found at {self.console_path}")
    #
    # def info(self, torrent_id: str = None) -> str:
    #     """Get torrent info"""
    #     cmd = "info" if torrent_id is None else f"info {torrent_id}"
    #     return self._run_console_command(cmd)


def main():
    print('main')

    api = DelugeConsoleAPI()
    response = api.info()
    print(response)


# Example usage for Execute plugin
if __name__ == "__main__":
    main()

'''
127.0.0.1:58846

root@93d6ed90a128:/# deluge-console --help
/usr/lib/python3.12/site-packages/deluge/ui/ui_entry.py:20: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
  import pkg_resources
usage: deluge-console [-h] [-V] [-c <config>] [-l <logfile>] [-L <level>]
                      [--logrotate [<max-size>]] [-q] [--profile [<profile-file>]]
                      [-d <ip_addr>] [-p <port>] [-U <user>] [-P <pass>]
                      Command ...

Starts the Deluge console interface

Common Options:
  -h, --help                  Print this help message
  -V, --version               Print version information
  -c, --config <config>       Set the config directory path
  -l, --logfile <logfile>     Output to specified logfile instead of stdout
  -L, --loglevel <level>      Set the log level (none, error, warning, info, debug)
  --logrotate [<max-size>]    Enable logfile rotation, with optional maximum logfile size,
                                default: 2M (Logfile rotation count is 5)
  -q, --quiet                 Quieten logging output (Same as `--loglevel none`)
  --profile [<profile-file>]  Profile deluge-console with cProfile. Outputs to stdout
                                unless a filename is specified

Console Options:
  These daemon connect options will be used for commands, or if console ui autoconnect is enabled.

  -d, --daemon <ip_addr>      Deluge daemon IP address to connect to (default 127.0.0.1)
  -p, --port <port>           Deluge daemon port to connect to (default 58846)
  -U, --username <user>       Deluge daemon username to use when connecting
  -P, --password <pass>       Deluge daemon password to use when connecting

Console Commands:
  The following console commands are available:

  Command                     Description
    add                       Add torrents
    cache                     Show information about the disk cache
    config                    Show and set configuration values
    connect                   Connect to a new deluge server
    debug                     Enable and disable debugging
    del                       `rm` alias
    exit                      `quit` alias
    gui                       Enable interactive mode
    halt                      Shutdown the deluge server.
    help                      Displays help on other commands
    info                      Show information about the torrents
    manage                    Show and manage per-torrent options
    move                      Move torrents' storage location
    pause                     Pause torrents
    plugin                    Manage plugins
    quit                      Exit the client
    reannounce                `update_tracker` alias
    recheck                   Forces a recheck of the torrent data
    resume                    Resume torrents
    rm                        Remove a torrent
    status                    Shows various status information from the daemon
    update_tracker            Update tracker for torrent(s)

'''
