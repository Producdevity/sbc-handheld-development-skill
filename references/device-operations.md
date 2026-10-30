# Device operations

Use capability probes, not assumptions. An SSH alias identifies a host, not its current CFW, device, storage layout, frontend state, or installed PortMaster version.

## Read-only discovery

Collect only what the task needs:

- `/etc/os-release`, kernel, architecture, libc, and ELF interpreter;
- device-tree compatible strings and PortMaster `device_info` output;
- mounted ROM roots and filesystem type;
- PortMaster location/version and active `control.txt`/CFW module;
- frontend, compositor, audio server, and application process tree;
- `/proc/bus/input/devices`, relevant `/sys/class/input` capabilities, and `/dev/uinput` availability;
- framebuffer/DRM nodes and installed capture utilities;
- application launcher, log, config, save, and installed binary hashes;
- `readelf`, `ldd`, debugger, tracing, and performance-tool availability.

Do not collect home directories, shell environments, SSH material, Wi-Fi profiles, tokens, account data, or full network addresses in a general probe. Sanitize serials, MAC addresses, and incidental identifiers before retaining evidence.

[probe_handheld.sh](../scripts/probe_handheld.sh) provides a conservative stdout-only baseline. Extend a project copy only when a task needs more evidence; do not turn the global probe into a dump of every file on the device.

Treat PortMaster's `device_info.txt` as executable shell, not a read-only data file. Inspect the installed version before sourcing it: current versions write a report under `$HOME`, and their SDL resolution probe depends on the active compositor environment. When its values are needed for diagnostics, use a temporary `HOME` and the frontend's measured SDL/Wayland environment. A plain SSH shell can otherwise return a fallback resolution that does not match the display.

## Frontend-owned launch

The normal proof path is:

```text
frontend selection -> firmware launcher -> PortMaster launcher -> application -> PortMaster cleanup -> frontend resume
```

Verify the process chain and the selected executable. Never infer success from the launcher process alone.

Prefer the frontend's own launch entry point over menu navigation: the
EmulationStation API on KNULLI, Batocera, ROCKNIX and AmberELEC; the content
loader on muOS; the PyUI command handoff on SpruceOS. Each CFW profile below
covers its entry point. Screen capture and injected keys are for end-to-end
menu checks, or for firmware without an entry point such as dArkOS FCAMOD.

### muOS

muOS launch and controller internals change between releases. Before launching,
navigating, or injecting input, read [the muOS profile](cfw/muos.md) and trace
the installed scripts. Do not reproduce a remembered request file, controller
setting, or handoff path from another version.

`mod_muOS.txt` records the foreground executable for some PortMaster integrations, but it is only one layer. Source PortMaster's active controls and module instead of reconstructing its SDL, audio, governor, and cleanup environment.

### KNULLI and Batocera-derived systems

Read [the KNULLI profile](cfw/knulli.md) for its measured frontend lifecycle,
SSH service, persistence boundary, and generated SDL environment. Batocera
derivatives share ancestry, not necessarily the same scripts or paths; inspect
the installed system rather than applying the KNULLI profile wholesale.

### ROCKNIX

