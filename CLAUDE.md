# picstory — agent instructions (autonomous experiment)

## Start here, every session

1. Run `uv run python scripts/check_hard_stop.py`. If it fails or `HALT.md` exists: stop. Do nothing else.
2. Read `QUEUE.md`, `DECISIONS.md`, `REVIEW.md` (if present), and the most recent file in `logs/`.
3. Identify your role for this session. **One role per session. Never both.**

## Roles

### BUILDER
Works `QUEUE.md` top-down. Takes the top unblocked item, implements it, commits. Ends the session with a worklog to `logs/builder-NNN.md` (NNN = zero-padded sequence: builder-001.md, builder-002.md, …).

### CRITIC
Reads the diff since the last critic commit and writes `REVIEW.md`. **Never edits code.** Its instruction:

> Find every place the implementation does not match TAXONOMY.md. You are not reviewing code quality. You are checking whether this app encodes the specific failure modes in that file, or a generic version of them. For each taxonomy ID, state whether the detector implements the actual described failure or a plausible substitute.

CRITIC worklogs go to `logs/critic-NNN.md` and do not count toward the builder-session hard stop.

## Standing rules — both roles

- `TAXONOMY.md` is **frozen and read-only**. If an item is unimplementable, that is a `DECISIONS.md` entry — it is never quietly reworded.
- `PREDICTION.md` is read-only. Nothing edits it, ever.
- **Nothing answers its own decision.** BUILDER logs and skips. CRITIC may add D-items and may not close them. Only the human writes rulings.
- **When open decisions reach five**, both routines halt and write `HALT.md` with the list. That is the stall made loud.
- **Network:** calls to `api.anthropic.com` are allowed — the Anthropic API is the vision model for judgment-dependent detectors (owner amendment, 9 Aug 2026; see D-001). All other network beyond package installs is forbidden.
- **Spending:** bounded by the owner's spend cap set in the Anthropic console, not by the agent's judgment. Within the cap, API usage is a normal tool. If the cap is hit, API calls fail — treat that as a blocked item, log it, move on; never work around it.
- **API discipline:** a model-call detector must embed the taxonomy item's Detection text in its prompt and return structured output naming the ID. A generic "critique this photo" prompt is the substitute PREDICTION.md names, and the CRITIC is instructed to flag it. The test suite must run offline — record API responses as fixtures; tests never make live calls.
- No deletion of anything tracked.
- Every session ends with a worklog: date, what moved, what is open, test count.

## Output discipline

Every script writes its full output to `outputs/reports/` and prints **at most three lines** to stdout: a summary line, a path, and a pass/fail. Use `scripts/_report.py` for this, everywhere.

**If you are about to pipe or truncate command output, the script is wrong. Fix the script.**

## Hard stop

Enforced by `scripts/check_hard_stop.py`, run at the start of every session: if `logs/` holds 25 builder worklogs, or the date is past 29 August 2026, it writes `HALT.md` and exits nonzero. `HALT.md` present means stop, in every session, for every role. (Extended from 20 worklogs / 22 August by the owner, 15 Aug 2026, for phase 2 — real-photo hardening, QUEUE.md Stage 5.)

## The design constraint that governs everything

The taxonomy is the product's vocabulary. Every diagnosis, habit, share-list one-liner, and comparison verdict maps to a taxonomy ID or to `unclassified` (per TAXONOMY.md section U). Output that names findings outside this vocabulary is a bug, not creativity.
