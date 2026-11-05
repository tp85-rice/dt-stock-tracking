"""Read SEC EDGAR filings from www.sec.gov.

* list_filings(cik, form): recent filings of one form type (via EDGAR's company browse feed).
* primary_document(filing): the main document of a filing (the inline-XBRL report).
* xbrl_facts(html): tagged numbers in an inline-XBRL document, with their periods and dimensions.

SEC asks every client to identify itself (User-Agent) and to stay under 10 requests per second.
"""

from __future__ import annotations

import datetime as dt
import html as htmllib
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

SEC = "https://www.sec.gov"
USER_AGENT = os.environ.get("SEC_USER_AGENT", "dt-stock-tracking tp85@rice.edu")
_MIN_INTERVAL = 0.2  # seconds between requests: well under SEC's 10 per second
_last_request = 0.0


_cache: dict[str, str] = {}
RETRIES = 3            # extra attempts after the first
BACKOFF = 5.0          # seconds; doubles each retry (5, 10, 20)


def _get(url: str, timeout: int) -> str:
    global _last_request
    wait = _MIN_INTERVAL - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    finally:
        _last_request = time.monotonic()


def _retryable(exc: Exception) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in (429, 500, 502, 503, 504)
    return isinstance(exc, (TimeoutError, urllib.error.URLError, ConnectionError, OSError))


def fetch(url: str, timeout: int = 90) -> str:
    """GET with SEC's rate limit, retries on timeouts and server errors, and a per-run cache.
    Several signals often read the same filing: it is downloaded once per run."""
    if url in _cache:
        return _cache[url]
    for attempt in range(RETRIES + 1):
        try:
            text = _get(url, timeout)
            break
        except Exception as exc:  # noqa: BLE001 - classified below
            if attempt == RETRIES or not _retryable(exc):
                raise
            time.sleep(BACKOFF * 2 ** attempt)
    # Filing lists change during the day; documents in Archives never do.
    if "/Archives/" in url:
        _cache[url] = text
    return text


@dataclass
class Filing:
    cik: str
    form: str
    filed: dt.date
    index_url: str           # .../<accession>-index.htm
    folder: str = ""         # .../Archives/edgar/data/<cik>/<accession without dashes>

    def __post_init__(self):
        if not self.folder:
            self.folder = self.index_url.rsplit("/", 1)[0]


def list_filings(cik: str | int, form: str, count: int = 10) -> list[Filing]:
    """Newest first. Uses EDGAR's company browse feed (Atom) on www.sec.gov."""
    url = (f"{SEC}/cgi-bin/browse-edgar?action=getcompany&CIK={int(cik):010d}&type={form}"
           f"&dateb=&owner=include&count={max(count, 10)}&output=atom")
    feed = fetch(url)
    out = []
    for entry in re.findall(r"<entry>.*?</entry>", feed, re.S):
        def tag(t: str) -> str:
            m = re.search(f"<{t}>(.*?)</{t}>", entry, re.S)
            return m.group(1).strip() if m else ""
        if tag("filing-type") != form:
            continue  # the feed also returns amendments (e.g. 10-Q/A) for type=10-Q
        out.append(Filing(str(int(cik)), form, dt.date.fromisoformat(tag("filing-date")), tag("filing-href")))
    out.sort(key=lambda f: f.filed, reverse=True)
    return out[:count]


def filing_documents(filing: Filing) -> list[str]:
    idx = json.loads(fetch(filing.folder + "/index.json"))
    return [i["name"] for i in idx["directory"]["item"]]


_PRIMARY = re.compile(r"^[a-z0-9]+-\d{8}\.htm$")


def primary_document(filing: Filing) -> str:
    """URL of the main inline-XBRL document (named like nvda-20260726.htm)."""
    names = filing_documents(filing)
    for n in names:
        if _PRIMARY.match(n):
            return f"{filing.folder}/{n}"
    raise LookupError(f"no primary document in {filing.index_url}: {names[:10]}")


