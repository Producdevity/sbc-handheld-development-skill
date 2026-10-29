# SpruceOS on Miyoo Flip

Do not confuse the Miyoo Flip with the Miyoo Mini Flip. SpruceOS and CrossMix
are also not interchangeable profiles: CrossMix targets TrimUI hardware, while
Miyoo Flip adaptations changed device paths, display handling, and
configuration. Detect the installed firmware and inspect its lifecycle.

## Target and remote access

Current SpruceOS detects the Flip from the `0xd05` CPU part and selects an
aarch64, 640x480 RK3566 profile. Its SD-card root is `/mnt/SDCARD`. Verify these
markers rather than inferring them from a hostname.

Spruce persists network-service settings in
`/mnt/SDCARD/Saves/spruce/spruce-config.json`. When SSH is enabled,
`networkservices.sh` starts Dropbear after Wi-Fi connects. The `spruce` account
uses `/mnt/SDCARD` as its home, so its persistent key file is
`/mnt/SDCARD/.ssh/authorized_keys`. Verify effective permissions and batch-mode
login. Current PyUI exposes the toggle under **Settings -> Additional Settings
-> Network Settings -> Enable SSH**; older builds used an SSH app.

On a measured SpruceOS 4.1.2 Flip, the vendor init script launched
`/usr/sbin/dropbear -R` with `/etc/dropbear` linked to volatile
`/var/run/dropbear`, causing the host key to change after reboot. The Spruce
service attempted to stop `sshd`, while the process was named `dropbear`, so its
persistent `dropbearmulti` keys did not take over port 22. Treat this as a
versioned observation. Do not hide a changed fingerprint with
`StrictHostKeyChecking=no` or modify firmware startup without authorization.

When authorized to repair this, check for existing persistent keys before
generating replacements. A later Flip check found the earlier trusted ED25519
key intact but both SSH scripts reverted, so replacing the Mac's known-host
entry would have trusted the temporary server instead of fixing the cause.

- Compare the public key from `dropbearmulti dropbearkey -y -f KEY_FILE` with
  the trusted fingerprint. Never copy or print the private key.
- Back up `spruce/scripts/network/sshFunctions.sh` and
  `spruce/bin/SSH/dropbear-wrapper.sh` on the SD card.
- Generate missing ED25519/RSA keys in `spruce/etc/ssh/keys`, then stop the
  vendor listener with `/etc/init.d/S50dropbear stop`. Stopping `sshd` does not
  release its port on this build.
- Start Spruce's `dropbearmulti dropbear` with explicit persistent `-r` paths
  and a separate `-P /var/run/dropbearmulti.pid`. Stop that listener by its
  verified PID, not by killing SSH sessions indiscriminately.
- In the forced-command wrapper, use `exec /bin/sh -c "$SSH_ORIGINAL_COMMAND"`
  for non-interactive commands; unquoted `exec $SSH_ORIGINAL_COMMAND` breaks
  quoting and compound commands. Preserve its SFTP branch.
- Reboot and verify strict batch-mode login with the same fingerprint, the
  SD-card listener owning port 22, and correct command quoting. Spruce updates
  can overwrite these scripts; recheck their hashes if the problem returns.

## Frontend-owned launch and capture

Normal game and app launches belong to Spruce's `principal.sh` loop. PyUI
writes a command to `/tmp/cmd_to_run.sh` and exits; the loop validates and runs
it, cleans up, and starts PyUI again. Prefer visible PyUI navigation. Do not run
a port beside PyUI or write the command file without explicit authorization and
inspection of the installed loop; it contains executable shell.

### Remote PyUI handoff

When virtual input cannot reach PyUI, use its command handoff after verifying
the installed `principal.sh`, `mainui.py`, and `devices/miyoo_trim_common.py`.
Startup and return to PyUI were verified on SpruceOS 4.3.3 on 2026-09-07:

1. Confirm PyUI is idle, no game or installer is active, and
   `/tmp/cmd_to_run.sh` does not exist. Identify the exact main-mode PyUI PID;
   message windows can use the same executable.
2. Read the item's `config.json`. For an app such as PortMaster, reproduce
   `run_app`: change to its directory and invoke its configured launch script.
   For a port, reproduce `run_game`: invoke the `Emu/PORTS/config.json` launch
   path with the port's `.sh` as its argument. Preserve the `/Emu/PORTS/../..`
   spelling: `standard_launch.sh` extracts the system name from `$0`.
