#!/usr/bin/env bash



execute() {
  lib="$(dirname "${BASH_SOURCE[0]}")/exe_lib.sh"
  # shellcheck disable=SC1090
  . "${lib}"
#  exe_added '8178b09bde84d46c945b7b601b8bc3c0a959569e' 'Friendship (2025) [1080p] [WEBRip] [5.1] [YTS.MX]' '/deluge/downloads'
  exe_completed '94941321a2d383ddf0b276f94c889b980715c072' 'The Naked Gun (2025) [1080p] [WEBRip] [5.1] [YTS.MX]' '/ocean/video/movies/movin'
}

echo
execute
echo
