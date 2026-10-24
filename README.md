# SBC Handheld Development Skill

An [Agent Skill](https://agentskills.io/specification) for developing, packaging,
debugging and testing native Linux ARM handheld apps and PortMaster ports.
It includes guidance for muOS, KNULLI, ROCKNIX, SpruceOS, dArkOS and AmberELEC,
plus bounded input automation, screen capture, controller probes and validation
helpers. Support and test coverage depend on the actual device and firmware.

## Install

With the [skills CLI](https://github.com/vercel-labs/skills):

```sh
npx skills add Producdevity/sbc-handheld-development-skill --skill handheld-development
```

Use `--global` for a user-wide installation and `--agent codex` (or another
supported agent) to choose the destination. Omit those options for interactive
project installation. The installed skill stays named `handheld-development`.
Invoke it with `$handheld-development` or ask for Linux handheld port work.

Install directly from a local checkout:

```sh
npx skills add . --skill handheld-development
```

These commands follow the [official installation reference](https://github.com/vercel-labs/skills/blob/main/docs/commands.md#skills-add).

The repository uses the standard `skills/handheld-development/` layout. The
skill folder contains its instructions, references, helpers, tests, examples,
schemas and Codex UI metadata; repository documentation stays outside it.

## Develop from a checkout

Keep one canonical checkout and symlink its entire skill directory into your
agent's skills directory. For the shared user skills location, starting in
this repository:

```sh
mkdir -p "$HOME/.agents/skills"
ln -s "$PWD/skills/handheld-development" "$HOME/.agents/skills/handheld-development"
```

If that destination already exists, preserve it before replacing it. A single
directory symlink keeps relative references and new helper files working;
individual file symlinks are unnecessary. If your skills directory is managed
by dotfiles, place the link in the underlying dotfiles directory instead.

Some agent sandboxes require an installed skills directory to remain a real
directory. For those environments, keep a real `handheld-development/` directory
with a regular copy of `SKILL.md`; Codex skips symlinked manifests in this layout.
Link `LICENSE` and the resource directories to the checkout. Edits and new files
inside linked directories update immediately. After editing the canonical
manifest, refresh its installed copy from the repository root:

```sh
cp skills/handheld-development/SKILL.md "$HOME/.agents/skills/handheld-development/SKILL.md"
```

Add a link if the skill gains a new top-level resource. Repository-only files
remain outside the installed skill.

## Requirements

Host helpers use Python 3.10+, POSIX shell and OpenSSH. PNG normalization needs
Pillow. Native controller helpers need matching Linux/SDL2 development headers
and a suitable cross compiler. Handheld tools are discovered on the installed
firmware; this repository does not bundle binaries, drivers or game assets.

## Validate

From the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python tools/validate_skill.py
python -m unittest discover -s skills/handheld-development/tests -v
```

The checks cover metadata, local links, JSON syntax and host helper behavior.
CI also checks shell and Linux C syntax; hardware compatibility requires
project-specific device tests. Keep shared resources portable and retain
project-specific probes, paths and evidence in that project's ignored files.

## License

[MIT](LICENSE), preserving the license from the original
[Producdevity/dotfiles](https://github.com/Producdevity/dotfiles) source.
Third-party firmware, tools and documentation linked by the skill retain
their own licenses.
