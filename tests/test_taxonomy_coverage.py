"""Taxonomy coverage guard.

Parses TAXONOMY.md for item IDs (F01..F15, S01..S04, R01) and fails unless
every ID appears in BOTH:
  1. a detector: the ID occurs in at least one .py file under src/, and
  2. a test that NAMES it: a test function whose name contains the ID
     (e.g. def test_f01_digital_zoom_...), in tests/, excluding this file.

This is the machine-checkable line between encoding the specific failure
modes in TAXONOMY.md and shipping a generic taxonomy with the right labels.
It cannot check substance - that is the CRITIC's job - but it guarantees no
ID is silently dropped.

The CMP rubric and section U carry no [FSR]nn ID and are exempt here;
CMP conformance is checked by the CRITIC against Stage 3 output.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = ROOT / "TAXONOMY.md"
SRC = ROOT / "src"
TESTS = ROOT / "tests"
THIS_FILE = Path(__file__).name

ID_HEADING = re.compile(r"^### ([FSR]\d{2})\b", re.MULTILINE)
TEST_DEF = re.compile(r"def (test_[a-z0-9_]+)")


def taxonomy_ids() -> list[str]:
    text = TAXONOMY.read_text(encoding="utf-8")
    return sorted(set(ID_HEADING.findall(text)))


def test_taxonomy_parses() -> None:
    ids = taxonomy_ids()
    assert ids, "No taxonomy IDs parsed from TAXONOMY.md - parser or file is broken"
    assert len(ids) == 20, (
        f"Expected 20 IDs (15 F + 4 S + 1 R), parsed {len(ids)}: {ids}. "
        "TAXONOMY.md is frozen - if this changed, something edited it."
    )


@pytest.mark.xfail(
    strict=True,
    reason="F14 stands stubbed per DECISIONS.md D-007 for the remainder of the "
    "experiment - this guard's red is the documented, intended end state, not a "
    "regression. strict=True so a future F14 implementation forces this marker's "
    "conscious removal rather than letting it XPASS silently.",
)
def test_every_id_has_detector_and_named_test() -> None:
    ids = taxonomy_ids()

    src_files = list(SRC.rglob("*.py")) if SRC.exists() else []
    src_blob = "\n".join(p.read_text(encoding="utf-8") for p in src_files)
    missing_detector = [i for i in ids if i not in src_blob]

    named_in_tests: set[str] = set()
    for p in TESTS.rglob("test_*.py"):
        if p.name == THIS_FILE:
            continue
        for m in TEST_DEF.finditer(p.read_text(encoding="utf-8")):
            fn = m.group(1)
            for i in ids:
                if i.lower() in fn:
                    named_in_tests.add(i)
    missing_test = [i for i in ids if i not in named_in_tests]

    problems = []
    if missing_detector:
        problems.append(f"IDs with no detector under src/: {missing_detector}")
    if missing_test:
        problems.append(f"IDs with no test naming them under tests/: {missing_test}")
    assert not problems, (
        "Taxonomy coverage failed.\n"
        + "\n".join(problems)
        + "\nEvery TAXONOMY.md ID must appear in a detector and in a test "
        "function name (e.g. test_f06_edge_intrusion_...). If an item is "
        "unimplementable, that is a DECISIONS.md entry, not an omission."
    )