ROCKNIX commonly runs EmulationStation under Sway. Its
[`emulationstation-next`](https://github.com/ROCKNIX/emulationstation-next/blob/f6c542872e3850c5f432929ead219547a897cd4a/es-app/src/services/HttpServerThread.cpp)
serves the same loopback `/launch` API as KNULLI; follow the KNULLI steps with
the installed ROM path (commonly `/storage/roms`). PortMaster's `mod_ROCKNIX.txt` calls `portmaster_sway_fullscreen.sh` when present; keep `pm_platform_helper` in the launcher rather than reproducing Sway rules.

Probe for the active screenshot helper and compositor socket. A framebuffer tool is not automatically valid for a Sway-composited application.

### SpruceOS on Miyoo Flip

Read [the SpruceOS Miyoo Flip profile](cfw/spruce.md) for its PyUI lifecycle,
SSH behavior, capture limitations, and frontend input adapter. Do not apply it
to CrossMix or a Miyoo Mini Flip.

### AmberELEC

Read [the AmberELEC profile](cfw/amberelec.md) for its SSH persistence,
`emustation.service` lifecycle, measured R36S/RG351MP identity mismatch, and
RK3326 controller profile.

### ArkOS, dArkOS, dArkOSRE, and other CFWs

Treat these as separate targets. PortMaster ships distinct modules because audio, GPU, privilege, tty, frontend, and filesystem behavior differ. Do not merge dArkOS variants or infer ArkOS behavior from them. When no supported remote-launch API is proven, use visible frontend navigation or ask the user to launch the item.

For dArkOS, read [the dArkOS profile](cfw/darkos.md). It covers firmware identity, the EmulationStation service, PortMaster versions, RK3326 input and audio controls. Verify those details on the installed image; do not apply them to another ArkOS variant by name alone.

## Capture selection

Choose the method that captures the application actually being tested:

1. firmware-native screenshot helper;
2. compositor-native capture, such as `grim` under Sway;
3. `fbgrab` for a live fbdev target;
4. `ffmpeg` with its `fbdev` input when the framebuffer is readable;
5. a CFW-specific framebuffer helper with its required library environment;
6. application-owned readback only for renderer diagnostics.

Verify that the output exists, is non-empty, has current timestamps, and depicts the intended state. A black image may mean a blank framebuffer while another plane or compositor contains the game.

Framebuffer alpha bytes are not necessarily meaningful transparency. Some
`fbgrab` builds write them into the PNG alpha channel as zero or low values,
making a valid capture appear transparent. The shared capture helper converts
every 8-bit RGB/RGBA PNG to opaque RGB with host-side Python before returning it.
For captures acquired through another path, run `scripts/normalize_png.py`
before showing or publishing them. Discard the unused alpha; compositing onto
a background would darken the original pixels. Inspect the normalized image
and show it with an absolute-path Markdown image embed.

Treat capture-process completion and image validity as separate checks. An
FFmpeg single-frame capture can write a complete PNG before the process exits.
Use a bounded timeout and a unique output path; verify decoding and freshness
before accepting or rejecting the image.

For repeated diagnostics on a proven live fbdev source, a read-only copy of
the active framebuffer page followed by host-side encoding avoids probe and
encoder overhead. Check dimensions, pixel layout, stride and mapping bounds,
and verify that the active page offset stayed unchanged during the copy.
This is not a substitute for identifying the active compositor or DRM plane.

An immediate black capture can also be a normal startup frame. If the process chain is healthy, take a short bounded series of delayed captures before changing launch or capture methods. Record each timestamp; do not silently discard the early frame.

The available method changes by firmware version. `fbgrab` worked on specific muOS and KNULLI H700 builds; on an RG35XX-SP muOS build it captured the frontend but only black for a fullscreen GLES game, so use an in-app capture there. Older muOS builds exposed PNG capture as `mufbset -g`, while current builds may use the same name only for display-mode configuration. Check the installed command's help before using `-g`. ROCKNIX uses Sway-aware handling. SpruceOS on Miyoo Flip provides a KMS/FFmpeg screenshot helper.

[`capture_screen.sh`](../scripts/capture_screen.sh) wraps the measured fbdev methods and Sway/`grim` for host-side use:

```sh
capture_screen.sh HOST evidence/current.png
```

It uses `mufbset` only when the installed command advertises `-g`. For Sway it reads `XDG_RUNTIME_DIR` and `WAYLAND_DISPLAY` only from a running compositor or EmulationStation process and verifies the socket before invoking `grim`. It does not enable ROCKNIX's optional screenshot service or claim to support every compositor.

## Logs and process evidence

- Prefer the port's `log.txt` or application-owned log.
- Capture the frontend-to-app process tree with timestamps.
- Record exit status and confirm frontend restoration.
- Use `journalctl` only for the relevant unit/time window.
- Bound `strace`, `perf`, packet capture, and verbose logs by duration and file size.
- Never enable per-frame or per-packet logging for a long run unless sampling is the experiment.

For short performance runs, record the process and thread IDs before sampling. `/proc/PID/task/*/stat`, `/proc/PID/status`, and `/proc/PID/smaps_rollup` are widely available, but their fields and permissions still need probing. Frame timing may come from a renderer swap hook, application instrumentation, or timestamped captures; record which clock and layer produced it.

## Safe deployment

Before copying:

1. identify the exact target root and existing installation;
2. compare local and installed hashes;
3. identify user-owned configs, saves, APK/game data, credentials, and logs;
4. stage the new files beside the destination;
5. replace only project-owned files;
6. verify hashes and permissions after installation.

[`hash_tree.py`](../scripts/hash_tree.py) creates a sorted SHA-256 manifest that includes files, directories, and symlinks:

```sh
python3 hash_tree.py /path/to/data --output before.json
python3 hash_tree.py /path/to/data --compare before.json
```

Use it to prove which files changed during setup or an update. Keep a separate backup for file contents, ownership, permissions, and extended attributes.

Use existing task authorization for scoped test-app stops and frontend
restoration. Removing installations, resetting user/setup state, touching
unrelated processes or changing firmware needs separate authorization when
outside that scope. Keep temporary tools under the target's `/tmp` or the
app's directory; system-package installation follows the skill's authorization
rules.
