from pathlib import Path

from slopaudit.config import Config
from slopaudit.scaffold import (
    DRIFT_FILE_THRESHOLD,
    ProjectProfile,
    count_python_files,
    detect_project,
    manifest_name,
    render_starter_config,
)


def write_project(root: Path, *dependencies: str) -> None:
    quoted = ", ".join(f'"{dependency}"' for dependency in dependencies)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "demo"\nversion = "0"\ndependencies = [{quoted}]\n'
    )


def profile(python_files: int) -> ProjectProfile:
    return ProjectProfile(
        manifest="pyproject.toml",
        llm_sdks=("openai",),
        agent_frameworks=("langchain",),
        python_files=python_files,
    )


def test_detects_llm_sdks_and_agent_frameworks(tmp_path: Path) -> None:
    write_project(tmp_path, "OpenAI>=1", "anthropic", "langchain", "langgraph", "numpy")
    found = detect_project(tmp_path)
    assert found.manifest == "pyproject.toml"
    assert found.llm_sdks == ("anthropic", "openai")
    assert found.agent_frameworks == ("langchain", "langgraph")
    assert found.python_files == 0


def test_falls_back_to_requirements_txt(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("openai>=1\npython-dotenv\n")
    (tmp_path / "requirements-dev.txt").write_text("pytest\n")
    found = detect_project(tmp_path)
    assert found.manifest == "requirements.txt"
    assert found.llm_sdks == ("openai",)
    assert found.agent_frameworks == ()


def test_counts_project_files_but_skips_vendored_folders(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "b.py").write_text("")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "c.py").write_text("")
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "d.py").write_text("")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "e.py").write_text("")
    assert count_python_files(tmp_path) == 3


def test_prefers_pyproject_over_other_manifests(tmp_path: Path) -> None:
    write_project(tmp_path, "openai")
    (tmp_path / "requirements.txt").write_text("langchain\n")
    assert manifest_name(tmp_path) == "pyproject.toml"


def test_small_project_keeps_drift_off_and_config_loads(tmp_path: Path) -> None:
    text = render_starter_config(profile(12))
    assert "#   LLM SDKs: openai" in text
    assert "#   Agent frameworks: langchain" in text
    assert "drift rules stay off" in text
    assert "drf = false" in text
    (tmp_path / "slopaudit.toml").write_text(text)
    config = Config.load(tmp_path)
    assert config.modules["drf"] is False


def test_large_project_enables_drift_and_config_loads(tmp_path: Path) -> None:
    text = render_starter_config(profile(DRIFT_FILE_THRESHOLD))
    assert "so the drift rules are enabled" in text
    assert "drf = true" in text
    (tmp_path / "slopaudit.toml").write_text(text)
    config = Config.load(tmp_path)
    assert config.modules["drf"] is True


def test_missing_manifest_writes_the_default_starter(tmp_path: Path) -> None:
    found = detect_project(tmp_path)
    assert found.manifest is None
    text = render_starter_config(found)
    assert "# No dependency manifest found; this is the default starter." in text
    assert "drf = false" in text
    (tmp_path / "slopaudit.toml").write_text(text)
    Config.load(tmp_path)
