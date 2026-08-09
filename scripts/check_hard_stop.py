"""Hard-stop enforcement. Run at the start of every session, both roles.

Writes HALT.md and exits nonzero if:
  - HALT.md already exists, or
  - logs/ holds >= 20 builder worklogs (builder-*.md), or
  - today's date is past 2026-08-22.

Per PREDICTION.md: do not rescue a stall. The stall is the finding.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HALT = ROOT / "HALT.md"
LOGS = ROOT / "logs"
HARD_DATE = date(2026, 8, 22)
MAX_BUILDER_SESSIONS = 20


def main() -> int:
    if HALT.exists():
        print("HALT.md present - stopped. Do nothing else this session.")
        return 1

    n = len(list(LOGS.glob("builder-*.md"))) if LOGS.exists() else 0
    today = date.today()

    reason = None
    if n >= MAX_BUILDER_SESSIONS:
        reason = f"hard stop: {n} builder worklogs (limit {MAX_BUILDER_SESSIONS})"
    elif today > HARD_DATE:
        reason = f"hard stop: date {today} is past {HARD_DATE}"

    if reason:
        HALT.write_text(
            f"# HALT\n\n{reason}. Written automatically on {today}.\n\n"
            "Per PREDICTION.md: read and score now. Do not rescue.\n",
            encoding="utf-8",
        )
        print(reason)
        print(HALT)
        return 1

    print(f"OK - {n}/{MAX_BUILDER_SESSIONS} builder sessions used, hard date {HARD_DATE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
