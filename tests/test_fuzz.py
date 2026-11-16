"""Fuzz the scanner with generated, syntactically valid Python.

The default suite skips these (``addopts = -m 'not fuzz'``); run them with
``pytest -m fuzz`` after installing the optional extra:
``pip install -e ".[dev,fuzz]"``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

try:
    from hypothesis import HealthCheck, given, settings
    from hypothesmith import from_grammar
except ImportError:  # pragma: no cover - only when the fuzz extra is absent
    pytest.skip("install the fuzz extra: pip install -e '.[dev,fuzz]'", allow_module_level=True)

from slopaudit.api import Config, scan_source, select_rules
from slopaudit.context import FileContext, build_project
from slopaudit.engine import _check_file

pytestmark = pytest.mark.fuzz


def rule_errors(source: str) -> list[str]:
    """Run every rule the way scan_source does, but keep the errors it discards."""
    config = Config()
    project = build_project(Path.cwd(), config, network=False)
    ctx = FileContext(
        project.root / "fuzz.py", "fuzz.py", source, project, ast.parse(source), None
    )
    errors: list[str] = []
    _check_file(ctx, select_rules(config), errors)
    return errors


@given(from_grammar())
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
    report_multiple_bugs=False,
)
def test_scan_source_never_crashes_or_reports_rule_errors(source: str) -> None:
    findings = scan_source(source)
    assert isinstance(findings, list)
    assert rule_errors(source) == []
