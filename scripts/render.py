"""Render the human-facing papers.md from papers.yaml.

Format mirrors the hand-curated `blockchain_papers_2025.md`: top header with totals,
one section per conference (NDSS → USENIX → CCS → S&P), papers numbered alphabetically
within each section, author names from DBLP without affiliations (affiliations are a
TODO for a future stage that scrapes conference pages).
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import yaml

from scripts.conferences import CONFERENCES

REPO_ROOT = Path(__file__).resolve().parent.parent
PAPERS_TPL = REPO_ROOT / "data" / "{year}" / "papers.yaml"
OUT_TPL = REPO_ROOT / "output" / "{year}" / "papers.md"


def _format_authors(authors: list[dict]) -> str:
    return ", ".join(a["name"] for a in authors)


def render_papers_md(papers: list[dict], year: int) -> str:
    by_conf: dict[str, list[dict]] = defaultdict(list)
    for p in papers:
        by_conf[p["conference"]].append(p)
    for lst in by_conf.values():
        lst.sort(key=lambda p: p["title"].lower())

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    total = len(papers)

    lines: list[str] = []
    lines.append(f"# {year} 四大安全顶会区块链相关论文清单")
    lines.append("")
    lines.append(f"> 生成时间: {today}")
    lines.append("> 数据来源: DBLP")
    lines.append(f"> 总计: {total} 篇")
    lines.append("")
    lines.append("---")
    lines.append("")

    for conf in CONFERENCES:
        items = by_conf.get(conf.display, [])
        lines.append(f"## {conf.display} {year}（{len(items)} 篇）")
        lines.append("")
        for i, p in enumerate(items, 1):
            lines.append(f"### {i}. {p['title']}")
            lines.append(f"- **作者:** {_format_authors(p['authors'])}")
            if p.get("ee"):
                lines.append(f"- **链接:** {p['ee']}")
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Render output/<year>/papers.md from papers.yaml.")
    ap.add_argument("--year", type=int, required=True)
    args = ap.parse_args()

    papers_path = Path(str(PAPERS_TPL).format(year=args.year))
    papers = yaml.safe_load(papers_path.read_text(encoding="utf-8")) or []
    out_path = Path(str(OUT_TPL).format(year=args.year))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_papers_md(papers, args.year), encoding="utf-8")
    print(f"[render] -> {out_path}")


if __name__ == "__main__":
    main()
