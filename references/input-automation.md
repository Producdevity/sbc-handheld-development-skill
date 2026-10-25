# Input and automation

Input passes through several layers:

```text
printed label -> evdev device -> CFW mapping -> SDL -> PortMaster/gptokeyb -> application
```

State which layer an experiment covers. An evdev event does not prove that the application received the intended action.

## Inspect first

Record the physical device name, IDs, capabilities, axis ranges, fuzz/flat values, SDL GUID, active `SDL_GAMECONTROLLERCONFIG`, and PortMaster `sdl_controllerconfig`.

Resolve mappings in this order:

1. run the maintained project probe or `probe_handheld.sh` and check for `evemu`, `evtest`, SDL helpers, and `/dev/uinput`;
2. identify the SDL shared library loaded by the application;
3. trace the real CFW and PortMaster launch chain;
4. capture the final controller database and `SDL_GAMECONTROLLERCONFIG` inherited by the application;
5. run the SDL probe with that library and mapping;
6. only then create a virtual device or inject an action.

Do not use an SSH shell's environment as the application environment. If the first generic input attempt is not classified or produces the wrong action, stop guessing and measure the exact SDL path before another injection attempt.

If the target already provides the complete evemu toolset, prefer a measured evemu description and bounded replay over writing another physical-device clone. Recheck the installed image rather than carrying tool availability forward as an assumption.

```sh
sed -n '1,240p' /proc/bus/input/devices
for path in /sys/class/input/event*/device/name; do printf '%s: ' "$path"; cat "$path"; done
evtest /dev/input/eventX
```

`evtest` may not be installed. Do not infer SDL button indexes from Linux capability-bit order, or printed labels from names such as `BTN_SOUTH` and `BTN_EAST`. `JSIOCGBTNMAP` and `JSIOCGAXMAP` describe the legacy Linux joystick interface only; their indexes are not SDL raw joystick indexes and must never be translated into an SDL mapping.

`EVIOCGRAB`, including `evtest --grab`, isolates only the evdev node it opens. A controller that also exposes `/dev/input/jsN` can still reach a frontend through the legacy joystick interface. Do not treat one `/proc/PID/fd` snapshot as proof of isolation: a frontend can open another interface after hot-plug. Before automated input, either use the CFW's supported frontend handoff and restore lifecycle or prove throughout the test that every interface exposed by the virtual controller is ignored by the frontend. There is no portable command for stopping and restoring every CFW frontend.

The skill also includes two source-level probes:

- [`joystick_map_probe.c`](../scripts/joystick_map_probe.c) prints the legacy Linux joystick maps returned by `JSIOCGAXMAP` and `JSIOCGBTNMAP`.
- [`sdl_controller_probe.c`](../scripts/sdl_controller_probe.c) prints raw SDL joystick capabilities, GUIDs, controller mappings, and both raw and semantic events for a bounded period. It can load an explicit mapping file and select a device by index, name, or GUID.

Compile them with the same sysroot and SDL headers used by the target project. Run the SDL probe with the same shared library and final mapping used by the application; verify the linked library on the target. The probes are not prebuilt binaries.

For example:

```sh
./sdl_controller_probe --mapping-file /path/to/effective-gamecontrollerdb.txt \
  --name 'Controller Name' --watch-ms 5000
```

If PortMaster exports a mapping string rather than only a file, preserve that variable when launching the probe through the same diagnostic path.

`SDL_GAMECONTROLLERCONFIG` may contain several newline-separated mappings.
Read `/proc/PID/environ` as NUL-separated entries and split the selected entry
at its first `=`. Converting the whole environment to lines and filtering by
variable name loses every mapping after the first. Inspect only the relevant
variables; do not dump credentials from the process environment.

## Pick the right input source

| Experiment | Input source |
|---|---|
| Reproduce one physical controller | Measured evemu description and recording |
| Drive a measured frontend that ignores hot-plugged devices | The CFW profile's documented existing-node path |
| Clone a device when `python-evdev` is already installed | `evdev.UInput.from_device(...)` with the measured source node |
| Drive portable SDL semantics | Generic semantic uinput gamepad plus a verified SDL mapping |
| Reproduce a CFW-specific controller path | A project-owned profile that deliberately matches that device |
| Navigate a keyboard-only frontend | Dedicated uinput keyboard |
| Exercise a pointer UI | Dedicated uinput pointer or application touch adapter |
| Test removal with held controls | Persistent uinput device destroyed without first releasing state |
| Verify PortMaster keyboard translation | PortMaster's gptokeyb or gptokeyb2 |

