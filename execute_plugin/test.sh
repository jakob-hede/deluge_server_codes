#!/usr/bin/env bash



execute() {
  lib="$(dirname "${BASH_SOURCE[0]}")/exe_lib.sh"
  # shellcheck disable=SC1090
  . "${lib}"
  exe_added "$@"
  exe_completed "$@"
  exe_removed "$@"
}

echo
execute "Hrello"
echo

#execute () {
###  echo 'execute' "$0" "$@"
##  /opt/roots/delugor_root/opt/deludome/codes/execute_plugin/added_exe.sh "$@"
##  /opt/roots/delugor_root/opt/deludome/codes/execute_plugin/completed_exe.sh "$@"
##  /opt/roots/delugor_root/opt/deludome/codes/execute_plugin/removed_exe.sh "$@"
#}

#  printf '%s\n' "$*" >> "${DELUXE_LOG_FILE}"


  #  local script_dir="$(dirname $0)"
  #  local project_dir="$(realpath "/..")"

#/opt/deludome/codes/execute_plugin/completed_exe.sh