"""One agent answer = one JSON object per line (JSON lines file).

    {"case_id": "G07",                  # gold set case (evaluation only)
     "ticker": "NVDA", "signal_code": "S7",
     "value": 31.6,                     # a number, or null when abstaining or when the answer is a label
     "label": null,                     # event / driver / theme label, for non-numeric tasks
     "unit": "$B", "period": "Q2 FY27", "entity": "NVIDIA",
     "observed_on": "2026-08-26",       # date the figure was published
     "abstain": false,                  # true = "not in the passage"
     "quote": "Inventory was $31.6 billion, up from $25.8 billion sequentially",
     "source_url": "https://www.sec.gov/...", "source_title": "NVIDIA Q2 FY27 CFO commentary",
     "source_text": "...",              # the fetched document text the quote is checked against (submit only)
     "confidence": 0.9,
     "model": "claude-...", "prompt_version": "junior-v0.1",
     "usage": {"input_tokens": 1200, "output_tokens": 150}}

Only the keys needed by the step that reads the file are required (see REQUIRED).
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

KNOWN = {"case_id", "ticker", "signal_code", "value", "label", "unit", "period", "entity", "observed_on", "abstain",
         "quote", "source_url", "source_title", "source_text", "confidence", "model", "prompt_version", "usage",
         "arrow", "notes", "withheld"}

REQUIRED = {
    "evaluate": {"case_id"},
    "submit": {"ticker", "signal_code", "period", "observed_on", "quote", "source_url"},
}


def schema_problems(a: dict, step: str) -> list[str]:
    """Empty list = the answer has the expected shape (the scorecard's 'Schema valid' check)."""
    if not isinstance(a, dict):
        return ["not a JSON object"]
    if "_parse_error" in a:
        return [f"not valid JSON ({a['_parse_error']})"]
    probs = [f"unknown key {k!r}" for k in sorted(set(a) - KNOWN) if not k.startswith("_")]
    probs += [f"missing {k!r}" for k in sorted(REQUIRED[step] - set(a))]
    abstain = a.get("abstain", False)
    if not isinstance(abstain, bool):
        probs.append("'abstain' must be true or false")
    v = a.get("value")
    if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))):
        probs.append("'value' must be a number or null")
    if not abstain and v is None and not a.get("label") and not a.get("withheld"):
        probs.append("no value or label, and not abstaining")
    c = a.get("confidence")
    if c is not None and (not isinstance(c, (int, float)) or not 0 <= c <= 1):
        probs.append("'confidence' must be between 0 and 1")
    if a.get("observed_on"):
        try:
            dt.date.fromisoformat(str(a["observed_on"]))
        except ValueError:
            probs.append("'observed_on' must be YYYY-MM-DD")
    u = a.get("usage")
    if u is not None and not (isinstance(u, dict) and all(isinstance(u.get(k, 0), int) for k in ("input_tokens", "output_tokens"))):
        probs.append("'usage' must have integer input_tokens and output_tokens")
    return probs


def load(path: str | Path) -> list[dict]:
    """Each line parsed; a line that is not valid JSON becomes {"_parse_error": ...} so it scores as schema-invalid."""
    out = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            obj = {"_parse_error": f"line {n}: {exc}"}
        if isinstance(obj, dict):
            obj["_line"] = n
        out.append(obj)
    return out
