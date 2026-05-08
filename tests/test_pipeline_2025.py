"""Regression tests against the curated 2025 list.

These rely on data/2025/papers.yaml being present (run `make 2025` first). They lock in
the contracts the user called out: author counts for Sisi Duan / Aniket Kate / Xiapu Luo,
the AD-MPC needs_review path, and the Muhui Jiang-vs-Mengmeng-Jiang title parse.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
import yaml

from scripts.classify import classify_papers, load_keywords

REPO_ROOT = Path(__file__).resolve().parent.parent
PAPERS_2025 = REPO_ROOT / "data" / "2025" / "papers.yaml"
RAW_2025 = REPO_ROOT / "data" / "2025" / "raw"


pytestmark = pytest.mark.skipif(
    not PAPERS_2025.exists(),
    reason="run `make 2025` (or scripts/fetch.py + classify + normalize) before running these tests",
)


@pytest.fixture(scope="module")
def papers() -> list[dict]:
    return yaml.safe_load(PAPERS_2025.read_text(encoding="utf-8")) or []


@pytest.fixture(scope="module")
def author_counts(papers: list[dict]) -> Counter[str]:
    c: Counter[str] = Counter()
    for p in papers:
        for a in p["authors"]:
            c[a["pid"]] += 1
    return c


@pytest.fixture(scope="module")
def pid_for_name(papers: list[dict]) -> dict[str, str]:
    """Map canonical name -> first PID seen. Convenient for asserting on author identity."""
    out: dict[str, str] = {}
    for p in papers:
        for a in p["authors"]:
            out.setdefault(a["name"], a["pid"])
    return out


def test_total_papers(papers: list[dict]) -> None:
    # Curated count from blockchain_papers_2025.md.
    assert len(papers) == 57


def test_per_conference_counts(papers: list[dict]) -> None:
    by_conf: Counter[str] = Counter(p["conference"] for p in papers)
    assert by_conf["NDSS"] == 13
    assert by_conf["USENIX Security"] == 18
    assert by_conf["ACM CCS"] == 12
    assert by_conf["IEEE S&P"] == 14


def test_sisi_duan_has_five_papers(author_counts: Counter[str], pid_for_name: dict[str, str]) -> None:
    pid = pid_for_name["Sisi Duan"]
    assert author_counts[pid] == 5, f"expected Sisi Duan = 5 papers, got {author_counts[pid]}"


def test_aniket_kate_has_four_papers(author_counts: Counter[str], pid_for_name: dict[str, str]) -> None:
    pid = pid_for_name["Aniket Kate"]
    assert author_counts[pid] == 4


def test_xiapu_luo_has_four_papers(author_counts: Counter[str], pid_for_name: dict[str, str]) -> None:
    pid = pid_for_name["Xiapu Luo"]
    assert author_counts[pid] == 4


def test_dark_forest_second_author_is_muhui_jiang(papers: list[dict]) -> None:
    """DBLP gets this right; this test guards against an accidental author-list shuffle."""
    paper = next(p for p in papers if p["title"].startswith("Surviving in Dark Forest"))
    assert paper["authors"][1]["name"] == "Muhui Jiang"


def test_ad_mpc_is_auto_needs_review() -> None:
    """Without manual_overrides applied, AD-MPC must classify as needs_review on the title alone."""
    kw = load_keywords()
    title = "AD-MPC: Asynchronous Dynamic MPC with Guaranteed Output Delivery"
    from scripts.classify import classify_title

    status, matched, _ = classify_title(title, kw)
    assert status == "needs_review"
    assert "mpc" in matched


def test_ad_mpc_present_after_overrides() -> None:
    """With manual_overrides.yaml shipped, AD-MPC ends up included in the final list."""
    if not (RAW_2025 / "ccs.json").exists():
        pytest.skip("raw data not present")
    rows = classify_papers(2025)
    ad_mpc = next(r for r in rows if "AD-MPC" in r["title"])
    assert ad_mpc["status"] == "include"
    assert ad_mpc["auto_status"] == "needs_review"
