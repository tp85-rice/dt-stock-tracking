"""SEC EDGAR feeds from inline-XBRL 10-Q / 10-K filings.

edgar_xbrl params (one company, latest quarter):
    {"cik": 1045810, "measure": "<measure>", ...}
    measure "concept":  value of one fact.  {"concept": "us-gaap:InventoryNet", "instant": true, "divide": 1e9}
                        optional "dims": {"ProductOrServiceAxis": "AICloudsIndustrialEnterpriseMember"}
    measure "margin":   numerator / denominator x 100 for the quarter.
                        {"numerator": "us-gaap:GrossProfit", "denominator": "us-gaap:Revenues"}
    measure "dso":      receivables at quarter end / quarter revenue x days in the quarter.
                        {"receivables": "us-gaap:AccountsReceivableNetCurrent", "revenue": "us-gaap:Revenues"}
    Period label: "<fiscal period> FY<yy>" from the filing's own dei:DocumentFiscalPeriodFocus / FiscalYearFocus.

edgar_capex_sum params (several companies, one calendar quarter):
    {"companies": [{"ticker": "AMZN", "cik": 1018724, "concept": "us-gaap:PaymentsToAcquireProductiveAssets"}, ...],
     "divide": 1e9}
    Cash-flow capex is often reported year-to-date only; the quarter is YTD minus the previous filing's YTD
    (and the 10-K's full year minus the Q3 YTD). Proposed only when every company has reported the quarter.
    Period label: "Q<n> CY<yy>".
"""

from __future__ import annotations

import datetime as dt

from worker import sec
from worker.adapters import Reading


def _fiscal_label(facts: list[sec.Fact]) -> str | None:
    fp, fy = sec.dei(facts, "DocumentFiscalPeriodFocus"), sec.dei(facts, "DocumentFiscalYearFocus")
    if not fp or not fy:
        return None
    fp = "Q4" if fp.upper() == "FY" else fp.upper()
    return f"{fp} FY{str(fy).strip()[-2:]}"


def _period_end(facts: list[sec.Fact], anchor: str) -> dt.date:
    """Latest end date of the anchor concept (the filing's own reporting period)."""
    ends = [f.end for f in facts if f.name == anchor and not f.dims]
    if not ends:
        raise LookupError(f"{anchor} not found in filing")
    return max(ends)


def _latest_report(cik: int) -> tuple[sec.Filing, str, list[sec.Fact]]:
    filings = sec.list_filings(cik, "10-Q", 3) + sec.list_filings(cik, "10-K", 2)
    filings.sort(key=lambda f: f.filed, reverse=True)
    if not filings:
        raise LookupError(f"no 10-Q or 10-K for CIK {cik}")
    f = filings[0]
    url = sec.primary_document(f)
    return f, url, sec.xbrl_facts(sec.fetch(url))


def _fmt(v: float) -> str:
    return f"{v:,.0f}"


def xbrl_signal(ticker: str, signal: str, p: dict) -> list[Reading]:
    filing, url, facts = _latest_report(int(p["cik"]))
    label = _fiscal_label(facts)
    if not label:
        return []
    measure = p.get("measure", "concept")
    anchor = p.get("revenue") or p.get("denominator") or "us-gaap:Revenues"
    end = _period_end(facts, anchor if measure != "concept" or not p.get("instant") else p["concept"])
    # A 10-K reports the fourth quarter only inside the full year; the concept measures need a quarter.
    title = f"{ticker} {filing.form} filed {filing.filed} ({label})"

    if measure == "concept":
        f = sec.pick(facts, p["concept"], end, duration=None if p.get("instant") else "quarter",
                     dims=p.get("dims"))
        if f is None:
            return []
        value = float(f.value) / float(p.get("divide", 1))
        dims = f" [{', '.join(f'{k}={v}' for k, v in f.dims.items())}]" if f.dims else ""
        quote = f"XBRL {f.name}{dims} = {_fmt(float(f.value))} for the period ending {end}"
        return [Reading(label, round(value, 3), filing.filed, url, quote, title,
                        check={"method": "xbrl", "facts": [{"name": f.name, "value": f.value, "end": str(end),
                                                            "dims": f.dims}]})]

    if measure == "margin":
        num = sec.pick(facts, p["numerator"], end, duration="quarter")
        den = sec.pick(facts, p["denominator"], end, duration="quarter")
        if not num or not den or not den.value:
            return []
        value = float(num.value) / float(den.value) * 100
        quote = (f"XBRL {num.name} {_fmt(float(num.value))} / {den.name} {_fmt(float(den.value))} "
                 f"= {value:.2f}% for the quarter ending {end}")
        return [Reading(label, round(value, 2), filing.filed, url, quote, title, notes="Computed from tagged figures.",
                        check={"method": "xbrl_ratio", "numerator": num.value, "denominator": den.value})]

    if measure == "dso":
        ar = sec.pick(facts, p["receivables"], end)
        rev = sec.pick(facts, p["revenue"], end, duration="quarter")
        if not ar or not rev or not rev.value:
            return []
        days = rev.days or 91
        value = float(ar.value) / float(rev.value) * days
        quote = (f"XBRL {ar.name} {_fmt(float(ar.value))} / {rev.name} {_fmt(float(rev.value))} "
                 f"x {days} days = {value:.1f} days")
        return [Reading(label, round(value, 1), filing.filed, url, quote, title,
                        notes="Computed; the company may state a rounded figure in its CFO commentary.",
                        check={"method": "xbrl_dso", "receivables": ar.value, "revenue": rev.value, "days": days})]

    raise ValueError(f"unknown edgar_xbrl measure {measure!r}")


