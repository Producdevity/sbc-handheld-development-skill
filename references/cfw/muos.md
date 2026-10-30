# muOS device operations

Treat the installed firmware as authoritative. Use pinned upstream source to explain that build, not as a substitute for inspecting it. muOS changes its launch-state files, controller settings, and cleanup functions between releases.

## Trace the installed build

Record `/etc/os-release` and the device board name, then inspect only the files used by that build:

- `/opt/muos/script/mux/frontend.sh` for the frontend loop and content-loader trigger;
- `/opt/muos/script/mux/launch.sh` for request parsing, launcher selection, and cleanup;
- the selected assignment INI under `/opt/muos/share/info/assign/`;
- the resolved external launcher, commonly under `/opt/muos/script/launch/`;
- the SDL environment function in `/opt/muos/script/var/func.sh`;
- the installed PortMaster `control.txt` and `mod_muOS.txt`;
- the active controller database and its resolved symlink target;
- the frontend and launched application's actual process environments, filtered to relevant SDL, audio, display, and PortMaster variables.

Use bounded searches for function and variable names. Do not recursively dump `/opt/muos`, user storage, or complete process environments.

The normal external-port path is conceptually:

```text
muxfrontend/muxplore
  -> frontend content-loader state
  -> mux launch script
  -> assignment INI
  -> external launcher
  -> port launcher
  -> application
  -> mux cleanup
  -> frontend resumes
```

Verify every resolved path on the installed build. A measured MustardOS 2508.4 build (`BUILD_ID=a55cdbe8`) used `/tmp/rom_go`, `/tmp/con_go`, `settings/advanced/swap`, and `ext-general.sh`. The pinned upstream snapshots linked below instead used `/run/muos/content`, `/run/muos/controller`, and `settings/remap/layout`. This drift is why remembered request formats and settings must not be written or treated as stable APIs.

Official upstream references:

