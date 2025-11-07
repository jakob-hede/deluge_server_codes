#!/usr/bin/env bash

execute() {
  declare lib
  lib="$(dirname "${BASH_SOURCE[0]}")/exe_lib.sh"
  # shellcheck disable=SC1090
  . "${lib}"
  exe_status "$@"
}

execute "$@"
