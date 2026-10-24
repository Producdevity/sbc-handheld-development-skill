#!/bin/sh

set -eu

usage() {
  echo "usage: $0 HOST release-all" >&2
  exit 2
}

[ "$#" -eq 2 ] || usage

host=$1
operation=$2

case "$host" in
  -*)
    echo "HOST must not begin with '-'" >&2
    exit 2
    ;;
esac

release_all() {
  {
    for code in 304 305 307 308 310 311 314 315 316 317 318; do
      printf '1 %s 0\n' "$code"
    done
    for code in 0 1 2 3 4 5 16 17; do
      printf '3 %s 0\n' "$code"
    done
    printf '0 0 0\n'
  } | ssh "$host" '
    set -eu
    event=/dev/input/event5
    sender=/mnt/SDCARD/spruce/bin64/sendevent
    [ -x "$sender" ]
    [ "$(sed -n "1p" /sys/class/input/event5/device/name)" = "MIYOO Player1" ]
    exec "$sender" "$event"
  '
}

[ "$operation" = "release-all" ] || usage
release_all
