"""Fetch DBLP per-conference XML and dump a normalised JSON record per paper.

DBLP is the single source of truth for the pipeline: it has stable XML for the four target
conferences, and every author carries a PID we use as the canonical identifier downstream.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from lxml import etree

from scripts.conferences import CONFERENCES, Conference, dblp_xml_url

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR_TPL = REPO_ROOT / "data" / "{year}" / "raw"

# DBLP appends a numeric disambiguation suffix (e.g. "Guang Hua 0001") to homonyms.
# The PID still uniquely identifies the person, so we strip the suffix from display names.
_NAME_DISAMBIG = re.compile(r"\s+\d{4}$")


@dataclass(frozen=True)
class Author:
    pid: str
    name: str  # display name as it appears on this paper, with disambiguation suffix stripped


@dataclass(frozen=True)
class Paper:
    dblp_key: str
    conference: str  # conf code, e.g. "ndss"
    year: int
    title: str
    authors: tuple[Author, ...]
    pages: str | None
    ee: str | None  # primary external link (DOI / openaccess URL)


def _clean_title(text: str) -> str:
    # DBLP titles end with a period. Drop it and collapse internal whitespace.
    text = " ".join(text.split())
    return text[:-1] if text.endswith(".") else text


def _clean_name(text: str) -> str:
    return _NAME_DISAMBIG.sub("", " ".join(text.split()))


def parse_inproceedings(xml_bytes: bytes, conf_code: str, year: int) -> list[Paper]:
    """Return every <inproceedings> in this XML as a Paper.

    DBLP wraps every entry in a <bht>/<dblpcites>/<r> shell; the entries we care about are
    direct children of <r>. Some entries (e.g. front matter) are <proceedings>, which we skip.
    """
    parser = etree.XMLParser(recover=True, resolve_entities=False)
    root = etree.fromstring(xml_bytes, parser=parser)
    papers: list[Paper] = []
    for entry in root.iter("inproceedings"):
        key = entry.get("key", "")
        title_el = entry.find("title")
        if title_el is None or not (title_el.text or "").strip():
            continue
        # Title may contain inline tags (<i>, <sub>); join all text nodes.
        title = _clean_title("".join(title_el.itertext()))
        authors: list[Author] = []
        for author_el in entry.iter("author"):
            pid = author_el.get("pid") or ""
            if not pid:
                continue
            name = _clean_name("".join(author_el.itertext()))
            if name:
                authors.append(Author(pid=pid, name=name))
        ee_el = entry.find("ee")
        pages_el = entry.find("pages")
        papers.append(
            Paper(
                dblp_key=key,
                conference=conf_code,
                year=year,
                title=title,
                authors=tuple(authors),
                pages=(pages_el.text or "").strip() if pages_el is not None else None,
                ee=(ee_el.text or "").strip() if ee_el is not None else None,
            )
        )
    return papers


def _paper_to_dict(p: Paper) -> dict:
    return {
        "dblp_key": p.dblp_key,
        "conference": p.conference,
        "year": p.year,
        "title": p.title,
        "authors": [{"pid": a.pid, "name": a.name} for a in p.authors],
        "pages": p.pages,
        "ee": p.ee,
    }


def fetch_one(conf: Conference, year: int, client: httpx.Client, retries: int = 3) -> list[Paper]:
    url = dblp_xml_url(conf, year)
    last_exc: Exception | None = None
    # DBLP occasionally returns SSL EOFs mid-handshake; a small retry pad keeps the
    # pipeline resilient without papering over a real outage.
    for attempt in range(retries):
        try:
            resp = client.get(url, timeout=60.0, follow_redirects=True)
            resp.raise_for_status()
            return parse_inproceedings(resp.content, conf.code, year)
        except (httpx.HTTPError, httpx.TransportError) as exc:
            last_exc = exc
            if attempt < retries - 1:
                print(f"    retry {attempt + 1}/{retries - 1}: {exc.__class__.__name__}", flush=True)
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}") from last_exc


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch DBLP XML for the four target conferences.")
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()

    out_dir = args.out_dir or Path(str(RAW_DIR_TPL).format(year=args.year))
    out_dir.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": "sec-blockchain-papers/0.1 (+https://github.com)"}
    with httpx.Client(headers=headers) as client:
        for conf in CONFERENCES:
            print(f"[fetch] {conf.display} {args.year} ...", flush=True)
            papers = fetch_one(conf, args.year, client)
            (out_dir / f"{conf.code}.json").write_text(
                json.dumps([_paper_to_dict(p) for p in papers], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"    {len(papers)} papers -> {out_dir / f'{conf.code}.json'}")


if __name__ == "__main__":
    main()
