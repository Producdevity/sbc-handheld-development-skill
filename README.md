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

The command follows the [official installation reference](https://github.com/vercel-labs/skills/blob/main/docs/commands.md#skills-add).

The repository root is the skill directory: `SKILL.md`, references, helpers,
tests, examples, schemas and Codex UI metadata live alongside this README.

## Develop from a checkout

Keep one checkout in your agent's skills directory. Point optional workspace
shortcuts at that checkout so manual and agent edits change the same files.

If the skills directory belongs to a dotfiles repository, use a submodule from
that repository's root:

```sh
git submodule add -b master git@github.com:Producdevity/sbc-handheld-development-skill.git .agents/skills/handheld-development
```

Preserve an existing installation before converting it. Edit and commit skill
files inside the submodule; dotfiles tracks `.gitmodules` and the skill's commit
reference. Keep the installed directory real and `SKILL.md` a regular file
when required by the agent's sandbox.

## Requirements

Host helpers use Python 3.10+ (standard library only), POSIX shell and OpenSSH.
Native controller helpers need matching Linux/SDL2 development headers
and a suitable cross compiler. Handheld tools are discovered on the installed
firmware; this repository does not bundle binaries, drivers or game assets.

## Validate

From the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python tools/validate_skill.py
python -m unittest discover -s tests -v
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
