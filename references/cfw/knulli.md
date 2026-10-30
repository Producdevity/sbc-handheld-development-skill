# KNULLI device operations

Inspect the installed release before using a remembered Batocera or KNULLI
path. Services, persistence, storage filesystems, and frontend helpers vary
between releases.

## Frontend-owned launch

The EmulationStation loopback web service can expose state such as `/isIdle`
and `/runningGame` when enabled. Probe the installed service before using it.
On one measured build, `POST /launch` launched the entry already selected in
the UI rather than the path supplied in the request body. Navigate the visible
frontend, then verify the reported game and process tree.

Some builds provide `/etc/init.d/S31emulationstation` with `stop`, `start`,
`suspend`, and `resume` actions. Inspect that script before an explicitly
authorized isolated test. Never start `emulationstation` directly. A successful
`start` return is not restoration proof; wait for the normal process chain and
responsive frontend.

## SSH and persistence

Starting with Scarab, SSH is a service enabled under **System Settings ->
Services**. The documented account is `root`. The default password is `linux`,
but Security settings expose the effective password and security enforcement
can change it.

KNULLI keeps user data under `/userdata`; system changes outside it are not
persistent unless deliberately preserved. On the measured RG40XX-H build
`/userdata` is exFAT through FUSE: run `sync` after restoring launchers or
deleting staged files, or a hang can revert them. Before installing an authorized key,
inspect both `/root/.ssh` and `/userdata/system/.ssh`. Do not assume one resolves
to the other.

On a measured Scarab 2026-05-11 RG40XX-H build, Dropbear read
`/root/.ssh/authorized_keys` from the volatile root overlay. A key under
`/userdata/system/.ssh` was not active after boot. That build needed a narrow
user service under `/userdata/system/services` to copy the persistent key into
the live root directory and apply `0700`/`0600` modes. Do not generalize that
workaround: first inspect the installed Dropbear process and filesystem layout.

Do not run `knulli-save-overlay` merely to retain a key. It persists unrelated
root changes as well. On builds where `/root/.ssh` resolves into `/userdata`,
install the key there directly. An exFAT userdata filesystem cannot preserve
Unix modes on the persistent source, so verify permissions on the live copy.
Test batch-mode login immediately and after reboot. A different SD card or
selected userdata device has separate SSH state.

## Controller environment

KNULLI's launcher can generate `SDL_GAMECONTROLLERCONFIG`. Preserve the final
value through PortMaster and inspect the application's process environment when
controller semantics matter. A mapping observed in an SSH shell is not proof
of what the application inherited.

Official references:

- [KNULLI SSH](https://knulli.org/configure/ssh/)
- [KNULLI networking and security](https://knulli.org/configure/networking/)
- [KNULLI patches and overlays](https://knulli.org/configure/patches-and-overlays/)
- [KNULLI storage partitioning](https://knulli.org/guides/partitioning/)