def _calendar_label(end: dt.date) -> str:
    return f"Q{(end.month - 1) // 3 + 1} CY{str(end.year)[-2:]}"


def _quarter_capex(cik: int, concept: str) -> tuple[dt.date, float, sec.Filing, str, str] | None:
    """Latest quarter's capex for one company: (quarter end, value, filing, url, how)."""
    filings = sec.list_filings(cik, "10-Q", 4) + sec.list_filings(cik, "10-K", 2)
    filings.sort(key=lambda f: f.filed, reverse=True)
    reports = []
    for f in filings[:3]:
        url = sec.primary_document(f)
        reports.append((f, url, sec.xbrl_facts(sec.fetch(url))))
        # Stop as soon as the latest quarter can be computed.
        latest_f, latest_url, latest = reports[0]
        cands = [x for x in latest if x.name == concept and not x.dims and x.start]
        if not cands:
            return None
        end = max(x.end for x in cands)
        q = sec.pick(latest, concept, end, duration="quarter")
        if q:
            return end, float(q.value), latest_f, latest_url, "reported for the quarter"
        ytd = sec.pick(latest, concept, end, duration="ytd")
        if ytd is None:
            return None
        if len(reports) < 2:
            continue
        # Previous report's YTD ending the day before this quarter starts.
        qstart = end - dt.timedelta(days=95)
        for _, _, prev in reports[1:]:
            pc = [x for x in prev if x.name == concept and not x.dims and x.start == ytd.start
                  and x.end < end and x.end >= qstart - dt.timedelta(days=10)]
            if pc:
                prior = max(pc, key=lambda x: x.end)
                return end, float(ytd.value) - float(prior.value), latest_f, latest_url, \
                    f"year to date {ytd.start}..{end} minus {ytd.start}..{prior.end}"
    return None


def capex_sum(ticker: str, signal: str, p: dict) -> list[Reading]:
    parts = []
    for c in p["companies"]:
        r = _quarter_capex(int(c["cik"]), c["concept"])
        if r is None:
            return []
        parts.append((c, *r))
    ends = {_calendar_label(end) for _, end, *_ in parts}
    if len(ends) != 1:
        return []  # someone has not reported the latest quarter yet: wait until all have
    label = ends.pop()
    divide = float(p.get("divide", 1e9))
    total = sum(v for _, _, v, *_ in parts) / divide
    lines = [f"{c['ticker']} {v / divide:,.3f}B ({how}; {f.form} filed {f.filed})" for c, _, v, f, _, how in parts]
    observed = max(f.filed for *_, f, _, _ in parts)
    return [Reading(label, round(total, 3), observed, parts[0][4],
                    "; ".join(lines), f"Big-4 capex {label} from four SEC filings",
                    notes=" + ".join(f"{c['ticker']} {v / divide:.3f}" for c, _, v, *_ in parts),
                    check={"method": "xbrl_capex_sum", "parts": [
                        {"ticker": c["ticker"], "value": v, "end": str(end), "filing": u, "how": how}
                        for c, end, v, _, u, how in parts]})]
