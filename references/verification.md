# Verification

Use the smallest proof that answers the current question, but do not skip layers when making a release or compatibility claim.

## Proof ladder

1. **Source/static:** review, formatting, lint, host unit tests.
2. **Built:** correct architecture, interpreter, dependencies, and symbols.
3. **Packaged:** official package layout and PortMaster checks pass.
4. **Copied:** expected archive or files reached the target.
5. **Installed:** fresh install completed and installed hashes/permissions match.
6. **Frontend-launched:** the real frontend handed off to the real PortMaster launcher.
7. **Rendered:** a current capture shows the intended application state.
8. **Input-observed:** measured semantic controls cause the expected transitions.
9. **Functional:** task-specific behavior works, exits cleanly, and restores the frontend.
10. **Physical/device coverage:** the declared CFW, hardware, resolution, and architecture matrix was exercised.

State the highest layer actually proven. A screenshot cannot prove controller behavior, audio quality, frame pacing, save persistence, or online gameplay.

## Match proof to the change

Do not turn every device regression into a full hardware certification pass. Choose the smallest proof that covers the changed subsystem and the claim:

- **Metadata or package-only change:** source and official package checks; install only when layout or updater behavior changed.
- **Renderer, asset, or runtime change:** exact installed hash, normal frontend launch, the affected state visibly rendered, one application-visible transition when needed to prove responsiveness, clean exit, and frontend restoration.
- **Input change or controller-compatibility claim:** the relevant input gates below, including application-visible actions.
- **Setup, patching, or installer change:** the fresh-install gate.
- **Performance claim:** a controlled before/after measurement at the layer named by the claim.

Expand the matrix only when the change can affect that subsystem, a release claim requires it, or earlier evidence exposes a regression. Record untested layers instead of reverse-engineering an unrelated subsystem merely to raise the proof level.

## Experiment record

Before acting, write:

- hypothesis and competing explanations;
- exact local artifact/hash;
- exact installed artifact/hash;
- CFW/device/PortMaster versions;
- preconditions and user-owned state to preserve;
- action sequence and timeouts;
- expected observable transition;
- logs, captures, process state, and cleanup evidence.

Afterward record deviations and uncertainty. Do not silently rerun until one attempt appears successful.

When levels, spawns or routes vary between runs, steer scripted play by in-game feedback (for example depth or region) and compare normalized measures, such as cost per unit of work, alongside whole-run totals. Run memory-heavy device tests only while no trial owns the device; concurrent runs fail with misleading allocation errors.

Arms switched by time within one session measure the scene as much as the change once the
player moves. Compare memory or steady-state changes as whole sessions on the same scripted
route, in interleaved pairs; switching such a setting mid-session (for example mlock) adds
its own transient.

## Input gates

Test separately:

- initial controller discovery;
- face-button positions and d-pad;
- both sticks and axis polarity/dead zone;
- shoulders, analog/digital triggers, Start/Back/Guide, and stick clicks;
- holds, repeats, chords, and simultaneous axes;
- controller disconnect/reconnect and destruction with held state;
- frontend exit chord and frontend restoration.

Use application-visible results or SDL event traces. Raw evdev output alone proves only the input-source layer.

## Visual and timing gates

- Confirm capture source, timestamp, dimensions, and active display plane.
- Use a video or repeated captures plus timestamps for animation/frame-pacing claims.
- Framebuffer and KMS buffer captures read whole buffers and never show tearing. On
  Allwinner BSP kernels (sunxi disp2), `echo /tmp/f.bmp >
  /sys/class/disp/disp/attr/capture_dump` writes one frame of display-engine output
  (about 1 s each); a split there is a software tear, none means it is after the display
  engine.
- Distinguish renderer cadence, game update cadence, input polling, and display refresh.
- Diagnostic captures (readback plus PNG encoding) add to swap and render-thread time;
  take timings from runs without them.
- Retain numerical frame/queue/latency metrics for streaming or media work.

Keep frequently polled diagnostic control files on a
[verified tmpfs](https://docs.kernel.org/filesystems/tmpfs.html).
Rate-limit or remove polling, including file open/close operations, during
benchmarks. Validate a clean launch separately from the instrumented run.

## Memory and CPU counters

zram stores pages it cannot shrink uncompressed (`mm_stat` column 8, `huge_pages`, where
present): swapping already-compressed data (block-compressed textures, compressed stores)
frees nothing and costs a fault per touch. Keep such data resident (mlock) instead.
Attribute major faults per thread before blaming one subsystem.

Cortex-A53 stall attribution (implementation events, TRM): `0xE1` issue queue empty on an
I-cache miss, `0xE2` on an I-uTLB miss, `0xE7` Wr stall on a load miss, `0xE8` on a store,
`0xE4`-`0xE6` interlocks. A55 numbers differ.

On Bifrost libmali (r20p0, g2p0), a GPU write (transform feedback, `glCopyBufferSubData`)
into a buffer that queued draws read makes the calling thread wait for them; give such
writes their own buffers. Each render pass costs hundreds of microseconds of driver CPU
regardless of size.

## Clock controls

Record online CPUs, process affinity, governors, frequency limits and thermal
cooling states before and after measurements. A [CPUFreq policy maximum](https://github.com/torvalds/linux/blob/v4.4/drivers/cpufreq/cpufreq.c#L560-L620)
may include a thermal constraint; writing it back can retain that cap as a user
limit after cooling. For fixed-clock tests, prefer a supported
[userspace frequency request](https://docs.kernel.org/admin-guide/pm/cpufreq.html#userspace),
preserve policy limits and thermal protection, and restore prior settings.
Verify attained clocks and distinguish controlled-clock results from stock behavior.

## Audio gates

- Confirm device/server selection and sample format.
- Test distinct effects, overlapping effects, music, pause/resume, device loss, and repeated sessions.
- A process writing to ALSA/PipeWire does not prove audible, non-repeating output.
- Respect the user's physical volume and environment; never force output volume.

## Networking and multiplayer gates

Separate:

- authentication/account creation;
- lobby and matchmaking state;
- signalling delivery;
- NAT discovery;
- direct peer or relay packet flow;
- in-match gameplay state;
- voice capture, delivery, decoding, and playback.

For direct-peer games, a server log saying a signal was delivered does not prove gameplay UDP connectivity. When testing multiple devices, preserve independent timestamps and packet-path evidence.

## Fresh-install gate

A development sync does not cover first-run setup. Test the release archive from a known clean port installation while preserving separate user saves and game data. Verify required user-supplied files, patching, config creation, error dialogs, relaunch, update behavior, and uninstall/reinstall behavior.

Do not remove an existing installation or reset state without explicit authorization.
