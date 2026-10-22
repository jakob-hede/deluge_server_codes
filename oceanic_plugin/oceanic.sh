#!/usr/bin/env bash
#
# Oceanic's one responder, run by the plugin for every event as
#   oceanic.sh <event> <torrent id> <torrent name> <location> [<detail>]
# the detail today the error text of delete_failed. One line appended to oceanic_plugin.log, then oceanor.py
# with oce_<event> and the rest of the arguments; the script's exit code is the Python's. The same script
# runs in the container and on dev.
#

__oce_habitize() {
    # the container's paths first, then the box's log dir, then the dev side's
    log_dir='/deluge/log'
    pyxe='/usr/bin/python'
    py_dir='/codes/py'
    [[ -d ${py_dir} ]] || {
        py_dir='/opt/projects/deluge_source_project/deluge_server_codes/py'
        pyxe='/opt/projects/deluge_source_project/venv/bin/python3'
    }
    [[ -d ${log_dir} ]] || log_dir='/mnt/btrfs_data/deluge/log'
    [[ -d ${log_dir} ]] || log_dir='/opt/projects/deluge_source_project/log/exelog'
    [[ -d ${log_dir} ]] || {
        printf 'oceanic.sh: no log dir, the last tried %s\n' "${log_dir}" >&2
        return 1
    }
}

__oce_stamp() {
    # local time to the millisecond, as torrentor.log and the plugin's log are stamped; whole seconds without
    # EPOCHREALTIME, whose separator is the locale's, a comma under en_DK
    if [[ ${EPOCHREALTIME:-} =~ ^([0-9]+)[.,]([0-9]{3}) ]]; then
        printf -v stamp '%(%Y-%m-%d %H:%M:%S)T,%s' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
    else
        printf -v stamp '%(%Y-%m-%d %H:%M:%S)T' -1
    fi
}

_oce_respond() {
    declare log_dir pyxe py_dir stamp
    __oce_habitize || return 1
    __oce_stamp
    declare event="$1" quoted
    printf -v quoted "'%s' " "${@:2}"
    printf '%s %-13s | %s\n' "${stamp}" "${event}" "${quoted% }" >> "${log_dir}/oceanic_plugin.log"
    "${pyxe}" "${py_dir}/runs/oceanor.py" "oce_${event}" "${@:2}"
}

__oce_main() {
    [[ ${BASH_SOURCE[0]} == "${0}" ]] || return 0
    set -uo pipefail
    _oce_respond "$@"
}

__oce_main "$@"
