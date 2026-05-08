"""Classify DBLP raw entries into include / needs_review / exclude.

The classifier is intentionally simple: title-only keyword matching plus a YAML override file.
Edge cases ("Mysticeti", "AD-MPC", ...) get flagged as `needs_review` and are resolved by
hand in `config/manual_overrides.yaml`. The pipeline never tries to make the LLM the arbiter.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from scripts.conferences import CONFERENCES

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR_TPL = REPO_ROOT / "data" / "{year}" / "raw"
OUT_TPL = REPO_ROOT / "data" / "{year}" / "classified.yaml"
KEYWORDS_PATH = REPO_ROOT / "config" / "keywords.yaml"
OVERRIDES_PATH = REPO_ROOT / "config" / "manual_overrides.yaml"

VALID_STATUSES = {"include", "needs_review", "exclude"}


@dataclass(frozen=True)
class Keywords:
    strong: tuple[str, ...]
    in_context: tuple[str, ...]
    negative: tuple[str, ...]


def load_keywords(path: Path = KEYWORDS_PATH) -> Keywords:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Keywords(
        strong=tuple(data.get("positive_strong") or ()),
        in_context=tuple(data.get("positive_in_context") or ()),
        negative=tuple(data.get("negative_overrides") or ()),
    )


def load_overrides(path: Path = OVERRIDES_PATH) -> dict[str, dict]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    overrides: dict[str, dict] = {}
    for entry in data.get("overrides") or []:
        key = entry["dblp_key"]
        if entry["status"] not in VALID_STATUSES:
            raise ValueError(f"override for {key}: bad status {entry['status']!r}")
        overrides[key] = entry
    return overrides


def _normalize(text: str) -> str:
    """Lowercase + collapse hyphens/underscores so 'smart-contract' and 'smart contract' equate."""
    text = text.lower().replace("-", " ").replace("_", " ")
    return re.sub(r"\s+", " ", text).strip()


def keyword_matches(keyword: str, title: str) -> bool:
    """Word-boundary, case-insensitive, allow trailing 's' for plurals.

    Keyword and title are both normalised so '-'/space variants collapse together. The
    optional 's' lets 'dag' match 'DAGs' and 'blockchain' match 'Blockchains' without
    blowing up false positives ('dagger' still won't match 'dag').
    """
    nk = _normalize(keyword)
    nt = _normalize(title)
    if not nk:
        return False
    return re.search(rf"\b{re.escape(nk)}s?\b", nt) is not None


def find_matches(keywords: list[str] | tuple[str, ...], title: str) -> list[str]:
    return [kw for kw in keywords if keyword_matches(kw, title)]


def classify_title(title: str, kw: Keywords) -> tuple[str, list[str], str | None]:
    """Return (status, matched_keywords, reason)."""
    strong = find_matches(kw.strong, title)
    context = find_matches(kw.in_context, title)
    negative = find_matches(kw.negative, title)

    if negative and (strong or context):
        return (
            "needs_review",
            sorted(set(strong + context + negative)),
            f"negative override hit: {', '.join(negative)}",
        )
    if strong:
        return "include", sorted(set(strong)), None
    if context:
        return (
            "needs_review",
            sorted(set(context)),
            "only in-context keyword(s) matched; abstract check or manual review required",
        )
    return "exclude", [], None


def classify_papers(year: int, raw_dir: Path | None = None) -> list[dict]:
    raw_dir = raw_dir or Path(str(RAW_DIR_TPL).format(year=year))
    kw = load_keywords()
    overrides = load_overrides()
    rows: list[dict] = []
    for conf in CONFERENCES:
        path = raw_dir / f"{conf.code}.json"
        if not path.exists():
            print(f"[classify] skipping {conf.code}: {path} not found")
            continue
        for paper in json.loads(path.read_text(encoding="utf-8")):
            status, matched, reason = classify_title(paper["title"], kw)
            override = overrides.get(paper["dblp_key"])
            row: dict = {
                "dblp_key": paper["dblp_key"],
                "title": paper["title"],
                "conference": conf.display,
                "year": paper["year"],
                "auto_status": status,
                "matched_keywords": matched,
                "status": override["status"] if override else status,
            }
            if reason:
                row["reason"] = reason
            if override:
                row["override_reason"] = override.get("reason", "manual override")
            rows.append(row)
    return rows


def write_classified(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Group by conference for readability and sort by title within each.
    rows_sorted = sorted(rows, key=lambda r: (r["conference"], r["title"].lower()))
    out_path.write_text(
        yaml.safe_dump(rows_sorted, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Classify raw DBLP papers as include/needs_review/exclude.")
    ap.add_argument("--year", type=int, required=True)
    args = ap.parse_args()

    rows = classify_papers(args.year)
    out_path = Path(str(OUT_TPL).format(year=args.year))
    write_classified(rows, out_path)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"[classify] {sum(counts.values())} papers -> {out_path}")
    for s, n in sorted(counts.items()):
        print(f"    {s}: {n}")


if __name__ == "__main__":
    main()
