# Contributing

Agents read this skill before every handheld task, so one wrong sentence costs
every later session time. Add only what you have verified, as briefly as the
surrounding text.

## What to add

- A quirk, path, mapping, tool behavior or limit you measured on a device or
  read in the source of the component that decides it.
- A correction of something the skill states wrongly. Replace or delete the
  wrong text; do not add a caveat beside it.

Leave out guesses, unexplained single observations and anything the skill or
its linked upstream documents already say.

## Confidence

- Reproduce the result on the device, or cite the deciding source file at a
  commit or release.
- Scope it to what you tested: device, CFW and build (for example "RG40XX-H,
  ROCKNIX 20260801"), plus the PortMaster version when it matters. Do not
  generalize to other devices or builds.

## Where

Use the most specific existing file:

- one CFW: `references/cfw/<cfw>.md` (create one for a new CFW);
- deployment, launch, capture and logs: `references/device-operations.md`;
- packaging and launcher rules: `references/portmaster.md`;
- controllers and injected input: `references/input-automation.md`;
- crashes and debuggers: `references/debugging.md`;
- performance and hardware claims: `references/verification.md`.

Put it in the section it belongs to; keep each file's structure.

## Writing

Short declarative sentences: what to do, and what was measured where. No
filler, hedging or narrative.

## Check and commit

Run the checks in [README.md](README.md#validate), then commit one finding or
one coherent group per commit, for example `docs(cfw/rocknix): grim capture
socket`. Push or open a pull request only as the repository owner allows.
