# Real-world check: mature packages as a false-positive control

Generated 2026-11-04 by `benchmarks/realworld.py` with slopguard 1.0.0rc1 (with PyPI lookups). Do not edit by hand.

These are well-reviewed, human-written packages, so a serious finding here is almost certainly a false positive. The code was parsed, never imported or run. They are not AI-generated, so this measures noise, not detection.

| Package (wheel) | Scanned | Lines | Critical | High | Medium | Low |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| requests-2.34.2-py3-none-any | 19 files | 6,385 | 0 | 0 | 0 | 4 |
| flask-3.1.3-py3-none-any | 24 files | 9,199 | 0 | 0 | 0 | 9 |
| click-8.5.0-py3-none-any | 17 files | 12,674 | 0 | 0 | 0 | 8 |
| jinja2-3.1.6-py3-none-any | 25 files | 14,425 | 0 | 0 | 1 | 13 |
| httpx-0.28.1-py3-none-any | 23 files | 8,828 | 0 | 0 | 0 | 7 |
| rich-15.0.0-py3-none-any | 100 files | 38,515 | 0 | 0 | 0 | 8 |
| werkzeug-3.1.9-py3-none-any | 52 files | 21,687 | 0 | 0 | 0 | 12 |
| typer-0.27.3-py3-none-any | 32 files | 13,911 | 0 | 0 | 2 | 9 |
| openai-3.45.0-py3-none-any | 2075 files | 243,304 | 0 | 0 | 0 | 60 |
| anthropic-2.4.0-py3-none-any | 2641 files | 187,633 | 0 | 0 | 0 | 21 |
| langchain_core-1.7.5-py3-none-any | 184 files | 70,889 | 0 | 0 | 1 | 65 |
| litellm-1.108.0-cp310-abi3-manylinux_2_28_x86_64 | 2989 files | 965,431 | 0 | 0 | 24 | 338 |

**1,592,881 lines scanned in 169s (includes downloads). Critical + high findings: 0** (0.000 per 1,000 lines; the project target is below 1).

## Findings by rule

| Rule | Severity | Count |
| --- | --- | ---: |
| HAL-01 | medium | 1 |
| INC-01 | medium | 2 |
| INC-02 | low | 372 |
| INC-02 | medium | 25 |
| INC-04 | low | 172 |
| INC-06 | low | 8 |
| LLM-12 | low | 2 |

Medium findings are hollow module-level functions and the occasional placeholder comment, which a person should judge. Low findings are hook methods with empty bodies, silent `except Exception: pass` blocks with no comment, and files with many TODOs.
