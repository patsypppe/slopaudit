"""Inspect a project and tailor the `slopaudit init` starter config."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from slopaudit.config import STARTER_CONFIG
from slopaudit.manifest import declared_dependencies

# Projects at or above this size tend to have their own conventions, which is
# what the drift rules compare against. Below it, the rules mostly report noise.
DRIFT_FILE_THRESHOLD = 200

LLM_SDKS = frozenset(
    {
        "anthropic",
        "azure-ai-inference",
        "cohere",
        "dashscope",
        "google-genai",
        "google-generativeai",
        "groq",
        "huggingface-hub",
        "litellm",
        "mistralai",
        "ollama",
        "openai",
        "replicate",
        "sentence-transformers",
        "together",
        "transformers",
        "vertexai",
    }
)

AGENT_FRAMEWORKS = frozenset(
    {
        "ag2",
        "agno",
        "atomic-agents",
        "autogen",
        "crewai",
        "dspy",
        "dspy-ai",
        "google-adk",
        "guidance",
        "haystack-ai",
        "instructor",
        "langchain",
        "langchain-anthropic",
        "langchain-community",
        "langchain-core",
        "langchain-openai",
        "langgraph",
        "llama-index",
        "llama-index-core",
        "openai-agents",
        "pydantic-ai",
        "pydantic-ai-slim",
        "pyautogen",
        "semantic-kernel",
        "smolagents",
    }
)

MANIFESTS = ("pyproject.toml", "setup.cfg", "Pipfile", "requirements.txt")
SKIP_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".svn",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "env",
        "node_modules",
        "site-packages",
        "venv",
    }
)


@dataclass(frozen=True)
class ProjectProfile:
    """What `slopaudit init` found in the project root."""

    manifest: str | None
    llm_sdks: tuple[str, ...]
    agent_frameworks: tuple[str, ...]
    python_files: int

    @property
    def suggests_drift(self) -> bool:
        return self.python_files >= DRIFT_FILE_THRESHOLD


def manifest_name(root: Path) -> str | None:
    """The manifest the dependencies came from, relative to the project root."""
    for name in MANIFESTS:
        if (root / name).is_file():
            return name
    nested = sorted(root.glob("requirements/*.txt"))
    if nested:
        return nested[0].relative_to(root).as_posix()
    return None


def count_python_files(root: Path) -> int:
    """Count project Python files, skipping hidden and vendored folders."""
    count = 0
    for path in root.rglob("*.py"):
        relative = path.relative_to(root)
        if any(part.startswith(".") or part in SKIP_DIRECTORIES for part in relative.parts[:-1]):
            continue
        count += 1
    return count


def detect_project(root: Path) -> ProjectProfile:
    """Read the manifest and the file tree, without importing or running anything."""
    declared = declared_dependencies(root) or set()
    return ProjectProfile(
        manifest=manifest_name(root),
        llm_sdks=tuple(sorted(declared & LLM_SDKS)),
        agent_frameworks=tuple(sorted(declared & AGENT_FRAMEWORKS)),
        python_files=count_python_files(root),
    )


def render_starter_config(profile: ProjectProfile) -> str:
    """The starter config with a short, commented profile of the project."""
    lines = STARTER_CONFIG.splitlines()
    header = [lines[0], "#"]
    if profile.manifest is None:
        header.append("# No dependency manifest found; this is the default starter.")
    else:
        header.append(f"# Profile from {profile.manifest}:")
        header.append(f"#   LLM SDKs: {', '.join(profile.llm_sdks) or 'none'}")
        header.append(f"#   Agent frameworks: {', '.join(profile.agent_frameworks) or 'none'}")
        if profile.suggests_drift:
            header.append(
                f"#   {profile.python_files} Python files, so the drift rules are enabled;"
            )
            header.append("#   set drf = false if they are too noisy.")
        else:
            header.append(f"#   {profile.python_files} Python files; drift rules stay off.")
    body = header + lines[1:]
    if profile.suggests_drift:
        body = [
            "drf = true                  # style drift against the rest of the repo (opt-in)"
            if line.startswith("drf = false")
            else line
            for line in body
        ]
    return "\n".join(body) + "\n"
