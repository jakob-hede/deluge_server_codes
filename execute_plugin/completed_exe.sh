#!/usr/bin/env bash

execute() {
  lib="$(dirname "${BASH_SOURCE[0]}")/exe_lib.sh"
  # shellcheck disable=SC1090
  . "${lib}"
  exe_completed "$@"
}

execute "$@"

#################
#  echo 'execute' "$0" "$@"
#  echo "lib=${lib}"

#  bashis='BASH_SOURCE'
#  echo "${bashis}=${!bashis}"
