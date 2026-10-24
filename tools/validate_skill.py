#!/usr/bin/env python3
"""Validate the packaged skill without contacting a device or external service."""
from pathlib import Path
import json
import re
from urllib.parse import unquote, urlsplit

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT


def validate():
    content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", content, re.DOTALL)
    if not match:
        raise ValueError("SKILL.md needs YAML frontmatter")
    metadata = yaml.safe_load(match[1])
    name = metadata.get("name", "")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
        raise ValueError("Invalid skill name")
    if name != "handheld-development":
        raise ValueError("Unexpected skill name")
    description = metadata.get("description", "")
    if not isinstance(description, str) or not 1 <= len(description) <= 1024:
        raise ValueError("Description must contain 1..1024 characters")
    if metadata.get("license") != "MIT" or not (SKILL / "LICENSE").is_file():
        raise ValueError("Packaged MIT license is missing")
    interface = yaml.safe_load((SKILL / "agents/openai.yaml").read_text())["interface"]
    if not 25 <= len(interface["short_description"]) <= 64:
        raise ValueError("UI description must contain 25..64 characters")
    if "$" + name not in interface["default_prompt"]:
        raise ValueError("Default prompt must reference the skill")
    links = 0
    for path in [SKILL / "README.md", SKILL / "SKILL.md", *(SKILL / "references").rglob("*.md")]:
        text = path.read_text(encoding="utf-8")
        for destination in re.findall(r"\[[^]\n]*\]\(([^)\s]+)\)", text):
            url = urlsplit(destination.strip("<>"))
            if url.scheme or not url.path:
                continue
            target = (path.parent / unquote(url.path)).resolve()
            if not target.is_relative_to(ROOT) or not target.exists():
                raise ValueError(f"Broken local link in {path.relative_to(ROOT)}: {destination}")
            links += 1
    json_files = [*(SKILL / "schemas").rglob("*.json"), *(SKILL / "examples").rglob("*.json")]
    for path in json_files:
        json.loads(path.read_text(encoding="utf-8"))
    print(f"Valid {name}: metadata, {links} local links and {len(json_files)} JSON files")


if __name__ == "__main__":
    validate()