These sources are complementary. Exact cloning is useful for one measured device. A generic controller is better for portable SDL behavior. A profile with unusual axes is appropriate for normalization tests. Keep the profiles and their evidence separate.

## Navigate with feedback

Choose the cheapest observation that establishes the required state:

1. Use a verified frontend or application command interface when it supports the
   operation and preserves the required launch lifecycle.
2. Otherwise, use available menu identifiers, selected-item text, focus, logs or
   application-owned state queries to guide controller input. A custom binary
   observer must match the exact installed build; it is not a portable CFW API.
3. Once a route works, batch its short input sequence from a known starting
   state, then verify the destination. Keep timing-sensitive replay in one
   process or persistent transport. Stop and inspect an unexpected result
   instead of continuing a guessed sequence.

Capture the first unfamiliar screen, visual defects, changed layouts and
unexpected states. Routine traversal of an established route does not need a
capture after every press. Use a bounded readiness check, such as the expected
menu or loaded level, rather than assuming a live process or a fixed delay
means the destination is ready.

A direct level/load command can set up a renderer test where the application
supports it. It does not verify controller navigation or menu behavior; retain
separate input tests for those requirements. Likewise, game-state readers do
not establish that the firmware frontend accepts the same input source.

## Helper commands

Read [input-service.md](input-service.md) when building a semantic device,
writing a timed plan or using evemu. It contains the helper API, example
mapping and command recipes. Complete the target/mapping investigation here
before creating a device or replaying inputs.

## CFW-specific input

- [muOS](cfw/muos.md) documents a measured existing-node path for builds whose
  running frontend ignores newly created uinput and evemu devices.
- [SpruceOS on Miyoo Flip](cfw/spruce.md) documents the measured PyUI event
  path and recovery-only `release-all` helper. Use its verified remote
  handoff or physical controls for frontend navigation.
- [dArkOS](cfw/darkos.md#programmatic-navigation) distinguishes frontend
  navigation, application state readers and isolated diagnostic launches.
- [AmberELEC](cfw/amberelec.md) documents the measured RK3326 GO-Super profile
  and its frontend limitations.

Read a CFW profile only for that installed firmware and measured device. Keep
the shared input protocol positional; do not copy CFW event codes into a
portable plan.

## Measured target profiles

Use [target-profile.schema.json](../schemas/target-profile.schema.json) when an
input result will be reused across sessions. One profile describes one input
consumer, such as a frontend, PortMaster, or the launched application. If the
frontend and application receive different mappings, record two profiles.

The profile records explicit face-button positions, printed labels, evdev
codes, consumer-layer indexes, and the value observed by that consumer. It does
not infer actions such as confirm, cancel, reload, or fire. Keep completed
profiles with the project's test evidence; the skill contains only an
[example](../examples/target-profile.json).

## Reuse measured profiles

Keep a small index under the project's `.agents/input/` linking each device and
input consumer to its measured profile and evidence. Check it at the start of
the next session; do not rediscover a working mapping from button names.

Before replaying cached inputs, compare the installed CFW/kernel, controller
identity, active SDL library hash, complete effective mapping, application
button-layout setting, and injector source hash. For frontend inputs, also
compare the relevant frontend binding/configuration. Locate event nodes by
measured identity, not a cached `eventN` number. A changed or missing value
requires rechecking the affected layer, not guessing a replacement mapping.

Record CFW Modern/Retro settings separately from the application's System/Swapped
setting. A user's reported setting is useful context, not a measured
position-to-action mapping. Some firmwares expose it in configuration; others
only reveal the result through generated SDL mappings or events. Preserve
`unknown` where physical position has not been established.

With matching fingerprints, reuse the established controls and verify one safe,
visible action. Do not toggle system layouts or rewrite the controller database
to make an automation profile fit. Save corrections beside the original
evidence so the next session uses the measured result.

## Evidence

Retain the plan and schema version, plan hash, adapter/source hash, installed application hash, target profile, nominal delays, actual timestamps, marks, and cleanup result. Application-visible behavior or an SDL trace is needed for an application-input claim; raw evdev output proves only the source layer.

Do not store secrets or personal data in plans or logs. Runner output is bounded but not automatically sanitized.
