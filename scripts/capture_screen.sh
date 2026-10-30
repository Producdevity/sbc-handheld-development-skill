#!/bin/sh
# The remote path below is generated from the local numeric process ID.
# shellcheck disable=SC2029

set -eu

usage() {
  echo "usage: $0 HOST OUTPUT.png [auto|spruce-kms|fbgrab|ffmpeg-fbdev|muos-mufbset|sway-grim]" >&2
  exit 2
}

[ "$#" -ge 2 ] && [ "$#" -le 3 ] || usage

host=$1
output=$2
method=${3:-auto}

case "$host" in
  -*)
    echo "HOST must not begin with '-'" >&2
    exit 2
    ;;
esac

case "$method" in
  auto | spruce-kms | fbgrab | ffmpeg-fbdev | muos-mufbset | sway-grim) ;;
  *) usage ;;
esac

find_wayland_environment() {
  ssh "$host" '
    for process in /proc/[0-9]*; do
      [ -r "$process/comm" ] && [ -r "$process/environ" ] || continue
      name=$(sed -n "1p" "$process/comm")
      case "$name" in
        emulationstatio* | sway* | weston*) ;;
        *) continue ;;
      esac
      runtime=$(tr "\000" "\n" <"$process/environ" | sed -n "s/^XDG_RUNTIME_DIR=//p" | sed -n "1p")
      display=$(tr "\000" "\n" <"$process/environ" | sed -n "s/^WAYLAND_DISPLAY=//p" | sed -n "1p")
      if [ -n "$runtime" ] && [ -n "$display" ] && [ -S "$runtime/$display" ]; then
        printf "%s\n%s\n" "$runtime" "$display"
        exit 0
      fi
    done
    exit 1
  '
}

remote="/tmp/handheld-capture-$$.png"
local_tmp="${output}.tmp.$$"
cleanup() {
  ssh "$host" "rm -f '$remote'" >/dev/null 2>&1 || true
  rm -f "$local_tmp"
}
interrupted() {
  trap - EXIT HUP INT TERM
  cleanup
  exit 1
}
trap cleanup EXIT
trap interrupted HUP INT TERM

wayland_environment=
if [ "$method" = auto ]; then
  if ssh "$host" 'command -v grim >/dev/null 2>&1' &&
    wayland_environment=$(find_wayland_environment); then
    method=sway-grim
  else
    wayland_environment=
    method=$(ssh "$host" '
      if [ -x /mnt/SDCARD/spruce/flip/screenshot.sh ]; then
        echo spruce-kms
      elif command -v fbgrab >/dev/null 2>&1; then
        echo fbgrab
      elif command -v ffmpeg >/dev/null 2>&1 && [ -r /dev/fb0 ]; then
        echo ffmpeg-fbdev
      elif [ -x /opt/muos/frontend/mufbset ] &&
        LD_LIBRARY_PATH=/opt/muos/frontend/lib /opt/muos/frontend/mufbset --help 2>&1 |
          grep -Eq -- "(^|[[:space:]])-g([[:space:],]|$)"; then
        echo muos-mufbset
      else
        echo none
      fi
    ')
  fi
fi

case "$method" in
  spruce-kms)
    if ! ssh "$host" '[ -x /mnt/SDCARD/spruce/flip/screenshot.sh ]'; then
      echo "SpruceOS KMS capture is not available on $host" >&2
      exit 1
    fi
    if ! ssh "$host" "/mnt/SDCARD/spruce/flip/screenshot.sh '$remote' >/dev/null 2>&1"; then
      ssh "$host" "rm -f '$remote'; LD_LIBRARY_PATH=/mnt/SDCARD/spruce/flip/lib:/usr/lib:/lib/:/mnt/SDCARD/spruce/flip/arm64-ffmpeg/bin /mnt/SDCARD/spruce/flip/arm64-ffmpeg/bin/ffmpeg -nostdin -hide_banner -loglevel error -f kmsgrab -device /dev/dri/card0 -i - -vf 'hwdownload,format=bgra' -frames:v 1 -y '$remote'"
    fi
    ;;
  fbgrab)
    if ! ssh "$host" '
      command -v fbgrab >/dev/null 2>&1 ||
        [ -x /mnt/SDCARD/spruce/bin64/fbgrab ] ||
        [ -x /mnt/SDCARD/spruce/bin/fbgrab ]
    '; then
      echo "fbgrab is not available on $host" >&2
      exit 1
    fi
    ssh "$host" "
    if command -v fbgrab >/dev/null 2>&1; then
      capture=fbgrab
    elif [ -x /mnt/SDCARD/spruce/bin64/fbgrab ]; then
      capture=/mnt/SDCARD/spruce/bin64/fbgrab
    else
      capture=/mnt/SDCARD/spruce/bin/fbgrab
    fi
    \"\$capture\" '$remote'
  "
    ;;
  ffmpeg-fbdev)
    if ! ssh "$host" 'command -v ffmpeg >/dev/null 2>&1 && [ -r /dev/fb0 ]'; then
      echo "ffmpeg fbdev capture is not available on $host" >&2
      exit 1
    fi
    ssh "$host" "ffmpeg -nostdin -hide_banner -loglevel error -f fbdev -framerate 1 -i /dev/fb0 -frames:v 1 -y '$remote'"
    ;;
  muos-mufbset)
    if ! ssh "$host" '
      [ -x /opt/muos/frontend/mufbset ] &&
        LD_LIBRARY_PATH=/opt/muos/frontend/lib /opt/muos/frontend/mufbset --help 2>&1 |
          grep -Eq -- "(^|[[:space:]])-g([[:space:],]|$)"
    '; then
      echo "mufbset on $host does not support PNG capture" >&2
      exit 1
    fi
    ssh "$host" "LD_LIBRARY_PATH=/opt/muos/frontend/lib /opt/muos/frontend/mufbset -g '$remote'"
    ;;
  sway-grim)
    if ! ssh "$host" 'command -v grim >/dev/null 2>&1'; then
      echo "grim is not available on $host" >&2
      exit 1
    fi
    if [ -z "$wayland_environment" ]; then
      wayland_environment=$(find_wayland_environment) || {
        echo "no active Sway/Wayland session found on $host" >&2
        exit 1
      }
    fi
    runtime=$(printf '%s\n' "$wayland_environment" | sed -n '1p')
    display=$(printf '%s\n' "$wayland_environment" | sed -n '2p')
    case "$runtime:$display" in
      *[!A-Za-z0-9_./:-]*)
        echo "unsafe Wayland environment returned by $host" >&2
        exit 1
        ;;
    esac
    ssh "$host" "XDG_RUNTIME_DIR='$runtime' WAYLAND_DISPLAY='$display' grim '$remote'"
    ;;
  *)
    echo "no supported capture method found on $host" >&2
    exit 1
    ;;
esac

mkdir -p "$(dirname "$output")"
scp -q "$host:$remote" "$local_tmp"
[ -s "$local_tmp" ] || {
  echo "capture is empty: $local_tmp" >&2
  exit 1
}

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 "$script_dir/normalize_png.py" "$local_tmp"
mv "$local_tmp" "$output"

printf 'captured method=%s path=%s\n' "$method" "$output"
