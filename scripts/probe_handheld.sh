#!/bin/sh

set -u

section() {
  printf '\n[%s]\n' "$1"
}

show_file() {
  label=$1
  path=$2
  if [ -r "$path" ]; then
    printf '%s=%s\n' "$label" "$(tr '\000' '\n' <"$path" 2>/dev/null | sed -n '1,20p')"
  fi
}

show_command() {
  name=$1
  if command -v "$name" >/dev/null 2>&1; then
    printf '%s=%s\n' "$name" "$(command -v "$name")"
  else
    printf '%s=missing\n' "$name"
  fi
}

show_command_or_path() {
  name=$1
  shift
  if command -v "$name" >/dev/null 2>&1; then
    printf '%s=%s\n' "$name" "$(command -v "$name")"
    return
  fi
  for path in "$@"; do
    if [ -x "$path" ]; then
      printf '%s=%s\n' "$name" "$path"
      return
    fi
  done
  printf '%s=missing\n' "$name"
}

if [ "${1:-}" = "--help" ]; then
  printf 'usage: %s\n' "$0"
  printf 'Print a read-only handheld development capability report to stdout.\n'
  exit 0
fi

if [ "$#" -ne 0 ]; then
  printf 'usage: %s\n' "$0" >&2
  exit 2
fi

section system
printf 'kernel=%s\n' "$(uname -r 2>/dev/null || true)"
printf 'machine=%s\n' "$(uname -m 2>/dev/null || true)"
if [ -r /etc/os-release ]; then
  sed -n '/^\(ID\|ID_LIKE\|NAME\|PRETTY_NAME\|VERSION\|VERSION_ID\|OS_NAME\|OS_VERSION\|OS_BUILD\)=/p' /etc/os-release
fi
if [ -r /usr/share/plymouth/themes/text.plymouth ]; then
  sed -n 's/^title=/cfw_title=/p' /usr/share/plymouth/themes/text.plymouth | sed -n '1p'
fi
if command -v getconf >/dev/null 2>&1; then
  printf 'libc=%s\n' "$(getconf GNU_LIBC_VERSION 2>/dev/null || true)"
fi
show_file device_model /proc/device-tree/model
show_file device_compatible /proc/device-tree/compatible
show_file miyoo_firmware /usr/miyoo/version
if [ -d /mnt/SDCARD/spruce ]; then
  printf 'spruce_root=/mnt/SDCARD/spruce\n'
  if [ -r /mnt/SDCARD/App/spruceRestore/.lastUpdate ]; then
    sed -n 's/^spruce_version=/spruce_version=/p' /mnt/SDCARD/App/spruceRestore/.lastUpdate | sed -n '1p'
  fi
fi

section storage
if [ -r /proc/mounts ]; then
  awk '$2 ~ /^\/(roms|roms2|storage|userdata|mnt|media)(\/|$)/ {print "mount=" $2 " type=" $3 " options=" $4}' /proc/mounts
fi
seen_portmaster='|'
for path in \
  /opt/system/Tools/PortMaster \
  /opt/tools/PortMaster \
  /roms/ports/PortMaster \
  /roms2/ports/PortMaster \
  /storage/roms/ports/PortMaster \
  /userdata/system/.local/share/PortMaster \
  /mnt/SDCARD/Persistent/portmaster/PortMaster \
  /mnt/mmc/MUOS/PortMaster; do
  if [ -d "$path" ]; then
    resolved=$(readlink -f "$path" 2>/dev/null || printf '%s' "$path")
    case "$seen_portmaster" in
      *"|$resolved|"*) continue ;;
    esac
    seen_portmaster="${seen_portmaster}${resolved}|"
    printf 'portmaster=%s\n' "$resolved"
    if [ -r "$resolved/version" ]; then
      printf 'portmaster_version=%s\n' "$(sed -n '1p' "$resolved/version")"
    fi
  fi
done
unset resolved seen_portmaster

section frontend
if command -v ps >/dev/null 2>&1; then
  if ps -ef >/dev/null 2>&1; then
    ps -ef 2>/dev/null
  else
    ps 2>/dev/null
  fi | awk 'BEGIN {IGNORECASE=1} /emulationstation|frontend\.sh|muxfrontend|muxlaunch|sway|weston|portmaster|mainui|principal\.sh/ && !/awk/ {print}' || true
fi
for path in \
  /run/muos/system/foreground_process \
  /opt/muos/config/system/foreground_process; do
  if [ -r "$path" ]; then
    printf 'foreground_file=%s value=%s\n' "$path" "$(sed -n '1p' "$path")"
  fi
