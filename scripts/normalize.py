"""Resolve author identities by DBLP PID and emit the final per-paper YAML.

A "canonical name" per PID is the most-frequently-seen display form across all included
papers (DBLP sometimes uses different transliterations on different papers). The optional
`config/author_aliases.yaml` covers the residual cases where DBLP failed to merge two PIDs.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from scripts.conferences import CONFERENCES

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR_TPL = REPO_ROOT / "data" / "{year}" / "raw"
CLASSIFIED_TPL = REPO_ROOT / "data" / "{year}" / "classified.yaml"
OUT_TPL = REPO_ROOT / "data" / "{year}" / "papers.yaml"
ALIASES_PATH = REPO_ROOT / "config" / "author_aliases.yaml"

DISPLAY_TO_CODE = {c.display: c.code for c in CONFERENCES}


def load_aliases(path: Path = ALIASES_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return dict(data.get("aliases") or {})


def _load_raw_index(year: int, raw_dir: Path | None = None) -> dict[str, dict]:
    raw_dir = raw_dir or Path(str(RAW_DIR_TPL).format(year=year))
    index: dict[str, dict] = {}
    for conf in CONFERENCES:
        path = raw_dir / f"{conf.code}.json"
        if not path.exists():
            continue
        for paper in json.loads(path.read_text(encoding="utf-8")):
            index[paper["dblp_key"]] = paper
    return index


def build_canonical_names(
    raw_papers: list[dict], aliases: dict[str, str]
) -> dict[str, str]:
    """For each PID, pick the display name that appears most often across the included papers.

    Aliases are applied per-occurrence before voting, so e.g. every "Andres Fabrega" sighting
    counts as "Andrés Fábrega" and outvotes any leftover unaccented appearance.
    """
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for p in raw_papers:
        for a in p["authors"]:
            display = aliases.get(a["name"], a["name"])
            counts[a["pid"]][display] += 1
    return {pid: ctr.most_common(1)[0][0] for pid, ctr in counts.items()}


def normalize_papers(
    year: int,
    classified_path: Path | None = None,
    raw_dir: Path | None = None,
    aliases: dict[str, str] | None = None,
) -> list[dict]:
    classified_path = classified_path or Path(str(CLASSIFIED_TPL).format(year=year))
    rows = yaml.safe_load(classified_path.read_text(encoding="utf-8")) or []
    aliases = aliases if aliases is not None else load_aliases()
    raw_index = _load_raw_index(year, raw_dir=raw_dir)

    included = [r for r in rows if r["status"] == "include"]
    raw_included = [raw_index[r["dblp_key"]] for r in included if r["dblp_key"] in raw_index]
    canonical = build_canonical_names(raw_included, aliases)

    out: list[dict] = []
    for r in included:
        raw = raw_index.get(r["dblp_key"])
        if not raw:
            print(f"[normalize] WARNING: {r['dblp_key']} not in raw data, skipping")
            continue
        authors = []
        for a in raw["authors"]:
            authors.append(
                {
                    "pid": a["pid"],
                    "name": canonical.get(a["pid"], aliases.get(a["name"], a["name"])),
                }
            )
        out.append(
            {
                "dblp_key": r["dblp_key"],
                "title": raw["title"],
                "conference": r["conference"],
                "conference_code": DISPLAY_TO_CODE[r["conference"]],
                "year": r["year"],
                "authors": authors,
                "ee": raw.get("ee"),
            }
        )
    return out


def write_papers(papers: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Sort papers by conference order then title for stable output.
    order = {c.display: i for i, c in enumerate(CONFERENCES)}
    sorted_papers = sorted(
        papers, key=lambda p: (order.get(p["conference"], 99), p["title"].lower())
    )
    out_path.write_text(
        yaml.safe_dump(sorted_papers, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the canonical papers.yaml from classified.yaml.")
    ap.add_argument("--year", type=int, required=True)
    args = ap.parse_args()

    papers = normalize_papers(args.year)
    out_path = Path(str(OUT_TPL).format(year=args.year))
    write_papers(papers, out_path)
    print(f"[normalize] {len(papers)} papers -> {out_path}")
    by_conf: dict[str, int] = {}
    for p in papers:
        by_conf[p["conference"]] = by_conf.get(p["conference"], 0) + 1
    for c in CONFERENCES:
        print(f"    {c.display}: {by_conf.get(c.display, 0)}")


if __name__ == "__main__":
    main()
