"""Aggregate author counts from papers.yaml and emit output/<year>/authors.md."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import yaml

from scripts.conferences import CONFERENCES

REPO_ROOT = Path(__file__).resolve().parent.parent
PAPERS_TPL = REPO_ROOT / "data" / "{year}" / "papers.yaml"
OUT_TPL = REPO_ROOT / "output" / "{year}" / "authors.md"


@dataclass
class AuthorRow:
    pid: str
    name: str
    papers: list[tuple[str, int, str]]  # (conf_display, idx_in_conf, short_title)

    @property
    def count(self) -> int:
        return len(self.papers)


def _conference_index(papers: list[dict]) -> dict[str, dict[str, int]]:
    """Index each paper by (conference_display, dblp_key) -> 1-based idx within that conf.

    Within a conference, papers are ordered alphabetically by title; the index here matches
    the rendered Markdown so users can cite e.g. `USENIX #3` and find it in papers.md.
    """
    by_conf: dict[str, list[dict]] = defaultdict(list)
    for p in papers:
        by_conf[p["conference"]].append(p)
    out: dict[str, dict[str, int]] = {}
    for conf, lst in by_conf.items():
        lst.sort(key=lambda p: p["title"].lower())
        out[conf] = {p["dblp_key"]: i + 1 for i, p in enumerate(lst)}
    return out


def _short_title(title: str) -> str:
    """Take the part before the first colon, trimmed; fall back to the first 5 words."""
    head = title.split(":", 1)[0].strip()
    if head and len(head.split()) <= 8:
        return head
    return " ".join(title.split()[:5])


def aggregate(papers: list[dict]) -> list[AuthorRow]:
    idx = _conference_index(papers)
    rows: dict[str, AuthorRow] = {}
    for p in papers:
        i = idx[p["conference"]][p["dblp_key"]]
        for a in p["authors"]:
            row = rows.get(a["pid"])
            if row is None:
                row = AuthorRow(pid=a["pid"], name=a["name"], papers=[])
                rows[a["pid"]] = row
            row.papers.append((p["conference"], i, _short_title(p["title"])))
    return list(rows.values())


def _conf_short(display: str) -> str:
    code = next((c.code for c in CONFERENCES if c.display == display), display)
    return {"ndss": "NDSS", "uss": "USENIX", "ccs": "CCS", "sp": "S&P"}.get(code, display)


def _format_papers_cell(papers: list[tuple[str, int, str]]) -> str:
    parts = []
    order = {c.display: i for i, c in enumerate(CONFERENCES)}
    for conf, i, short in sorted(papers, key=lambda x: (order.get(x[0], 99), x[1])):
        parts.append(f"{_conf_short(conf)} #{i} *{short}*")
    return "；".join(parts)


def render_authors_md(papers: list[dict], year: int) -> str:
    rows = aggregate(papers)
    rows.sort(key=lambda r: (-r.count, r.name.lower()))

    high = [r for r in rows if r.count >= 3]
    mid = [r for r in rows if r.count == 2]

    lines: list[str] = []
    lines.append(f"# {year} 作者论文数统计")
    lines.append("")
    lines.append(f"> 共 {len(papers)} 篇 ({_paper_breakdown(papers)})。")
    lines.append("")

    lines.append("## ≥3 篇")
    lines.append("")
    if high:
        lines.append("| 作者 | 篇数 | 论文（会议#） |")
        lines.append("|---|---|---|")
        for r in high:
            lines.append(f"| **{r.name}** | {r.count} | {_format_papers_cell(r.papers)} |")
    else:
        lines.append("（无）")
    lines.append("")

    lines.append("## 2 篇")
    lines.append("")
    if mid:
        mid_sorted = sorted(mid, key=lambda r: r.name.lower())
        lines.append("| 作者 | 论文（会议#） |")
        lines.append("|---|---|")
        for r in mid_sorted:
            lines.append(f"| {r.name} | {_format_papers_cell(r.papers)} |")
    else:
        lines.append("（无）")
    lines.append("")

    return "\n".join(lines)


def _paper_breakdown(papers: list[dict]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for p in papers:
        counts[p["conference"]] += 1
    parts = []
    for c in CONFERENCES:
        if counts.get(c.display):
            parts.append(f"{c.display} {counts[c.display]}")
    return " + ".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser(description="Render output/<year>/authors.md from papers.yaml.")
    ap.add_argument("--year", type=int, required=True)
    args = ap.parse_args()

    papers_path = Path(str(PAPERS_TPL).format(year=args.year))
    papers = yaml.safe_load(papers_path.read_text(encoding="utf-8")) or []
    out_path = Path(str(OUT_TPL).format(year=args.year))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_authors_md(papers, args.year), encoding="utf-8")
    print(f"[stats] -> {out_path}")


if __name__ == "__main__":
    main()
