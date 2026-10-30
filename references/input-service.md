# Input helper API

Use this reference after establishing the target and mapping with
[input-automation.md](input-automation.md). It covers helper commands, timed
plans and evemu recipes; device creation and replay still require the measured
firmware ownership/cleanup path.

## Included files

| File | Purpose |
|---|---|
| [`semantic_input.c`](../scripts/semantic_input.c) | Persistent gamepad, keyboard, or pointer with a local command socket |
| [`run_input_sequence.py`](../scripts/run_input_sequence.py) | Runs and records a bounded semantic timeline |
| [`input_sequence_plan.py`](../scripts/input_sequence_plan.py) | Validates and normalizes plans |
| [`input-sequence.schema.json`](../schemas/input-sequence.schema.json) | Plan contract for editors and CI |
| [`input-sequence.json`](../examples/input-sequence.json) | Gamepad plan example |
| [`pointer-sequence.json`](../examples/pointer-sequence.json) | Pointer plan example |

The skill does not bundle `evemu-*`, `evtest`, gptokeyb, SDL, or CFW launch helpers. Those come from evemu-tools, PortMaster, the target CFW, or the project runtime.

## Semantic input service

Build [`semantic_input.c`](../scripts/semantic_input.c) with the project's existing cross toolchain:

```sh
arm-linux-gnueabihf-gcc -O2 -Wall -Wextra -o semantic_input semantic_input.c -lm
```

Use the matching aarch64 compiler for aarch64 targets. Do not install a compiler on a handheld for this helper.

Start exactly one device per process:

```sh
./semantic_input serve gamepad /tmp/handheld-gamepad.sock
./semantic_input serve gamepad /tmp/handheld-gamepad.sock 750 rk3326-go-super
./semantic_input serve gamepad /tmp/handheld-gamepad.sock 750 xbox360
./semantic_input serve keyboard /tmp/handheld-keyboard.sock
./semantic_input serve pointer /tmp/handheld-pointer.sock
```

The optional registration delay is in milliseconds, up to 10000. The default is
750. A gamepad may also select a profile after the delay. `generic` is the
default; `rk3326-go-super` reproduces the measured controller exposed by RK3326
GO-Super drivers; `xbox360` uses the standard wired Xbox 360 identity and
layout. A matching identity still requires the target SDL mapping to be
verified before input is sent.

The Xbox profile uses `BTN_X` for west and `BTN_Y` for north. Linux aliases
these to `BTN_NORTH` and `BTN_WEST`, respectively; reusing the generic profile's
positional codes would swap X and Y under SDL's Xbox mapping.

Send commands from another process:

```sh
./semantic_input send /tmp/handheld-gamepad.sock down face.south
./semantic_input send /tmp/handheld-gamepad.sock axis stick.left.x 1
./semantic_input send /tmp/handheld-gamepad.sock release-all

./semantic_input send /tmp/handheld-keyboard.sock down key.enter
./semantic_input send /tmp/handheld-pointer.sock move pointer.x 20
./semantic_input send /tmp/handheld-pointer.sock down pointer.primary
```

Gamepad controls use these positional names:

- `face.south`, `face.east`, `face.west`, `face.north`
- `dpad.up`, `dpad.down`, `dpad.left`, `dpad.right`
- `shoulder.left`, `shoulder.right`, `trigger.left`, `trigger.right`
- `button.back`, `button.start`, `button.guide`
- `stick.left.press`, `stick.right.press`
- `stick.left.x`, `stick.left.y`, `stick.right.x`, `stick.right.y`

Axis values follow evdev and SDL: positive X is right, positive Y is down. Confirm
in-game polarity with one isolated move and an observed result; a modal opened by
an earlier step can make later moves look inverted.

 Keyboard controls include `key.a` through `key.z`, `key.0` through `key.9`, navigation keys, Enter, Escape, Space, Tab, Backspace, and left Ctrl/Alt/Shift. Pointer controls include three buttons and relative X, Y, vertical wheel, and horizontal wheel movement.

