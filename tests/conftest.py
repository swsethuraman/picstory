"""Session-wide backstop for CLAUDE.md's API-discipline rule: "the test suite
must run offline ... tests never make live calls."

Individual tests already inject fakes deliberately - a `VisionCaller` for
`_vision.judge`, a `detector_lookup` for the CLI dispatch loop, a `CmpCaller`
for `cmp.compare_group`. That covers every test that cares about a specific
detector's behavior. What it does not cover is the `main()` end-to-end smoke
tests (`test_cli_analyze.py`/`test_cli_analyze_batch.py`), which deliberately
exercise the *real*, unfaked registry to test production wiring - and
therefore inherit whatever `default_caller()` actually resolves to.

Discovered while wiring CMP (QUEUE.md item 11, builder-011): this session's
sandboxed environment has a genuinely working `PICSTORY_VISION_KEY` (unlike
the no-key sandbox D-006 originally diagnosed), so those `main()` tests were
silently making real, spend-cap-metered calls to api.anthropic.com on every
`uv run pytest` - one per judgment-dependent detector per frame, now one more
per near-duplicate group for CMP. Confirmed live and billable directly
(`anthropic.Anthropic(...).messages.create(...)` succeeded end-to-end from
this session's shell) before adding this fixture.

This autouse fixture patches `anthropic.Anthropic` itself to a client whose
`.messages.create` raises immediately, with no network I/O at all - not just
"no key", which would still attempt (and pay for the TLS handshake of) a
real, doomed-to-401 connection. `default_caller()`-based paths that hit this
get logged as an "error" DetectorRun/comparison the same way any other
blocked call already is (CLAUDE.md's spending rule: "if the cap is hit ...
treat that as a blocked item, log it, move on") - so the existing `main()`
smoke tests keep passing, just without ever touching the network.

Tests that need the *real* `default_caller()`/`cmp.default_caller()` code
path (only the D-006 key-resolution tests in test_vision_detectors.py, as of
this writing) re-patch `anthropic.Anthropic` themselves within the test body,
via the same `monkeypatch` fixture instance - that later, more specific
`setattr` simply overrides this one for the duration of that test, and
`monkeypatch` restores the true original `anthropic.Anthropic` afterward
either way.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_profile_store(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test gets its own `PICSTORY_PROFILE_PATH` (QUEUE.md item 12).

    `profile.default_profile_path()` falls back to `~/.picstory/profile.json`
    when the env var is unset - without this, `scripts/analyze_batch.py`'s
    `main()` smoke tests (which exercise the real profile load/record/save
    path, not an injected fake - same "test production wiring" reasoning as
    the live-call fixture above) would read and write whatever real profile
    file exists on the machine running the suite. Autouse + session-wide, the
    same backstop shape as `_block_live_anthropic_calls`, so no future test
    file has to remember to set this itself.
    """
    monkeypatch.setenv("PICSTORY_PROFILE_PATH", str(tmp_path / "profile.json"))


class _BlockedMessages:
    def create(self, *args, **kwargs):
        raise RuntimeError(
            "a test attempted a live Anthropic API call - CLAUDE.md requires the "
            "test suite to run offline. Inject a fake VisionCaller/CmpCaller/"
            "detector_lookup/cmp_compare instead of relying on default_caller()."
        )


class _NoLiveCallsAnthropic:
    def __init__(self, *args, **kwargs) -> None:
        self.messages = _BlockedMessages()


@pytest.fixture(autouse=True)
def _block_live_anthropic_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _NoLiveCallsAnthropic)