3. Stage the shell-quoted command in a task-specific `/tmp` file, check it with
   `sh -n`, and set mode 700. Publish it using an exclusive hard link to
   `/tmp/cmd_to_run.sh`; never overwrite another queued command.
4. Recheck the PyUI PID's command line. Only when its installed `mainui.py`
   handles SIGTERM by exiting, send TERM to that PID. Leave `principal.sh`
   running so it performs the normal setup and owns the child process.
5. Verify the principal -> firmware wrapper -> port process chain and a current
   capture. After normal application exit, verify command-file removal and
   visible PyUI restoration. If handoff fails, remove only this test's queued
   file after checking its identity and whether the loop has consumed it.

This launches an item through the firmware loop; it does not prove physical
menu navigation. It needs no persistent frontend modification. If the installed
scripts lack this contract, do not improvise a process kill or a direct launch.

Create any needed virtual input device before launching PortMaster: the
measured SDL GUI did not open a keyboard added after startup. Check its TERM
handler and exit controls independently of PyUI's. PortMaster 2026.10.01-0433
(2026-10-29) ignored a uinput keyboard but opened a hot-plugged `xbox360`
semantic gamepad. Spruce enables PortMaster's Xbox A/B swap: A is `face.east`,
B is `face.south`. Probe a harmless button first; the autoinstall dialog logs
`PRESSED <name>` at DEBUG in `PortMaster/pugwash.txt` (the main GUI logs INFO
only). If a port's `arch` is missing from the device capabilities, autoinstall
stops at an "incompatible with your device" prompt with inverted buttons: A
cancels (result 255, zip stays queued), B resumes. The main GUI then shows a
Spruce warning with a countdown; B quits, A confirms.

### Capture

For screenshots, prefer KMS capture through Spruce's bundled FFmpeg. The
generic `fbgrab` may see a stale or unused framebuffer.
[`capture_screen.sh`](../../scripts/capture_screen.sh) tries Spruce's installed
Flip helper, then a BGRA KMS download when its pixel format is incompatible.
PortMaster can own DRM directly; on the measured build both KMS capture and
`fbgrab` returned black while the process and initialization log were healthy.
That is runtime evidence, not rendering proof. With PortMaster 2026.10.01-0433,
KMS capture showed its dialogs and the LÖVE patcher; the helper needs a host
Python with Pillow on `PATH`.

## PyUI input recovery

On the measured 4.1.2 build, PyUI read input only from `/dev/input/event5`. A
hot-plugged uinput controller did not navigate the frontend even when it copied
the physical controller identity.

```sh
frontend_tap.sh HOST release-all
```

The Flip has Nintendo-style printed labels: `face.south` is its printed B and
`face.east` its printed A.

On the measured build, `evtest` observed these events while PortMaster was
running, but PortMaster's SDL controller layer did not act on them. A transient
uinput keyboard did reach PortMaster. Keep frontend, evdev, SDL, and
application-action claims separate.

On a measured 4.2.0 build, direct `sendevent` taps on `event5` produced SDL
button-down events without matching releases. PyUI then processed the held
state as repeated navigation. Do not automate PyUI by writing to its physical
input node. [`frontend_tap.sh`](../../scripts/adapters/spruce/frontend_tap.sh)
is retained only to release every control after an interrupted or older test.
Use the verified remote handoff above when available, otherwise physical
frontend navigation. For a launched SDL application, use a separate uinput
controller and verify its mapping in that process. Read the Ports controller
mode and the effective SDL database: this Flip's Nintendo mode maps `a:b1`,
`b:b0`, `x:b3`, `y:b2` for the Xbox 360 GUID. Do not reuse another CFW's mapping.

Sources:

- [SpruceOS Miyoo Flip platform profile](https://github.com/spruceUI/spruceOS/blob/main/spruce/scripts/platform/Flip.cfg)
- [SpruceOS frontend and game loop](https://github.com/spruceUI/spruceOS/blob/main/spruce/scripts/principal.sh)
- [SpruceOS network services](https://github.com/spruceUI/spruceOS/blob/main/spruce/scripts/networkservices.sh)
- [SpruceOS SSH implementation](https://github.com/spruceUI/spruceOS/blob/main/spruce/scripts/network/sshFunctions.sh)
- [SpruceOS app documentation](https://github.com/spruceUI/spruceOS/wiki/13.-Using-Apps)
- [Miyoo Flip RK3566 hardware research](https://github.com/Zetarancio/Miyoo-Flip-Mainline-Linux-Reverse-Engineering)
- [Surwish Miyoo Flip adaptation](https://github.com/Surwish/Surwish-Miyoo-Flip)