@dataclass
class Fact:
    name: str                       # e.g. us-gaap:Revenues
    value: float | str
    start: dt.date | None           # None for instants
    end: dt.date                    # period end (or the instant)
    dims: dict[str, str] = field(default_factory=dict)   # e.g. {"ProductOrServiceAxis": "DataCenterMember"}

    @property
    def days(self) -> int | None:
        return (self.end - self.start).days + 1 if self.start else None


def _date(s: str) -> dt.date:
    return dt.date.fromisoformat(s.strip()[:10])


def xbrl_facts(doc: str) -> list[Fact]:
    """All numeric and dei facts of an inline-XBRL document. Duplicates (same name, period, dims) collapsed."""
    contexts: dict[str, tuple[dt.date | None, dt.date, dict[str, str]]] = {}
    for m in re.finditer(r'<xbrli:context id="([^"]+)">(.*?)</xbrli:context>', doc, re.S):
        body = m.group(2)
        s = re.search(r"<xbrli:startDate>(.*?)<", body)
        e = re.search(r"<xbrli:endDate>(.*?)<", body)
        i = re.search(r"<xbrli:instant>(.*?)<", body)
        dims = {d.split(":")[-1]: v.strip().split(":")[-1]
                for d, v in re.findall(r'dimension="([^"]+)">([^<]+)<', body)}
        if s and e:
            contexts[m.group(1)] = (_date(s.group(1)), _date(e.group(1)), dims)
        elif i:
            contexts[m.group(1)] = (None, _date(i.group(1)), dims)

    facts: dict[tuple, Fact] = {}
    # Two separate passes: a nonNumeric text block can wrap many nonFraction facts, so one combined pattern
    # would swallow every number inside long text blocks.
    matches = [("nonFraction", m) for m in re.finditer(r"<ix:nonFraction([^>]*)>(.*?)</ix:nonFraction>", doc, re.S)]
    matches += [("nonNumeric", m) for m in re.finditer(r"<ix:nonNumeric([^>]*)>(.*?)</ix:nonNumeric>", doc, re.S)
                if 'name="dei:' in m.group(1)]
    for kind, m in matches:
        attrs, raw = m.groups()
        name = re.search(r'name="([^"]+)"', attrs)
        ctx = re.search(r'contextRef="([^"]+)"', attrs)
        if not name or not ctx or ctx.group(1) not in contexts:
            continue
        name = name.group(1)
        text = htmllib.unescape(re.sub(r"<[^>]+>", "", raw)).strip()
        if kind == "nonNumeric":
            if not name.startswith("dei:"):
                continue
            value: float | str = text
        else:
            if 'xsi:nil="true"' in attrs:
                continue
            num = text.replace(",", "").replace("$", "").strip()
            if num in ("", "-", "—", "–"):
                num = "0"
            try:
                value = float(num)
            except ValueError:
                continue
            scale = re.search(r'scale="(-?\d+)"', attrs)
            if scale:
                value *= 10 ** int(scale.group(1))
            if 'sign="-"' in attrs:
                value = -value
        start, end, dims = contexts[ctx.group(1)]
        key = (name, start, end, tuple(sorted(dims.items())))
        facts.setdefault(key, Fact(name, value, start, end, dims))
    return list(facts.values())


def dei(facts: list[Fact], name: str) -> str | None:
    """A document-level fact such as DocumentPeriodEndDate, DocumentFiscalPeriodFocus, DocumentFiscalYearFocus."""
    for f in facts:
        if f.name == f"dei:{name}" and not f.dims:
            return str(f.value)
    return None


def pick(facts: list[Fact], name: str, end: dt.date, *, duration: str | None = None,
         dims: dict[str, str] | None = None) -> Fact | None:
    """The fact `name` ending on `end` with exactly `dims`.
    duration: None = instant; 'quarter' = 80-100 days; 'ytd' = the longest duration ending on `end`."""
    dims = dims or {}
    cands = [f for f in facts if f.name == name and f.end == end and f.dims == dims]
    if duration is None:
        cands = [f for f in cands if f.start is None]
    elif duration == "quarter":
        cands = [f for f in cands if f.days and 80 <= f.days <= 100]
    else:
        cands = sorted([f for f in cands if f.days], key=lambda f: f.days or 0, reverse=True)
    return cands[0] if cands else None
