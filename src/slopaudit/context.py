"""Per-project and per-file context handed to rules."""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Any

from slopaudit.config import DEFAULT_EXCLUDE_DIRS, Config
from slopaudit.manifest import declared_dependencies
from slopaudit.models import Finding, RuleMeta, Severity
from slopaudit.registry import RegistryClient


@dataclass
class ProjectContext:
    root: Path
    config: Config
    registry: RegistryClient | None
    declared: set[str] | None
    local_modules: set[str]
    installed: dict[str, list[str]]
    changed: set[Path] | None = None
    _conventions: Any = None
    _manifests: dict[Path, set[str] | None] = field(default_factory=dict)

    def conventions(self) -> Any:
        """Style conventions mined from files outside the change (computed once)."""
        if self._conventions is None:
            from slopaudit.drift import mine_conventions

            self._conventions = mine_conventions(self.root, self.config, self.changed or set())
        return self._conventions

    def declared_for(self, file_path: Path) -> set[str] | None:
        """Dependencies declared by the manifests from the file's folder up to the project root.

        A monorepo or a ``fixtures/`` folder can carry its own ``pyproject.toml`` or requirements
        file, so the root manifest alone is not the whole truth. Returns None when no manifest exists
        anywhere on the way, in which case there is nothing to compare against.
        """
        root = self.root.resolve()
        folder = file_path.resolve().parent
        chain = [folder]
        if folder != root and root in folder.parents:
            chain = [folder, *[p for p in folder.parents if p == root or root in p.parents]]
        found: set[str] | None = None
        for directory in chain:
            if directory not in self._manifests:
                self._manifests[directory] = declared_dependencies(directory)
            names = self._manifests[directory]
            if names is not None:
                found = (found or set()) | names
        return found

    def is_local(self, name: str, file_path: Path) -> bool:
        if name in self.local_modules:
            return True
        folder = file_path.parent
        in_own_package = name in {folder.name, *(p.name for p in folder.parents)}
        return in_own_package or (folder / f"{name}.py").exists() or (folder / name).is_dir()


@dataclass
class FileContext:
    path: Path
    rel: str
    source: str
    project: ProjectContext
    tree: ast.Module | None = None
    syntax_error: SyntaxError | None = None
    cache: dict[str, Any] = field(default_factory=dict)
    lines: list[str] = field(init=False)

    def __post_init__(self) -> None:
        self.lines = self.source.splitlines()

    @property
    def config(self) -> Config:
        return self.project.config

    def options(self, rule_id: str) -> dict[str, Any]:
        return self.config.rule_options(rule_id)

    def line_text(self, line: int) -> str:
        return self.lines[line - 1] if 1 <= line <= len(self.lines) else ""

    def make_finding(
        self,
        meta: RuleMeta,
        line: int,
        message: str,
        *,
        end_line: int | None = None,
        confidence: float = 0.9,
        excerpt: str | None = None,
        trace: tuple[str, ...] = (),
        severity: Severity | None = None,
    ) -> Finding:
        return Finding(
            rule_id=meta.id,
            severity=meta.severity if severity is None else severity,
            message=message,
            path=self.rel,
            line=line,
            end_line=end_line or line,
            confidence=confidence,
            explanation=meta.explanation,
            fix=meta.fix,
            cwe=meta.cwe,
            owasp=meta.owasp,
            excerpt=self.line_text(line).strip() if excerpt is None else excerpt,
            trace=trace,
        )


def _local_module_names(root: Path) -> set[str]:
    """Names that are importable from inside the project: every folder that holds Python code
    (and the folders above it) and every module, wherever it sits. Test and fixture folders put
    their own packages on the path, so matching only the top level reports them as unknown."""
    names: set[str] = set()
    for base in (root, root / "src"):
        if not base.is_dir():
            continue
        for entry in base.iterdir():
            if entry.name.startswith((".", "_")) and entry.name != "__init__.py":
                continue
            if entry.is_dir():
                names.add(entry.name)
            elif entry.suffix == ".py":
                names.add(entry.stem)
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDE_DIRS and not d.startswith(".")]
        modules = [f[:-3] for f in files if f.endswith(".py") and not f.startswith("_")]
        names.update(m for m in modules if m.isidentifier())
        if any(f.endswith(".py") for f in files):
            folder = Path(current)
            while folder != root and root in folder.parents:
                if folder.name.isidentifier():
                    names.add(folder.name)
                folder = folder.parent
    return names


def build_project(
    root: Path,
    config: Config,
    *,
    network: bool = True,
    registry: RegistryClient | None = None,
    changed: set[Path] | None = None,
) -> ProjectContext:
    if registry is None and network and config.registry_lookups:
        registry = RegistryClient(ttl_hours=config.cache_ttl_hours)
    try:
        installed = {k: list(v) for k, v in metadata.packages_distributions().items()}
    except Exception:  # noqa: BLE001  # pragma: no cover - broken metadata must not stop a scan
        installed = {}
    return ProjectContext(
        root=root,
        config=config,
        registry=registry,
        declared=declared_dependencies(root),
        local_modules=_local_module_names(root),
        installed=installed,
        changed=changed,
    )
