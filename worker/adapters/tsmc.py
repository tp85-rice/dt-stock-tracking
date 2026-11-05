"""TSMC monthly revenue, year-on-year %, from TSMC's monthly 6-K reports on SEC EDGAR.

params: {"cik": 1046179}
Reads the sentence "revenue for <Month> <Year> was approximately NT$<x> billion, ... an increase of <y> percent
from <Month> <Year-1>". Period label: "Sep 2026" (month abbreviation and year).
"""

from __future__ import annotations

import datetime as dt
import html as htmllib
import re

from worker import sec
from worker.adapters import Reading

_SENTENCE = re.compile(
    r"revenue for (?P<month>[A-Z][a-z]+) (?P<year>\d{4}) was approximately NT\$(?P<nt>[\d,.]+) billion.*?"
    r"(?P<dir>increase|decrease) of (?P<pct>[\d.]+) percent from (?P=month) (?P<prev>\d{4})",
    re.S)


def parse_report(text: str) -> dict | None:
    t = re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", text)))
    m = _SENTENCE.search(t)
    if not m or int(m["prev"]) != int(m["year"]) - 1:
        return None
    pct = float(m["pct"]) * (1 if m["dir"] == "increase" else -1)
    month = dt.datetime.strptime(m["month"], "%B")
    return {"label": f"{month.strftime('%b')} {m['year']}", "yoy": pct, "nt_billion": m["nt"],
            "sentence": m.group(0)[:400]}


def monthly_yoy(ticker: str, signal: str, p: dict, last: int = 2) -> list[Reading]:
    out = []
    for f in sec.list_filings(int(p.get("cik", 1046179)), "6-K", 12):
        names = [n for n in sec.filing_documents(f) if n.startswith("tsm-revenue") and n.endswith(".htm")]
        if not names:
            continue  # other 6-Ks (board meetings, results)
        url = f"{f.folder}/{names[0]}"
        r = parse_report(sec.fetch(url))
        if r:
            out.append(Reading(r["label"], r["yoy"], f.filed, url, r["sentence"],
                               f"TSMC {r['label']} revenue report (6-K filed {f.filed})",
                               notes=f"NT${r['nt_billion']}B", check={"method": "text", "parsed": r}))
        if len(out) >= last:
            break
    return out
