"""Shared conference metadata used by every pipeline stage."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Conference:
    code: str
    display: str
    dblp_slug: str
    section_title: str


CONFERENCES: list[Conference] = [
    Conference("ndss",   "NDSS",            "ndss", "NDSS"),
    Conference("uss",    "USENIX Security", "uss",  "USENIX Security"),
    Conference("ccs",    "ACM CCS",         "ccs",  "ACM CCS"),
    Conference("sp",     "IEEE S&P",        "sp",   "IEEE S&P"),
]


CONF_BY_CODE: dict[str, Conference] = {c.code: c for c in CONFERENCES}


def dblp_xml_url(conf: Conference, year: int) -> str:
    return f"https://dblp.org/db/conf/{conf.dblp_slug}/{conf.dblp_slug}{year}.xml"
