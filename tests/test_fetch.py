"""DBLP XML parsing — small inline fixture, no network."""

from __future__ import annotations

from scripts.fetch import parse_inproceedings

SAMPLE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<bht>
<dblpcites>
  <r style="ee">
    <inproceedings key="conf/ndss/AlphaB25" mdate="2025-03-19">
      <author pid="11/2222">Alice Author</author>
      <author pid="33/4444-1">Bob Author 0001</author>
      <title>Some Blockchain Paper.</title>
      <year>2025</year>
      <booktitle>NDSS</booktitle>
      <ee type="oa">https://example.com/paper</ee>
      <crossref>conf/ndss/2025</crossref>
    </inproceedings>
  </r>
  <r>
    <proceedings key="conf/ndss/2025" mdate="2025-03-19">
      <title>NDSS 2025 proceedings.</title>
      <year>2025</year>
    </proceedings>
  </r>
</dblpcites>
</bht>
"""


def test_parses_inproceedings_only() -> None:
    papers = parse_inproceedings(SAMPLE_XML, "ndss", 2025)
    assert len(papers) == 1
    p = papers[0]
    assert p.dblp_key == "conf/ndss/AlphaB25"
    assert p.conference == "ndss"
    assert p.year == 2025
    # Title's trailing period is stripped.
    assert p.title == "Some Blockchain Paper"
    # PID is preserved verbatim, including disambiguation suffixes.
    assert p.authors[0].pid == "11/2222"
    assert p.authors[1].pid == "33/4444-1"
    # Author display name's homonym suffix is stripped from the visible string.
    assert p.authors[1].name == "Bob Author"
    assert p.ee == "https://example.com/paper"
