# AmberELEC device operations

Inspect the installed release and device profile before using RG351MP or R36S
paths. Community R36S images can report different hardware and firmware
identities at different layers.

## Access and frontend lifecycle

Enable SSH under **Main Menu -> Network Settings -> Enable SSH**. Official
images use `root` with the default password `amberelec`; upgraded 351ELEC
installations may still use `351elec`. The root filesystem is read-only and
`/storage` is persistent. Root's home is `/storage`, so authorized keys belong
under `/storage/.ssh`; apply `0700` to the directory and `0600` to the file,
then verify batch-mode login.

AmberELEC manages EmulationStation with `emustation.service`, not
`emulationstation.service`. Normal launches run through EmulationStation and
`/usr/bin/runemu.py`. For an explicitly authorized isolated test, use the
installed unit's stop/start lifecycle, then verify the unit, process, and
framebuffer. Do not launch EmulationStation directly.

On a measured R36S prerelease image, the device tree identified R35S/R36S while
the AmberELEC image profile, hostname, and `/storage/.config/.OS_ARCH`
identified RG351MP. PortMaster therefore reported `DEVICE_NAME=RG351MP`.
Record both layers. The installed PortMaster paths were
`/storage/roms/ports/PortMaster` and its `/roms/ports/PortMaster` alias;
`fbgrab` captured the stable 640x480 frontend. On the measured 4.4.189
kernel, capturing during a DRM display transition caused a kernel fault in
`rockchip_fbdev_mmap`. Avoid `fbgrab` during launch/exit. It also misses SDL
KMSDRM ports such as Unity (`/dev/fb0` keeps the console): use
`/sys/kernel/debug/dri/0/clients` (DRM master) and repeated `summary` reads
(cycling scanout address) as presentation evidence, and application readback
for content. The measured R36S prerelease-20250515 image enables a 384 MiB
swapfile; record `/proc/swaps`.

The normal launch path is `EmulationStation -> runemu.py -> port launcher`.
Before navigating menus, probe `http://127.0.0.1:1234/caps` over SSH with a
short timeout. [HTTP-enabled builds](https://github.com/AmberELEC/emulationstation/blob/e3846751ce50fdced1f2bbd7a5bb51f4da2e7007/es-app/src/services/HttpServerThread.cpp#L520)
provide `GET /reloadgames` and `POST /launch` (absolute ROM path, `text/plain`);
launch enters the normal frontend path. Verify the installed API first. On
R36S prerelease-20250515, `GET /reloadgames` then `POST /launch` with
`/storage/roms/ports/NAME.sh` started a PortMaster port through `runemu.py`;
after SIGTERM to the port, EmulationStation was DRM master again.

`/storage/roms` is exFAT on that image, so `rsync -a` fails every `chown`
(exit 23) while still copying the data. Use `rsync -rlt`.

New ports may need **Start -> Game Settings -> Update Gamelists** before
appearing in the frontend.

The installed `screensaver.sh` watches the physical controller node. Its idle
timeout can offline CPU cores even while a patcher is busy; virtual-pad input
does not reset it. Use measured physical-node activity for long tests and check
the online CPU mask. On the measured build, wake restored cores 2/3 but left
core 1 offline.

High-rate physical-node replay can dominate benchmarks: this build forks
`date` for every event. Measure watcher CPU and actual camera motion; neither
replay rate nor one injected axis event proves a held stick.

PortMaster returned to the Ports list. Its launcher logged a failed attempt to
restart the absent `oga_events.service`, but EmulationStation remained active.
Treat that warning as installed PortMaster behavior, not proof of failed
restoration.

Legacy R36S DTBs can expose `odroidgo3-keys` where `volume_sense.sh` expects
`rg351-keys`. Their model name can also skip the image's RG351MP boot audio
initialization.

## RK3326 input profile

On that R36S build, a generic keyboard arrow opened EmulationStation's input
configuration instead of navigating. The frontend accepted the
`rk3326-go-super` profile from
[`semantic_input.c`](../../scripts/semantic_input.c) because it matched the
installed controller. Use it only while the physical device reports:

```text
name=GO-Super Gamepad
bus=0019 vendor=484b product=1100 version=0100
axes=ABS_X,ABS_Y,ABS_RX,ABS_RY range=-1800..1800 fuzz=32 flat=32
```

Also compare `/storage/.config/emulationstation/es_input.cfg`, the legacy
joystick maps, and SDL's live mapping. EmulationStation and a PortMaster
application can assign different actions to the same raw button. Keep each
press and release in one bounded remote action and remove the cloned device
before reporting success.

Official references:

- [AmberELEC network access and credentials](https://amberelec.org/guides/getting-to-know-amberelec.html#accessing-the-handheld-over-a-network)
- [AmberELEC menu reference](https://amberelec.org/guides/menus)
- [AmberELEC supported devices](https://github.com/AmberELEC/AmberELEC#supported-devices)
