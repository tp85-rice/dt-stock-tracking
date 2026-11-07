"""Code-level checks on an agent's citation. They catch invented quotes and numbers; they cannot tell whether a
real quote actually supports the claim, which stays a human check (the scorecard's 'Citation valid')."""

from __future__ import annotations

import re
import unicodedata

_SPACE = re.compile(r"\s+")
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
                         " ": " "})
_NUM = re.compile(r"(?<![\w.])[-−(]?\$?\s?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*(%|percent|trillion|billion|million|"
                  r"thousand|bn|tn|mn|[bmk]\b)?", re.I)
_SCALE = {"trillion": 1e12, "tn": 1e12, "billion": 1e9, "bn": 1e9, "b": 1e9, "million": 1e6, "mn": 1e6, "m": 1e6,
          "thousand": 1e3, "k": 1e3}
_UNIT_SCALE = {"$t": 1e12, "$b": 1e9, "$bn": 1e9, "$m": 1e6, "$mn": 1e6, "$k": 1e3}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").translate(_QUOTES)
    return _SPACE.sub(" ", text).strip().lower()


def quote_found(quote: str | None, source_text: str | None) -> bool:
    """The quote appears word for word in the source (ignoring case, spacing and curly vs straight quotes)."""
    q = normalize(quote or "")
    return bool(q) and len(q) >= 8 and q in normalize(source_text or "")


def numbers_in(text: str) -> list[float]:
    """Every number in the text, both as written and scaled by a following word (31.6 billion -> 31.6 and 3.16e10)."""
    out = []
    for m in _NUM.finditer((text or "").translate(_QUOTES)):
        n = float(m.group(1).replace(",", "") + (m.group(2) or ""))
        out.append(n)
        word = (m.group(3) or "").lower()
        if word in _SCALE:
            out.append(n * _SCALE[word])
    return out


def close(a: float, b: float, rel: float = 0.005) -> bool:
    """Equal within 0.5% (a quote rounds 31.575 to 31.6)."""
    return a == b or abs(a - b) <= rel * max(abs(a), abs(b))


def value_in_quote(value: float | None, unit: str | None, quote: str | None) -> bool:
    """The value (in the signal's unit, e.g. 31.6 for $B) is one of the numbers in the quote."""
    if value is None:
        return False
    targets = {abs(value)}
    scale = _UNIT_SCALE.get((unit or "").strip().lower().replace(" ", ""))
    if scale:
        targets.add(abs(value) * scale)
    return any(close(t, n) for t in targets for n in numbers_in(quote or ""))


def check(answer: dict, source_text: str | None) -> dict:
    """The check stored with a proposal (proposals.check_result). passed = safe to show a reviewer as pending."""
    found = quote_found(answer.get("quote"), source_text)
    if answer.get("withheld") and answer.get("value") is None:
        in_quote = None  # a withheld metric has no number to find
    else:
        in_quote = value_in_quote(answer.get("value"), answer.get("unit"), answer.get("quote"))
    reasons = []
    if not source_text:
        reasons.append("no source text to check the quote against")
    elif not found:
        reasons.append("quote not found in the source")
    if in_quote is False:
        reasons.append("value not found in the quote")
    return {"check": "quote", "quote_found": found, "value_in_quote": in_quote, "passed": not reasons,
            "reasons": reasons}
