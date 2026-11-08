#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu

if [ "${1:-}" = --help ]; then
  printf 'Usage: %s [absolute-autoinstall-directory]\n' "$0"
  printf 'Print the PortMaster queue on this device without changing it.\n'
  exit 0
fi
[ "$#" -le 1 ] || {
  echo 'Expected at most one autoinstall directory' >&2
  exit 2
}

queue=${1:-}
if [ -z "$queue" ]; then
  selected=
  for base in \
    /opt/system/Tools/PortMaster \
    /opt/tools/PortMaster \
    "${XDG_DATA_HOME:-${HOME:-}/.local/share}/PortMaster" \
    /userdata/system/.local/share/PortMaster \
    /mnt/mmc/MUOS/PortMaster \
    /mnt/SDCARD/Persistent/portmaster/PortMaster \
    /roms/tools/PortMaster \
    /roms2/tools/PortMaster \
    /roms/ports/PortMaster \
    /roms2/ports/PortMaster \
    /storage/roms/ports/PortMaster; do
    case "$base" in /*) ;; *) continue ;; esac
    # muOS 2601.0 also has a copy of control.txt alone in /roms/ports/PortMaster; only the real install has harbourmaster.
    [ -r "$base/control.txt" ] && [ -f "$base/harbourmaster" ] || continue
    if [ -n "$selected" ]; then
      [ "$base" -ef "$selected" ] && continue
      printf 'Multiple PortMaster installations: %s and %s. Pass an explicit autoinstall directory.\n' \
        "$selected" "$base" >&2
      exit 1
    fi
    selected=$base
  done
  [ -n "$selected" ] || {
    echo 'PortMaster installation not found. Pass an explicit autoinstall directory for a custom location.' >&2
    exit 1
  }
  queue=$selected/autoinstall
fi

case "$queue" in
/*/autoinstall) ;;
*)
  echo 'Expected an absolute autoinstall directory' >&2
  exit 2
  ;;
esac
[ -d "$queue" ] && [ -w "$queue" ] || {
  printf 'PortMaster queue is missing or not writable: %s. Open PortMaster once or choose another queue.\n' "$queue" >&2
  exit 1
}
printf '%s\n' "$queue"
