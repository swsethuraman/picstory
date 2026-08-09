"""Output discipline helper. Every script routes its full output through here.

Full body -> outputs/reports/<timestamp>_<name>.md
Stdout    -> at most three lines: summary, path, PASS/FAIL.

If you are about to pipe or truncate command output, the script is wrong.
Fix the script (usually: make it call report()).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

REPORTS = Path(__file__).resolve().parents[1] / "outputs" / "reports"


def report(name: str, body: str, summary: str, passed: bool | None = None) -> Path:
    """Write the full body to a report file; print <=3 lines to stdout.

    name    -- short slug for the report filename (no spaces)
    body    -- the complete output, however long
    summary -- one line, what happened
    passed  -- optional pass/fail; prints a third line when given
    """
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / f"{datetime.now():%Y%m%d-%H%M%S}_{name}.md"
    path.write_text(body, encoding="utf-8")
    print(summary.splitlines()[0][:160])
    print(path)
    if passed is not None:
        print("PASS" if passed else "FAIL")
    return path