done

section display
for node in /sys/class/graphics/fb*; do
  if [ -d "$node" ]; then
    printf 'framebuffer=%s' "${node##*/}"
    if [ -r "$node/name" ]; then
      printf ' name=%s' "$(sed -n '1p' "$node/name")"
    fi
    if [ -r "$node/virtual_size" ]; then
      printf ' virtual_size=%s' "$(sed -n '1p' "$node/virtual_size")"
    fi
    printf '\n'
  fi
done
for node in /sys/class/drm/card*-*; do
  if [ -d "$node" ] && [ -r "$node/status" ]; then
    printf 'drm_connector=%s status=%s\n' "${node##*/}" "$(sed -n '1p' "$node/status")"
  fi
done

section input
if [ -r /proc/bus/input/devices ]; then
  sed -n '/^N: Name=/p;/^H: Handlers=/p;/^B: EV=/p;/^B: KEY=/p;/^B: ABS=/p' /proc/bus/input/devices
fi
show_file muos_sdl_name /opt/muos/device/config/sdl/name
show_file muos_layout_legacy /opt/muos/config/settings/advanced/swap
show_file muos_layout /opt/muos/config/settings/remap/layout
show_file muos_dpad_swap /opt/muos/config/settings/advanced/dpad_swap
if [ -e /usr/lib/gamecontrollerdb.txt ]; then
  printf 'sdl_controller_db=%s\n' "$(readlink -f /usr/lib/gamecontrollerdb.txt 2>/dev/null || printf '%s' /usr/lib/gamecontrollerdb.txt)"
fi
if [ -e /dev/uinput ]; then
  ls -l /dev/uinput 2>/dev/null || true
else
  printf '/dev/uinput=missing\n'
fi

section audio
if [ -r /proc/asound/cards ]; then
  sed -n '1,80p' /proc/asound/cards
fi
if [ -S /run/pipewire-0 ]; then
  printf 'pipewire_socket=/run/pipewire-0\n'
elif [ -S /var/run/pipewire-0 ]; then
  printf 'pipewire_socket=/var/run/pipewire-0\n'
fi

section tools
for name in \
  file readelf sha256sum \
  evemu-describe evemu-device evemu-record evemu-play evemu-event \
  sdl2-jstest jstest \
  grim grimshot rocknix-screenshot knulli-screenshot \
  gdb gdbserver strace perf \
  curl wget ssh scp; do
  show_command "$name"
done
show_command_or_path ldd /mnt/SDCARD/spruce/bin64/ldd
show_command_or_path evtest /mnt/SDCARD/spruce/bin64/evtest
show_command_or_path rsync /mnt/SDCARD/spruce/bin64/rsync
show_command_or_path fbgrab \
  /mnt/SDCARD/spruce/bin64/fbgrab \
  /mnt/SDCARD/spruce/bin/fbgrab
show_command_or_path ffmpeg \
  /mnt/SDCARD/spruce/flip/arm64-ffmpeg/bin/ffmpeg \
  /mnt/SDCARD/spruce/bin64/ffmpeg \
  /mnt/SDCARD/spruce/bin/ffmpeg
show_command_or_path gptokeyb \
  /opt/system/Tools/PortMaster/gptokeyb \
  /opt/tools/PortMaster/gptokeyb \
  /roms/ports/PortMaster/gptokeyb \
  /roms2/ports/PortMaster/gptokeyb \
  /storage/roms/ports/PortMaster/gptokeyb \
  /userdata/system/.local/share/PortMaster/gptokeyb \
  /mnt/SDCARD/Persistent/portmaster/PortMaster/gptokeyb \
  /mnt/mmc/MUOS/PortMaster/gptokeyb
show_command_or_path gptokeyb2 \
  /opt/system/Tools/PortMaster/gptokeyb2 \
  /opt/tools/PortMaster/gptokeyb2 \
  /roms/ports/PortMaster/gptokeyb2 \
  /roms2/ports/PortMaster/gptokeyb2 \
  /storage/roms/ports/PortMaster/gptokeyb2 \
  /userdata/system/.local/share/PortMaster/gptokeyb2 \
  /mnt/SDCARD/Persistent/portmaster/PortMaster/gptokeyb2 \
  /mnt/mmc/MUOS/PortMaster/gptokeyb2
show_command_or_path mufbset /opt/muos/frontend/mufbset
