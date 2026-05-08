"""Author normalisation: PID-based merge + alias fallback."""

from __future__ import annotations

from scripts.normalize import build_canonical_names


def test_pid_merges_two_display_forms() -> None:
    raw = [
        {"authors": [{"pid": "p1", "name": "Smith Johnson"}]},
        {"authors": [{"pid": "p1", "name": "Smith Johnson"}]},
        {"authors": [{"pid": "p1", "name": "S. Johnson"}]},
    ]
    canonical = build_canonical_names(raw, aliases={})
    # Same PID -> single canonical, picking the most-frequent display form.
    assert canonical == {"p1": "Smith Johnson"}


def test_alias_overrides_majority_form() -> None:
    """Aliases get applied before voting, so we can stamp out unaccented straggler forms
    without a quorum of hits."""
    raw = [
        {"authors": [{"pid": "p1", "name": "Andres Fabrega"}]},
        {"authors": [{"pid": "p1", "name": "Andres Fabrega"}]},
        {"authors": [{"pid": "p1", "name": "Andrés Fábrega"}]},
    ]
    canonical = build_canonical_names(raw, aliases={"Andres Fabrega": "Andrés Fábrega"})
    assert canonical == {"p1": "Andrés Fábrega"}


def test_distinct_pids_stay_separate() -> None:
    raw = [
        {"authors": [{"pid": "237/5007", "name": "Zuchao Ma"}]},
        {"authors": [{"pid": "237/5007", "name": "Zuchao Ma"}]},
        {"authors": [{"pid": "999/0001", "name": "Zheyuan Ma"}]},
    ]
    canonical = build_canonical_names(raw, aliases={})
    assert canonical["237/5007"] == "Zuchao Ma"
    assert canonical["999/0001"] == "Zheyuan Ma"
