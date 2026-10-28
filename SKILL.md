---
name: handheld-development
description: Develop, package, debug and validate native Linux ARM handheld apps and PortMaster ports. Use for firmware-aware deployment and launch, controller mapping, profiling and capture on muOS, KNULLI, ROCKNIX, SpruceOS, dArkOS, AmberELEC and related firmware.
license: MIT
---

# Handheld Development

Use the installed device, current firmware and PortMaster checkout as the
source of truth. Device names, mount paths, controller mappings, frontend
behavior and helper availability vary between builds.

## Start with the project

Read repository instructions, current worktree changes, project notes, device
profiles and deploy scripts before reusing historical commands. Before creating
or replacing a probe, launcher, input injector, capture or debugger helper,
search for a maintained project copy:

```sh
python3 "$SKILL_DIR/scripts/discover_artifacts.py" .
```

Set `SKILL_DIR` to this skill's directory. Read candidate helpers and their
adjacent documentation; check target identity, paths, cleanup, timeouts,
provenance and user-data boundaries. Search temporary artifacts only for
interrupted or user-requested investigations, or when maintained helpers are
missing. Bound those searches with `--include-temp`, age, category and project
filters rather than scanning all temporary files.

## Choose the reference

- **Port/package work:** [portmaster.md](references/portmaster.md).
- **Device launch, deployment, capture or logs:** [device-operations.md](references/device-operations.md).
- **Controller investigation or automated input:** [input-automation.md](references/input-automation.md).
- **Native crash, ABI or debugger work:** [debugging.md](references/debugging.md).
- **Hardware or performance claims:** [verification.md](references/verification.md).

Load only references relevant to the current task. Helper commands and timed
input plans are documented separately in [input-service.md](references/input-service.md).

## Establish the target

Reuse project profiles under `.agents/input/` after checking their firmware,
consumer, SDL mapping and injector fingerprints as described in
[reuse measured profiles](references/input-automation.md#reuse-measured-profiles).
For the current task, record the relevant device/CFW build, SoC/architecture,
libc/kernel, display, foreground frontend/compositor, PortMaster version,
installed artifact hash and application/data/save/log paths. Input work also
needs the effective controller layout, SDL library and complete
`SDL_GAMECONTROLLERCONFIG` inherited by the launched application.

Use [probe_handheld.sh](scripts/probe_handheld.sh) for a read-only baseline when
no maintained project probe exists. Discover installed capture, input and
debugger tools before choosing them. Prefer PortMaster's `CFW_NAME`,
`DEVICE_NAME`, `DEVICE_ARCH`, display dimensions, `directory`,
`sdl_controllerconfig`, `GPTOKEYB`, `ESUDO` and `TASKSET`; an SSH alias or mount
path does not establish firmware or controller identity.

## Preserve frontend ownership

Validate behavior through the firmware frontend. Directly executing a port's
`.sh` while the frontend owns display/input can invalidate rendering, mappings,
audio and cleanup. Use direct launches only for isolated diagnostics with a
known frontend suspend/restore path, and label that evidence accordingly.

## Input and automation

Name controls by position, such as `face.south`, `shoulder.left` or
`stick.left.x`, until the active mapping is measured. Printed labels, evdev
`BTN_*` names, SDL semantics and game prompts can disagree; identify the layer.
Use the [input workflow](references/input-automation.md) before injection and
[helper API](references/input-service.md) for semantic devices or timed plans.
Choose measured evemu replay, a verified virtual-device profile or the
application's input path for the actual experiment. Prefer
[state feedback and bounded input sequences](references/input-automation.md#navigate-with-feedback)
for routine navigation; capture images when the visual result matters.

Keep reusable tools in ignored project `.agents/tools/` or `.agents/input/`,
and plans/results in `.agents/evidence/`. Device `/tmp` is for deployed helpers
and transient output. Use bounded plans with per-command timeouts and
`release-all` cleanup. After a failed run, neutralize owned controls and restore
owned frontend, mount and debugger state; keep cleanup bounded and idempotent.

## Authorization and user state

Use existing session authorization. Device development/testing covers scoped
build deployment, launch, input injection, debugging and rollback. Preserve
excluded devices and user data; ask when a material or destructive action
falls outside that scope. Read-only access alone does not authorize mutations.

Silence tests with the normal firmware volume control at 0%; keep the app's
audio engine enabled. Record and restore the original volume before handing
the device back for playtesting. Do not directly disable output routing or
speaker switches: ordinary volume buttons must still unmute it.

Prefer installed tools. If a missing program is required, identify the smallest
package or transient helper, explain its changes and CFW persistence, and ask
before installing or copying it. Avoid general upgrades or cleanup to install
one debugging tool.

If a device is offered but may be busy, make one bounded read-only ownership
check. While an unrelated app is active, continue repository/static work;
do not deploy, inject input, stop that app or repeatedly poll for availability.

## Evidence

Distinguish built, installed, frontend-launched, rendered, input-observed and
physically verified results. State device/CFW coverage and remaining limits.
A screenshot, process, signal log or host test does not prove stable gameplay
or a performance improvement.
