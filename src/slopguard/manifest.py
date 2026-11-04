"""Read declared dependencies from requirements files and pyproject.toml."""

from __future__ import annotations

import configparser
import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

from slopguard.registry import normalize

_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def requirement_name(spec: str) -> str | None:
    match = _REQUIREMENT_NAME.match(spec)
    return normalize(match.group(1)) if match else None


def _from_requirements_file(path: Path) -> set[str]:
    names: set[str] = set()
    for raw in path.read_text(errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith(("-", "git+", "http://", "https://", ".")):
            continue
        name = requirement_name(line)
        if name:
            names.add(name)
    return names


def _from_pyproject(path: Path) -> set[str] | None:
    try:
        data = tomllib.loads(path.read_text(errors="replace"))
    except tomllib.TOMLDecodeError:
        return None
    tool = data.get("tool", {})
    declares = (
        "project" in data
        or "dependency-groups" in data
        or "poetry" in tool
        or "dev-dependencies" in tool.get("uv", {})
        or "dev-dependencies" in tool.get("pdm", {})
        or "envs" in tool.get("hatch", {})
    )
    if not declares:
        return None  # tool settings only, such as [tool.ruff]: not a dependency manifest
    specs: list[str] = []
    project = data.get("project", {})
    specs += [s for s in project.get("dependencies", []) if isinstance(s, str)]
    for group in project.get("optional-dependencies", {}).values():
        specs += [s for s in group if isinstance(s, str)]
    for group in data.get("dependency-groups", {}).values():
        specs += [s for s in group if isinstance(s, str)]
    specs += _strings(tool.get("uv", {}).get("dev-dependencies", []))           # uv (older layout)
    for group in tool.get("pdm", {}).get("dev-dependencies", {}).values():       # PDM
        specs += _strings(group)
    for env in tool.get("hatch", {}).get("envs", {}).values():                   # Hatch environments
        if isinstance(env, dict):
            specs += _strings(env.get("dependencies", [])) + _strings(env.get("extra-dependencies", []))
    names = {n for n in map(requirement_name, specs) if n}
    poetry = tool.get("poetry", {})
    tables = [poetry.get("dependencies", {}), poetry.get("dev-dependencies", {})]
    tables += [g.get("dependencies", {}) for g in poetry.get("group", {}).values()]
    for table in tables:
        names |= {normalize(k) for k in table if k.lower() != "python"}
    return names


def _strings(value: object) -> list[str]:
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _from_setup_cfg(path: Path) -> set[str] | None:
    parser = configparser.ConfigParser()
    try:
        parser.read(path, encoding="utf-8")
    except (configparser.Error, UnicodeDecodeError):
        return None
    blocks = []
    if parser.has_option("options", "install_requires"):
        blocks.append(parser.get("options", "install_requires"))
    if parser.has_section("options.extras_require"):
        blocks += [parser.get("options.extras_require", key) for key in parser.options("options.extras_require")]
    if not blocks:
        return None  # e.g. only flake8 or isort settings
    lines = [line.strip() for block in blocks for line in block.splitlines()]
    return {n for n in map(requirement_name, lines) if n}


def _from_pipfile(path: Path) -> set[str] | None:
    try:
        data = tomllib.loads(path.read_text(errors="replace"))
    except tomllib.TOMLDecodeError:
        return None
    tables = [data.get("packages", {}), data.get("dev-packages", {})]
    return {normalize(name) for table in tables if isinstance(table, dict) for name in table}


def declared_dependencies(root: Path) -> set[str] | None:
    """Return normalised declared dependency names, or None when no manifest exists."""
    found = False
    names: set[str] = set()
    for path in sorted(root.glob("requirements*.txt")) + sorted(root.glob("requirements/*.txt")):
        found = True
        names |= _from_requirements_file(path)
    readers = (("pyproject.toml", _from_pyproject), ("setup.cfg", _from_setup_cfg), ("Pipfile", _from_pipfile))
    for filename, reader in readers:
        path = root / filename
        declared = reader(path) if path.is_file() else None
        if declared is not None:
            found = True
            names |= declared
    return names if found else None