- [MustardOS internal launch snapshot](https://github.com/MustardOS/internal/tree/807c51e46c29c34f45e12c1a26f0212f06d2abb3/script)
- [MustardOS frontend input snapshot](https://github.com/MustardOS/frontend/blob/876f00d5499a2f6a5e76e52c2b711b478980feb2/common/platform/input.c)
- [MustardOS control schemes](https://muos.dev/tour/modules/muxcontrol)

The [dispatcher snapshot](https://github.com/MustardOS/internal/blob/41c21d10127120ffc10a57ead83bbe01eb1625c7/script/var/boot.sh#L242-L268)
waits for `SAFE_QUIT` after its frontend child exits. If an owned isolated
diagnostic stopped that child, resuming the parent alone can leave it waiting.
Inspect the installed dispatcher, complete only its confirmed exit handshake
during cleanup, and verify a responsive frontend. Handshake paths vary by build.

## Resolve controller semantics

Keep these paths separate:

```text
physical control
  -> evdev event
  -> SDL raw joystick index
  -> selected controller-database entry
  -> SDL GameController semantic
  -> frontend or PortMaster translation
  -> application action
```

muOS can select different controller databases for modern and retro layouts. The selection setting and runtime selection file are version-specific. `dpad_swap` is a separate hardware/firmware D-pad-versus-stick behavior and must not be interpreted as the face-button layout.

Before injecting frontend input, read the device's codes under
`/opt/muos/device/config/input/code/{button,dpad}/` and the layout setting. On
2601.0 Jacaranda (RG35XX-SP), the codes were `a=304 b=305 x=307 y=306`, with the D-pad
on ABS 16/17. `settings/advanced/swap=1` swapped the frontend actions relative
to those names: 305 confirmed, 304 went back, and 307 ran the footer's Y action.
The footer labels name actions, not codes. PortMaster's patcher on the same
device also took 305 as A.

The frontend and a PortMaster application may not use the same final mapping. The external launcher can export an SDL mapping, then PortMaster's `control.txt` can select or overwrite it before starting the game. Capture the final application environment or run the SDL probe through the same launch chain. An SSH shell's environment and the database symlink observed before launch are not sufficient.

The pinned muOS frontend source supports mapped SDL GameController devices and a raw-joystick fallback. A virtual controller may therefore be classified differently from the physical controller or become an extra rather than the primary device. Confirm the active mapping and the visible result after each injected action.

Before compiling an input helper, run the capability probe. The measured 2508.4 image already shipped `evemu-describe`, `evemu-device`, `evemu-record`, `evemu-play`, `evemu-event`, and `evtest`; use those installed tools for an exact-device experiment when they meet the evidence requirement. Do not assume later or earlier images contain them.

On the measured 2508.4 image, `muxfrontend` did not open uinput or evemu
devices created after the frontend had started. A matching name and capability
set was not enough. For bounded frontend automation on that image, first check
whether the installed `evemu-event` can write to the existing measured
`muOS-Keys` event node already opened by the frontend. If it can, inject one
press/release pair at a time with `--sync`, using only raw codes recorded for
that exact target, and capture the visible result after each action. The same
node can be used after the normal frontend handoff only after confirming the
launched application has opened it. Always send the release event, even when
the expected screen transition does not occur.

Do not restart `muxfrontend` merely to make a newly created virtual controller
visible. If the existing node is unavailable, not writable, or not fully
measured, use another firmware-supported input path or stop the automation.

An SDL trace proves delivery to that SDL consumer; also verify that the frontend moved as intended. Grid layouts can remap navigation axes, and repeated events can advance multiple items. Measure single-step navigation separately from sustained gameplay axes.

A new `muxfrontend` process can open a clone created during gameplay. After
an app exits, re-identify the foreground consumer and inspect a fresh capture
before sending more input: an exit chord may close the whole app rather than
return to its library. Neutralize and remove app-only clones before continuing
frontend navigation.

Never translate `JSIOCGBTNMAP` indexes into SDL indexes. The legacy joystick API can omit or order keys differently from SDL. On a measured H700 build, SDL's raw ordering included Escape and volume keys before face buttons; only the target SDL probe exposed the indexes used by the application.

## Launch and capture

Launch through the frontend loop's content loader, which is what menu
selection and boot-to-last use. On the traced 2508.4 build, `frontend.sh` runs
`launch.sh` whenever `/tmp/rom_go` is non-empty. Boot-to-last fills it with
`cat <content>.cfg`, plus `<content>.gov`/`.con` (or `core.gov`/`core.con`)
into `/tmp/gov_go` and `/tmp/con_go`. The frontend writes
`/opt/muos/share/info/core/<System>/<Name>.cfg` on the item's first menu launch.
`muxfrontend` exits when `/tmp/safe_quit` exists or on USR1/TERM. The loop then
runs the loader in the original `frontend.sh` and its environment, and returns
to the launcher afterwards:

```sh
CFG=/opt/muos/share/info/core/Ports/<Name>.cfg
MUX=$(pidof muxfrontend)
[ -s "$CFG" ] && [ -n "$MUX" ] && [ ! -e /tmp/rom_go ] && ! pgrep -f "mux/launch.s[h]" >/dev/null || exit 1
cat "$CFG" >/tmp/rom_go
for T in gov con; do
	F="${CFG%.cfg}.$T"; [ -e "$F" ] || F="$(dirname "$CFG")/core.$T"
	[ -e "$F" ] && cat "$F" >"/tmp/${T}_go"
done
: >/tmp/safe_quit
kill -USR1 "$MUX"
```

Verified on 2508.4 (RG35XX-H, 2026-10-30): `frontend.sh` -> `launch.sh` ->
port, correct rendering and controller, normal exit back to the launcher.
`launch.sh` clears the framebuffer, applies the governor and control scheme,
and restores fb mode, gptokeyb and rumble afterwards. Running a port's `.sh`
directly from SSH skips all of that while `muxfrontend` keeps the display and
input. Do not restart the loop with `FRONTEND stop`/`start` from SSH: the new
`frontend.sh` inherits the SSH environment. Use `pidof muxfrontend`, not
`pgrep -x`: BusyBox matches `-x` against argv0, which is the full path, so
`pgrep -x muxfrontend` (also used by `GET_FRONTEND_PIDS`) finds nothing.

On an RG35XX-SP muOS build, `fbgrab` of an idle frontend can return a uniform white image. `/opt/muos/config/boot/last_play` then still names the last launched content, which the frontend highlights after that content exits; confirm the launched process hash after pressing confirm instead of trusting the highlight.

After selection:

1. verify the frontend-to-launcher-to-application process chain;
2. verify the installed application artifact hash;
3. wait for an application readiness signal such as the expected process, log marker, or changed frame;
4. capture a bounded series when the first frame is black;
5. perform only the semantic input needed by the current claim;
6. exit through the application when possible;
7. verify application exit, PortMaster cleanup, restored framebuffer mode, and a responsive frontend.

The mux launch script normally restores runtime state such as the governor, framebuffer mode, rumble, and owned gptokeyb processes. Verify the installed cleanup code and final state instead of assuming that a returned launcher process proves restoration.

## Silence audio

The volume buttons run `/opt/muos/script/device/audio.sh U` and `D`. The script
sets the PipeWire default sink with `wpctl` in `settings/advanced/incvolume`
steps and saves the level as `settings/general/volume`; use that path. On a
measured RG35XX-H build the codec also exposes an `SPK` switch (the speaker
amplifier). The buttons never touch it, so switching it off leaves the speaker
silent at every volume. Do not change it.

1. Source `/opt/muos/script/var/func.sh` (it also sets `XDG_RUNTIME_DIR` for
   `wpctl`) and record `GET_VAR config settings/general/volume`.
2. Silence with `/opt/muos/script/device/audio.sh 0`.
3. Before handing the device back, run `audio.sh <recorded level>` and check
   `wpctl get-volume @DEFAULT_AUDIO_SINK@`.

## Record reusable evidence

Store a sanitized, versioned target record with:

- muOS version/build and board name;
- hashes of the inspected launch scripts and SDL library;
- resolved controller database and relevant layout setting;
- physical evdev identity and capabilities;
- raw SDL indexes and final controller mapping under the real application environment;
- capture method and frontend restoration evidence.

Treat the record as a measured example. Recheck drift-prone paths and mappings after every firmware or PortMaster update.
