# dArkOS device operations

## Identity and launch

`/etc/os-release` can identify the Debian userland rather than dArkOS.
Correlate it with the boot theme title, device tree, installed frontend and
PortMaster device information. An R36S image can retain an RG351MP software
profile; record both identities rather than changing the profile to match the
case label.

Inspect `emulationstation.service` and its `ExecStart` wrapper. Use the normal
frontend to launch ports. For an authorized isolated diagnostic, use the
service lifecycle and verify restoration; do not start another
EmulationStation process directly. Shutdown text left in the framebuffer is
not evidence that the OS powered off.

Check both `/opt/system/Tools/PortMaster` and the ROM-volume installation.
Follow the selected `control.txt` into `device_info.txt` and `funcs.txt` before
judging which helpers it provides; they need not be defined in `control.txt`.
A missing CFW module alone does not prove an incompatible installation.
Resolve this through PortMaster's supported initialization/update path rather
than adding device-specific replacements to every port.

## Programmatic navigation

Discover command interfaces in the installed frontend before replaying menus.
Do not assume KNULLI's HTTP launch service exists on dArkOS. The audited FCAMOD
[startup code](https://github.com/christianhaitian/EmulationStation-fcamod/blob/c4809d8ef33159385a2d516b4b3aec832f4ce2e8/es-app/src/views/ViewController.cpp)
selects a system or game list; those startup settings do not launch a named
port. Its `game-start` and `game-end` scripts are lifecycle notifications, not
an external launch API. Check the actual fork/version before applying this.

For a verified menu route, use a bounded input sequence and check arrival,
rather than capturing after every button. The frontend's
[input handler](https://github.com/christianhaitian/EmulationStation-fcamod/blob/c4809d8ef33159385a2d516b4b3aec832f4ce2e8/es-core/src/InputManager.cpp)
uses SDL joystick events and its own bindings and axis threshold crossings.
An evdev injector that works in a game does not prove frontend compatibility.
If navigation is ignored, check the frontend's loaded SDL, input backend,
configuration and observed values before retrying the same route.

For repeated application tests without a verified frontend launch interface,
use an authorized isolated service stop/restore diagnostic. Preserve the
normal account and required environment, and inspect the complete configured
launch command: governor, priority, audio and lifecycle wrappers may surround
the port script. A bare SSH invocation omits those steps and does not prove
normal frontend behavior. Keep the measured launch recipe and state observers
in the project's ignored files; return to the normal frontend for integration
checks.

## Input, audio and storage

RK3326 images may expose `GO-Super Gamepad`; verify its IDs, axes and the
frontend's actual input configuration before using the measured profile from
[AmberELEC](amberelec.md#rk3326-input-profile). Shared hardware does not imply
identical SDL mappings or frontend actions.

When injecting axes into a physical evdev node, a polling driver can replace
the injected value and fuzz filtering can discard repeated samples. If this
occurs, use bounded, varying samples within the measured range, then restore
the measured neutral value. Verify motion in SDL or the game; repeated pulses
do not establish a continuously held stick.

Inspect ALSA controls before muting. Some RK817 codecs expose a volume-only
`Playback` control and a separate `Playback Path` enum with `OFF`, `SPK`, `HP`
and `SPK_HP`. Do not assume the H700 `SPK` switch or PulseAudio exists.
`OFF` disables system-wide routing; volume buttons may leave it off. Route
changes can reset volume, so reapply the saved level when undoing a routing mute.

Use `findmnt` or `lsblk` when calculating setup space. `/opt/system/Tools` may
be a bind mount from the same partition as `/roms`, not extra storage.

## EGL library selection

The frontend can select Mali directly with
`SDL_VIDEO_EGL_DRIVER=libEGL.so`, while `libEGL.so.1` resolves to GLVND.
They can maintain separate current-display state. A port that loads EGL
functions itself must use the same implementation as SDL; otherwise SDL can
create its window successfully while guest-context setup reports no current
EGL display. Inspect resolved library paths before changing drivers or bundling
replacement libraries.