`release-all` returns every declared control to neutral. `quit` releases controls and removes the device. `destroy` skips the helper's release step and unregisters the device while it may still be held; use it only for an explicit held-state hot-unplug test. The kernel may emit synthetic release events while unregistering the device, so record the evdev sequence rather than assuming observers receive no release.

The gamepad IDs normally produce this SDL2 mapping entry:

```text
03000000091200000100000001000000,Handheld Development Gamepad,a:b0,b:b1,x:b3,y:b2,back:b6,guide:b8,start:b7,leftstick:b9,rightstick:b10,leftshoulder:b4,rightshoulder:b5,lefttrigger:a2,righttrigger:a5,leftx:a0,lefty:a1,rightx:a3,righty:a4,dpup:h0.1,dpright:h0.2,dpdown:h0.4,dpleft:h0.8,platform:Linux,
```

Confirm the GUID and event mapping with the target's SDL build. Add the mapping only to the development process being tested; do not replace the frontend-generated controller database.

The GUID can differ across SDL versions and joystick backends even when the uinput identity is unchanged. Replace the example GUID with the value printed by `sdl_controller_probe` and verify SDL button/axis indexes with that SDL probe. Use `joystick_map_probe` only for the separate legacy joystick interface.

## Timed plans

The JSON Schema is the contract for humans, editors, CI, and the runner. Validate a plan, then pass an adapter after `--`:

```sh
python3 run_input_sequence.py input-sequence.json --dry-run

python3 run_input_sequence.py plan.json --log result.jsonl -- \
  ./semantic_input send /tmp/handheld-gamepad.sock

python3 run_input_sequence.py plan.json --log result.jsonl -- \
  ssh target /tmp/semantic_input send /tmp/handheld-gamepad.sock
```

The adapter receives one of:

```text
down CONTROL
up CONTROL
axis CONTROL VALUE
move CONTROL VALUE
release-all
```

Plans support `wait`, `mark`, `tap`, `hold`, `chord`, `down`, `up`, `axis`, and `move`. A `mark` writes a named log record; it does not capture or verify state. Hold and delay durations begin after the preceding adapter command returns, so adapter startup does not shorten them. `after_ms` delays the next step. An axis step with `duration_ms` returns the axis to zero. Each command has a timeout, the complete plan has a runtime limit, and failure cleanup calls `release-all`.

Keep target-state verification outside the input plan. A project test can run a
separate observer around the replay or consume its marks, screenshots, logs, or
instrumentation. Do not give a portable input plan arbitrary callback or shell
execution fields.

A plan must match its adapter. Do not send a pointer plan to a gamepad process. A project adapter may route several device types while preserving the same command contract.

Keep SSH setup and virtual-device creation outside a timing-sensitive plan. A new SSH process per command is convenient but adds latency; timing experiments should use one persistent transport.

`--dry-run` validates and prints the normalized timeline. It does not test a device, mapping, or adapter.

## evemu

The external evemu-tools package provides these commands:

```sh
evemu-describe /dev/input/eventX > controller.evemu
evemu-record /dev/input/eventX > sequence.events
evemu-device controller.evemu
evemu-play /dev/input/eventY < sequence.events
```

The `.evemu` description defines device identity and capabilities. The `.events` file contains timestamped input. Some `evemu-play` versions can create a device from a complete recording but may prompt. Automation should create the described device explicitly, record the assigned event node, replay the events, and always tear it down.

Start timed replays at `0.000001`, not `0.000000`. A zero first timestamp can
collapse the first hold, leaving later movements relative to the wrong
position. Shift all timestamps by one microsecond when normalizing a recording;
preserve their intervals and matching releases. This is an
[upstream-documented evemu behavior](https://android.googlesource.com/platform/frameworks/native/+/b5d245390fc6aa4119e7ce3a2f398254369838e6/cmds/evemu-record/main.rs).

Probe permissions for both `/dev/uinput` and the event node created by `evemu-device`. A CFW may allow unprivileged uinput creation but restrict the resulting `/dev/input/event*`; in that case, use its normal privilege wrapper consistently for device creation, replay, and teardown.

Use `evemu-event` only with a known node and measured event code. Raw codes belong in a target profile, not a cross-device plan.
