"""Score agent answers against the gold set in the LLM scorecard.

    python -m worker.agents.evaluate templates/llm_eval_scorecard.xlsx answers.jsonl --version junior-v0.1 \
        --out scored.xlsx

Reads the 'Gold set' tab, matches each answer to its case by Case ID, fills one 'Runs' row per gold case in a copy
of the workbook (--out; the original is never changed), and prints the same summary as the 'Summary' tab, with
PASS / FAIL against its pass targets. A gold case with no answer counts as a schema failure.

What the code decides and what stays with a person:
* Value correct      - automatic: value (within 0.5%) or label, plus unit, period and entity when the gold row has them.
                       Should-abstain cases are correct only if the agent abstained.
* Event / type       - automatic for label tasks (driver, event, Q&A theme); blank for KPI extraction.
* Citation valid     - pre-filled: 1 if the quote is word for word in the gold passage (and holds the value).
                       A person must still confirm the quote supports the claim; the row's Notes say so.
* Hallucination      - automatic: an answer where the gold says abstain, a quote that is not in the passage,
                       or a value that is not in its own quote.
* Schema valid       - automatic (answers.schema_problems).
The column layout follows templates/build_templates.py; if the scorecard's columns change, update GOLD and RUNS.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

import openpyxl

from worker.agents import answers as answers_mod
from worker.agents.checks import close, normalize, quote_found, value_in_quote

# 1-based column numbers in the scorecard tabs.
GOLD = {"case_id": 1, "ticker": 2, "passage": 7, "task": 8, "answer": 9, "unit": 10, "period": 11, "entity": 12,
        "abstain": 13, "hard": 14}
RUNS = {"run_id": 1, "case_id": 2, "version": 3, "output": 5, "cited": 6, "value_ok": 7, "type_ok": 8,
        "citation_ok": 9, "hallucination": 10, "schema_ok": 11, "reviewer": 12, "date": 13, "notes": 14}
LABEL_TASKS = {"driver extraction", "event extraction", "q&a theme"}
_NUMBER = re.compile(r"^[-−]?\$?\s?[\d,]*\.?\d+\s*%?$")


def _num(text) -> float | None:
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return float(text)
    s = str(text or "").strip()
    if not _NUMBER.match(s):
        return None
    return float(s.replace("$", "").replace(",", "").replace("%", "").replace("−", "-").strip())


def _same(a, b) -> bool:
    return normalize(str(a or "")).replace(" ", "") == normalize(str(b or "")).replace(" ", "")


def read_gold(wb) -> list[dict]:
    ws = wb["Gold set"]
    out = []
    for r in range(2, ws.max_row + 1):
        get = lambda k: ws.cell(row=r, column=GOLD[k]).value  # noqa: E731
        if get("case_id") in (None, ""):
            continue
        out.append({k: get(k) for k in GOLD} | {"_row": r})
    return out


def score(gold: dict, a: dict | None) -> dict:
    """One Runs row (1/0 values; None = leave blank) plus notes."""
    task = normalize(str(gold.get("task") or ""))
    is_label_task = task in LABEL_TASKS
    if a is None:
        return {"value_ok": 0, "type_ok": 0 if is_label_task else None, "citation_ok": 0, "hallucination": 0,
                "schema_ok": 0, "output": "(no answer)", "cited": None, "notes": "no answer for this case"}
    probs = answers_mod.schema_problems(a, "evaluate")
    should_abstain = str(gold.get("abstain") or "").strip().upper() == "Y"
    abstained = bool(a.get("abstain"))
    value, label = a.get("value"), a.get("label")
    output = "abstained" if abstained else (str(value) if value is not None else str(label or ""))
    if a.get("unit") and not abstained:
        output += f" {a['unit']}"
    notes = []

    if should_abstain:
        value_ok = int(abstained)
        type_ok = int(abstained) if is_label_task else None
        citation_ok = int(abstained)
        hallucination = int(not abstained)
        if not abstained:
            notes.append("gold says the passage has no answer, but the agent answered")
    elif abstained:
        value_ok, type_ok, citation_ok, hallucination = 0, (0 if is_label_task else None), 0, 0
        notes.append("agent abstained but the gold has an answer")
    else:
        gold_num = _num(gold.get("answer"))
        if gold_num is not None:
            core = value is not None and close(float(value), gold_num)
        else:
            core = _same(label if label is not None else value, gold.get("answer"))
        extras = all(_same(a.get(k), gold[k]) for k in ("unit", "period") if gold.get(k) not in (None, ""))
        if gold.get("entity") not in (None, ""):
            ge, ae = normalize(str(gold["entity"])), normalize(str(a.get("entity") or ""))
            extras = extras and bool(ae) and (ge in ae or ae in ge)  # "NVIDIA" matches "NVIDIA Corporation"
        value_ok = int(core and extras)
        type_ok = int(_same(label, gold.get("answer"))) if is_label_task else None
        in_passage = quote_found(a.get("quote"), gold.get("passage"))
        holds_value = value is None or value_in_quote(float(value), a.get("unit"), a.get("quote"))
        citation_ok = int(in_passage and holds_value)
        hallucination = int(not in_passage or not holds_value)
        if not in_passage:
            notes.append("quote not found in the gold passage")
        if not holds_value:
            notes.append("value not in its own quote")
        if citation_ok:
            notes.append("Citation valid pre-filled: a person must confirm the quote supports the claim")
    if probs:
        notes.append("schema: " + "; ".join(probs))
    return {"value_ok": value_ok, "type_ok": type_ok, "citation_ok": citation_ok, "hallucination": hallucination,
            "schema_ok": int(not probs), "output": output, "cited": a.get("quote"), "notes": "; ".join(notes)}


def summarise(rows: list[dict], tasks: list[str]) -> dict:
    def rate(key, subset):
        vals = [r[key] for r in subset if r[key] is not None]
        return sum(vals) / len(vals) if vals else None
    keys = ("value_ok", "type_ok", "citation_ok", "hallucination", "schema_ok")
    overall = {k: rate(k, rows) for k in keys} | {"n": len(rows)}
    by_task = {}
    for t in sorted(set(tasks)):
        sub = [r for r, tt in zip(rows, tasks) if tt == t]
        by_task[t] = {k: rate(k, sub) for k in keys} | {"n": len(sub)}
    return {"overall": overall, "by_task": by_task}


def targets(wb) -> dict:
    ws = wb["Summary"]
    v = lambda c: float(ws[c].value) if ws[c].value is not None else None  # noqa: E731
    return {"value_ok": v("B2"), "citation_ok": v("B3"), "hallucination": v("B4"), "schema_ok": v("B5")}


def verdict(overall: dict, t: dict) -> str:
    need = [overall["value_ok"], overall["citation_ok"], overall["hallucination"], overall["schema_ok"]]
    if any(x is None for x in need):
        return "not enough data"
    ok = (overall["value_ok"] >= t["value_ok"] and overall["citation_ok"] >= t["citation_ok"]
          and overall["hallucination"] <= t["hallucination"] and overall["schema_ok"] >= t["schema_ok"])
    return "PASS" if ok else "FAIL"


def evaluate(scorecard: str | Path, answers_path: str | Path, version: str, out: str | Path | None = None,
             today: dt.date | None = None) -> dict:
    wb = openpyxl.load_workbook(scorecard)
    gold = read_gold(wb)
    items = answers_mod.load(answers_path)
    by_case = {}
    extra = []
    for a in items:
        cid = a.get("case_id") if isinstance(a, dict) else None
        (extra.append(a) if cid is None or cid in by_case else by_case.__setitem__(str(cid).strip(), a))
    gold_ids = {str(g["case_id"]).strip() for g in gold}
    unknown = sorted(set(by_case) - gold_ids)
    rows = [score(g, by_case.get(str(g["case_id"]).strip())) for g in gold]
    tasks = [str(g.get("task") or "Other") for g in gold]
    summary = summarise(rows, tasks)
    t = targets(wb)
    result = {"version": version, "cases": len(gold), "answers": len(items), "unknown_case_ids": unknown,
              "unmatched_lines": len(extra), "targets": t, "summary": summary,
              "verdict": verdict(summary["overall"], t), "rows": rows}

    if out:
        ws = wb["Runs"]
        r = 2
        while ws.cell(row=r, column=RUNS["case_id"]).value not in (None, ""):
            r += 1
        start_id = r - 1
        for i, (g, row) in enumerate(zip(gold, rows)):
            cells = {"run_id": f"{version}-{start_id + i}", "case_id": g["case_id"], "version": version,
                     "output": row["output"], "cited": row["cited"], "value_ok": row["value_ok"],
                     "type_ok": row["type_ok"], "citation_ok": row["citation_ok"],
                     "hallucination": row["hallucination"], "schema_ok": row["schema_ok"], "reviewer": "auto",
                     "date": today or dt.date.today(), "notes": row["notes"] or None}
            for k, v in cells.items():
                ws.cell(row=r + i, column=RUNS[k]).value = v
        # Make the Summary tab show this version.
        sm = wb["Summary"]
        for rr in range(10, 20):
            if sm[f"A{rr}"].value in (None, "", version):
                sm[f"A{rr}"].value = version
                break
        sm["D22"].value = version
        wb.save(out)
    return result


def _pct(x):
    return "  -  " if x is None else f"{x * 100:5.1f}%"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Score agent answers against the scorecard's gold set.")
    ap.add_argument("scorecard")
    ap.add_argument("answers")
    ap.add_argument("--version", required=True, help="prompt / model version label, e.g. junior-v0.1")
    ap.add_argument("--out", help="write a scored copy of the workbook here (the original is not changed)")
    args = ap.parse_args(argv)
    if args.out and Path(args.out).resolve() == Path(args.scorecard).resolve():
        ap.error("--out must be a different file from the scorecard")
    res = evaluate(args.scorecard, args.answers, args.version, args.out)
    o, t = res["summary"]["overall"], res["targets"]
    print(f"{res['version']}: {res['cases']} gold case(s), {res['answers']} answer line(s)")
    if res["unknown_case_ids"]:
        print(f"  answers for unknown cases (ignored): {', '.join(res['unknown_case_ids'])}")
    if res["unmatched_lines"]:
        print(f"  {res['unmatched_lines']} line(s) with no case_id or a repeated case_id (ignored)")
    print(f"  Value correct   {_pct(o['value_ok'])}  (target >= {_pct(t['value_ok']).strip()})")
    print(f"  Event / type    {_pct(o['type_ok'])}")
    print(f"  Citation valid  {_pct(o['citation_ok'])}  (target >= {_pct(t['citation_ok']).strip()}; pre-filled, needs a person)")
    print(f"  Hallucination   {_pct(o['hallucination'])}  (target <= {_pct(t['hallucination']).strip()})")
    print(f"  Schema valid    {_pct(o['schema_ok'])}  (target >= {_pct(t['schema_ok']).strip()})")
    for task, s in res["summary"]["by_task"].items():
        print(f"    {task:<18} n={s['n']:<3} value {_pct(s['value_ok'])}  citation {_pct(s['citation_ok'])}  "
              f"hallucination {_pct(s['hallucination'])}")
    print(f"Result: {res['verdict']}" + (f"  (scored copy: {args.out})" if args.out else ""))
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
