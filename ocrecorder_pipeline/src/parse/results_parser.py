"""Parse result-table rows from saved HTML pages."""

from __future__ import annotations

import re


def parse_apn_list(apn_raw: str) -> list[str]:
    if not apn_raw:
        return []
    parts = re.split(r"[;,/|]+", apn_raw)
    cleaned = [p.strip() for p in parts if p.strip()]
    return cleaned


def parse_results(html: str) -> list[dict]:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("beautifulsoup4 is required for HTML parsing. Install with: pip install 'ocrecorder-pipeline[acquire]'") from exc

    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    for tr in soup.select("table tr"):
        cols = [td.get_text(" ", strip=True) for td in tr.select("td")]
        if len(cols) < 5:
            continue
        rows.append(
            {
                "doc_number": cols[0],
                "record_date": cols[1],
                "doc_type": cols[2],
                "parties_raw": cols[3],
                "apn_raw": cols[4],
                "apn_list": parse_apn_list(cols[4]),
            }
        )
    return rows
