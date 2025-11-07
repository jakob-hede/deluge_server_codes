#!/usr/bin/env bash

#DELUXE_LOG_FILE='/deluge/log/execute_plugin.log'
#DELUXE_LOG_FILE='/var/log/deluge/exe.log'

exe_added() {
  #  echo "${FUNCNAME}" "$@"
  exe_sub "${FUNCNAME[0]}" "$@"
}

exe_completed() {
  #  echo "${FUNCNAME}" "$@"
  exe_sub "${FUNCNAME[0]}" "$@"
  #  # Send output from python script to log file:
  #  exe_sub "$(/opt/optulation/mixed/jellyfin/py/jellyfining/apiing/run/library_refresh.py)"
  #  #  exe_sub "$(/opt/optulation/mixed/jellyfin/py/jellyfining/run/library_refresh.py)"
  #  #
}

exe_removed() {
  #  echo "${FUNCNAME}" "$@"
  exe_sub "${FUNCNAME[0]}" "$@"
}

exe_status() {
#  print "exe_status called"
  exe_sub "${FUNCNAME[0]}" "$@"
}

print() {
  printf '\e[90m%s\e[0m\n' "$*"
}

log_print() {
  print "$*"
  printf '%s\n' "$*" >> "${log_file}"
}

fail() {
  printf '\e[31mFAIL: %s\e[0m\n' "$*"
  exit 1
}

habitize() {
  timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

#  print "lib: ${lib}"
  declare script_dir config_file
  script_dir="$(dirname "${BASH_SOURCE[0]}")"
#  print "script_dir: ${script_dir}"
  config_file="${script_dir}/exe.conf.sh"
  [[ -f "${config_file}" ]] && {
    # shellcheck disable=SC1090
    . "${config_file}"
    print "sourced config_file: ${config_file}"
  }

  [[ -z "${log_dir}" ]] && log_dir='/deluge/log'
  [[ -z "${pyxe}" ]] && pyxe='/usr/bin/python'
  [[ -z "${py_dir}" ]] && py_dir='/codes/py'

#  log_dir='/deluge/log'
  [[ -d "${log_dir}" ]] || {
    log_dir='/mnt/btrfs_data/deluge/log'
    #     /bin/mkdir -p "${log_dir}"
  }
  [[ -d "${log_dir}" ]] || fail "log_dir no exists: ${log_dir}"
  print "log_dir: ${log_dir}"
  print "pyxe: ${pyxe}"
#  [[ -d "${log_dir}" ]] || {
#    printf 'log_dir no exists: %s\n'  "${log_dir}"
#    return 1
#  }
#  mkdir -p "${log_dir}"
  log_file="${log_dir}/execute_plugin.log"
#  log_file='/deluge/log/execute_plugin.log'
  touch "${log_file}"
  echo 'RESET' > "${log_file}"

  # make all log files in log_dir readable and writable by all users

}

exe_sub() ( # Start a subshell
  declare timestamp log_dir log_file pyxe py_file  # pystdout
  habitize
  declare funcname funcname_pad msg
  funcname="$1"
  shift

  funcname_pad="$(printf '%-13s' "${funcname}")"
  msg="${timestamp} ${funcname_pad} | $*"

  log_print "${msg}"
##  printf '%s\n' "$(tail "${log_file}")" >"${log_file}"
#  printf '%s\n' "${msg}" >>"${log_file}"
#
#  /usr/bin/python /codes/py/executor.py "${funcname}" "$@"

  py_file="${py_dir}/runs/executor.py"
  "${pyxe}" "${py_file}" "${funcname}" "$@"
)



#  python3 /codes/py/executor.py "${funcname}" "$@" || {
#    printf '%s\n' "ERROR: executor.py ${funcname} failed" >>"${log_file}"
#    return 1
#  }

#  pystdout="$(/usr/bin/python /codes/py/executor.py "${funcname}" "$@" 2>&1)"
#  printf '%s\n' "${pystdout}" >>"${log_file}"


# 2025-08-31T08:45:03Z exe_completed

#exe_sub() {
#  msg="$(date +%x.%T) $*"
#  echo "${msg}"
#  printf '%s\n' "$(tail "${DELUXE_LOG_FILE}")" >"${DELUXE_LOG_FILE}"
#  printf '%s\n' "${msg}" >>"${DELUXE_LOG_FILE}"
#}

#execute "$@"

#  printf '%s\n' "$*" >> "${DELUXE_LOG_FILE}"

#  local script_dir="$(dirname $0)"
#  local project_dir="$(realpath "/..")"
