#!/usr/bin/env bash

execute() {
  lib="$(dirname "${BASH_SOURCE[0]}")/exe_lib.sh"
  # shellcheck disable=SC1090
  . "${lib}"
  exe_removed "$@"
}

execute "$@"
