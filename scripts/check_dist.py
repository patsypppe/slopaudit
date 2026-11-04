#!/usr/bin/env python3
"""Sanity-check the built distribution before it is published.

    python scripts/check_dist.py dist/

Catches the mistakes that only show up on the PyPI page after upload: relative links in the
description (PyPI has no repository to resolve them against), a wrong content type, a missing
typing marker, or a wheel and source archive that disagree.
"""

from __future__ import annotations

import re
import sys
import tarfile
import zipfile
from pathlib import Path

RELATIVE_LINK = re.compile(r"\]\((?!https?://|#|mailto:)([^)\s]+)\)")


def main(folder: str) -> int:
    dist = Path(folder)
    wheels, sdists = sorted(dist.glob("*.whl")), sorted(dist.glob("*.tar.gz"))
    problems: list[str] = []
    if len(wheels) != 1 or len(sdists) != 1:
        problems.append(f"expected one wheel and one sdist in {dist}, found {len(wheels)} and {len(sdists)}")
    else:
        with zipfile.ZipFile(wheels[0]) as wheel:
            names = wheel.namelist()
            metadata = wheel.read(next(n for n in names if n.endswith(".dist-info/METADATA"))).decode()
        headers, _, description = metadata.partition("\n\n")
        version = re.search(r"^Version: (.+)$", headers, re.MULTILINE)
        if "Description-Content-Type: text/markdown" not in headers:
            problems.append("description content type is not text/markdown")
        broken = RELATIVE_LINK.findall(description)
        if broken:
            problems.append(f"{len(broken)} relative link(s) in the PyPI description, e.g. {broken[0]}")
        for required in ("slopaudit/py.typed", "slopaudit/cli.py", "slopaudit/rules/llm_flow.py"):
            if required not in names:
                problems.append(f"wheel is missing {required}")
        with tarfile.open(sdists[0]) as sdist:
            if not any(n.endswith("/LICENSE") for n in sdist.getnames()):
                problems.append("sdist has no LICENSE")
        if version and version.group(1) not in wheels[0].name:
            problems.append("wheel file name and metadata version disagree")
    for problem in problems:
        print(f"error: {problem}", file=sys.stderr)
    if not problems:
        print(f"{wheels[0].name}: ok ({len(names)} files, description links absolute)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "dist"))
