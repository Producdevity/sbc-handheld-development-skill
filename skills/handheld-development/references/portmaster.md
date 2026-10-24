# PortMaster work

Use the current upstream `PortMaster-New` instructions, PortMaster website documentation, `PortMaster-GUI` source, and recent accepted ports of the same engine/runtime. Installed CFW files win when they differ from upstream source.

## Package contract

A new port normally has this shape:

```text
ports/<name>/
  port.json
  README.md
  gameinfo.xml
  cover.jpg or cover.png
  screenshot.jpg or screenshot.png
  Port Name.sh
  <name>/
    licenses/
```

Follow the exact current schema and builder rather than copying this sketch literally. Check:

- lowercase payload directory and a correctly named top-level launcher;
- `gameinfo.xml`, `port.json`, README, cover, and 640x480 screenshot agreement;
- flat license files for every bundled or linked component;
- LF line endings for `.sh` and `.gptk` files;
- no `.DS_Store`, nested duplicate payload, `.gitkeep`, build cache, or source-control metadata;
- no raw file over the current PortMaster size limit;
- exact architecture, resolution, availability, and runtime metadata;
- launcher committed as a regular file; repair executable bits for shipped target binaries at launch when needed.

Run PortMaster-New's current checks and official archive builder. Do not hand-build a zip if the project already integrates those tools.

## Launcher contract

Use the established control-folder discovery. Then:

1. source `control.txt`;
2. set flags needed by the CFW module, such as `PORT_32BIT`, before sourcing `mod_${CFW_NAME}.txt`;
3. source only documented PortMaster helpers;
4. call `get_controls`;
5. derive the game directory from `/$directory/ports/...`;
6. redirect only the app's own HOME/XDG/save paths;
7. export `SDL_GAMECONTROLLERCONFIG="$sdl_controllerconfig"` for SDL game-controller consumers;
8. use `$GPTOKEYB` or `$GPTOKEYB2` only when the port needs translation or an exit chord;
9. call `pm_platform_helper` immediately before launching the executable;
10. wait for the application and end through `pm_finish`.

Do not add a competing trap or broad `pkill` cleanup. PortMaster owns gptokeyb cleanup and CFW-specific finalization.

Use `$ESUDO` instead of hardcoding `sudo`. Use `bind_directories` or `bind_files` when PortMaster supplies them; symlinks are not reliable on every exFAT-backed home or ROM volume.

## Dependencies and runtimes

- Prefer the exact PortMaster runtime key when an official runtime provides the dependency.
- Do not bundle SDL2, GPU drivers, libc, or other core system libraries.
- Bundle a library only after `readelf`/`ldd` and target evidence show that supported CFWs do not provide a compatible one.
- Record provenance and license terms for patches, runtimes, libraries, and assets.
- Keep 32-bit and 64-bit dependencies separate and verify the interpreter and symbol-version requirements.

## Controls

`get_controls` and the frontend-generated SDL database are the compatibility layer. Do not replace them with device-model hardcoding.

Use native SDL game-controller input when the application supports it. Use gptokeyb for keyboard/mouse translation, controller emulation, text entry, or a managed exit chord. A `.gptk` mapping describes the game's logical actions. The firmware and PortMaster provide the physical-device mapping.

## Development deploys

Prefer two explicit paths:

- **Release-install test:** build the real PortMaster archive and queue it in the CFW's discovered autoinstall directory. Open PortMaster from the frontend to process it.
- **Fast development sync:** stage files with temporary names, validate destination roots, preserve user game data/config/saves/logs, then rename atomically where the filesystem supports it.

Do not use `rsync --delete` without narrow excludes for user-owned data. Do not treat a direct file sync as proof that a fresh PortMaster installation works.

### SpruceOS

SpruceOS's PortMaster integration is unofficial and its own documentation describes port compatibility as hit-or-miss. On Miyoo Flip, the current launcher keeps PortMaster under `/mnt/SDCARD/Persistent/portmaster`, ports under `/mnt/SDCARD/Roms/PORTS`, and its home under `/mnt/SDCARD/Saves/flip/home`. It replaces generated `control.txt` files when PortMaster starts, so change the source integration or the port itself, not a generated copy. Verify input, architecture, libraries, and frontend return on the device before claiming support.

## Submission matrix

Use the current PortMaster-New matrix. At minimum distinguish:

- aarch64 and armhf;
- glibc and older-kernel limitations;
- muOS, KNULLI, ROCKNIX, AmberELEC, ArkOS, dArkOS variants, and other declared CFWs;
- 640x480, widescreen, square, rotated, and external-display behavior;
- no-stick, one-stick, and two-stick devices where controls depend on them.

Unsupported combinations belong in metadata and user documentation, backed by a concrete limitation.

## Current primary sources

- <https://portmaster.games/porting.html>
- <https://portmaster.games/packaging.html>
- <https://portmaster.games/gptokeyb-documentation.html>
- [PortMaster-New agent instructions](https://github.com/PortsMaster/PortMaster-New/blob/main/AGENTS.md)
- [PortMaster-GUI `control.txt`](https://github.com/PortsMaster/PortMaster-GUI/blob/main/PortMaster/control.txt)
- [PortMaster-GUI `funcs.txt`](https://github.com/PortsMaster/PortMaster-GUI/blob/main/PortMaster/funcs.txt)
- [PortMaster-GUI CFW modules](https://github.com/PortsMaster/PortMaster-GUI/tree/main/PortMaster) (`mod_${CFW_NAME}.txt`)

Read these from the public upstream repositories rather than assuming a local checkout exists. For reproducible work, record the upstream commit and use commit-pinned links in validation notes.
