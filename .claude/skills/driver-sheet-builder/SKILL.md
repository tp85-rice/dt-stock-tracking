---
name: driver-sheet-builder
description: "Build or refresh a ticker's driver spreadsheet (inputs/[TICKER]_driver_sheet.xlsx) for the stock driver tracker: drivers, signals, base case, event ladder, sources and readings, researched and cited, as a draft for the owners to review before import. Use for 'Build driver sheet for [TICKER]', 'Refresh [TICKER] driver sheet', or the driver-definition step of the agent pipeline."
---

# Driver Sheet Builder

Produces a filled, validated copy of `templates/stock_driver_template.xlsx` (template v2) for one ticker. It is the driver-definition step of the pipeline: the owners review the sheet, then import it with `python -m worker.import_xlsx`. From M5 on, the junior and senior analyst agents only update signals that this sheet defines.

This skill combines the parts of `thesis-research-bundle/` that define drivers, adapted to the app's rules. Where the bundle and this file disagree, **this file wins**.

## Sources of method (read these, and only these parts)

| File | Use | Do NOT use |
|---|---|---|
| `thesis-research-bundle/skills/thesis-driver-dashboard/SKILL.md` | BUILD Steps 1–3: mining drivers, driver types, indicators, binding constraint, evidence grade, methodology traps, disclosure behaviour, falsification tests, anchored thresholds, kill switches | Step 3 price cases and probabilities, Step 4 roll-ups to a thesis colour, Step 5 rating moves, the dashboard template |
| `thesis-research-bundle/skills/thesis-discussion-loop/SKILL.md` | "Disciplines": look up anything current, never recall it; grade evidence; show conflicting figures side by side; treat disclosure behaviour as data; pre-register dated predictions | Rating, fair value, scenarios, judgment log mechanics (those belong to discussion sessions with the owners) |
| `thesis-research-bundle/reference/Equity_Research_Master_Instructions.md` | Master Prompt 1, Section 1 (business model, the 3–5 KPIs, 1.7 management changes, 1.8 AI leverage for non-biotech names), Section 4 (what would break the thesis), Section 6 (catalyst watch) | "About Me" and everything personal, the portfolio description, Section 2 price targets, Section 7, Master Prompts 2–3, entry tickets. Do not read or repeat personal information |
| `research/House_Rules.md` | Apply every approved rule silently | — |
| `research/[TICKER]/` | Earlier spec, research notes, and the thesis state file if the owners have run a discussion session | Any holdings or trade details, if they ever appear: ignore them |

## Hard rules (the app's, non-negotiable)

1. **No advice in the sheet.** No rating, fair value, price target, valuation zone, buy / sell / hold wording, or "should". Thesis-session outputs like these stay in `research/[TICKER]/[TICKER]_Thesis_State.md`, never in the sheet, the database or the app.
2. **Colours follow the app, not the bundle.** GREEN = at or ahead of the Consensus base case; YELLOW = behind but within the tolerance band; RED = worse than tolerance, or a withheld metric; GREY = missing, stale or no base case. A reading that matches the base case is GREEN.
3. **Colours are scored against the Consensus row; when a signal has no Consensus row for that version and period, against the Thesis row** (our own estimate; the app shows it as "vs our estimate"). Consensus always wins when both exist. Management (guidance) rows are reference lines. (Owner decision 2026-11-07, see `research/OPEN_DECISIONS.md`.)
4. **No stock-level score.** Colours exist per signal; the app shows driver status (signal counts, narrative-only) but no single thesis colour.
5. **Never invent a number.** If it is not in a page you opened, leave the cell blank and list it under Gaps. A gap is better than a wrong number.
6. **Every number is cited** with a Source ID that resolves to a URL in the Source log. Re-source news and AI-summary figures to the filing or press release; if you cannot, the source is Tier C and the reliability note says so.

## Procedure

### 1. Gather current facts (look them up; never recall)

For the latest reported quarter and the next one: the 3–5 KPIs that best measure the business, segment revenue, margins, balance-sheet items tied to risk drivers, management guidance, the next earnings date, analyst consensus for the next quarter (and the pre-report consensus for the last one, so readings can be scored now), regulatory or contract events, recent definition changes or metrics the company stopped reporting. Record each fact with value, unit, period, URL, publication date, and evidence grade (company / third-party / rumor). Write them to `research/[TICKER]/research_notes.md` as you go.

### 2. Drivers (Drivers tab)

3–6 drivers that could move fair value meaningfully within 1–5 years. For each: ID `D1…`, name, a 1–2 sentence thesis about the business (not the stock price), valuation mechanism (revenue growth / margin / multiple / risk), horizon 1–5, impact H/M/L, direction, evidence (Source IDs), confidence, and the v2 fields:
- **Type**: Core (funds everything), Option (not yet in earnings, large share of value), Mechanism (an enabler other drivers depend on), Event (a dated binary).
- **Share of price** (0–1): rough share of today's price the driver carries. A judgment; say how you got it in Notes. Leave blank rather than guess wildly.
- **Depends on**: Driver IDs this one sits on (Mechanisms).

### 3. Signals (Signals tab)

2–5 per driver, at least one Tier A or B per driver (otherwise it shows narrative-only).
- Prefer **leading over lagging**; ask "what has to be true before this shows up in earnings?"
- Mark exactly one **binding constraint** per driver (`Y`): the indicator that gates the driver.
- Mark **kill switches** (`Y`): conditions that break the driver regardless of everything else.
- **Tier** = evidence grade of the source: company-confirmed = A, third-party data = B, rumor / social / AI summary = C.
- **Polarity** is per driver (customer capex is good for a supplier, a cash drain for the spender). Use "Event ladder" for milestone signals.
- **Tolerance band** (fraction of the base value): set it where the bear case starts. If the bear threshold is X and the base case is B, tolerance ≈ |B − X| / |B|. Write the reasoning in **Threshold anchor**, anchored to something external (guidance range, a competitor's disclosed figure, the metric's own history, the level where the base case breaks). Never a round number from the air.
- **Max staleness**: about 100 days for quarterly, 45 for monthly, 10 for weekly.
- **Notes**: which feed will update it later (`EDGAR: <XBRL tag>`, `FRED: <series>`, `TSMC monthly release`, `agent: web`), and methodology traps (small samples, definition changes, authorization vs operation, self-selected data).
- **Definition change**: date and note whenever the company redefined the metric (House Rule). Start a new Signal ID at the break.

### 4. Base case (Base case tab)

Version `v1` for the first snapshot, snapshot date = today. Never edit an imported row; later snapshots are `v2`, `v3`.
- **Consensus** rows (scored): analyst consensus per numeric signal and period. **Where it comes from (owner decision 2026-11-07):** the consensus quoted in news coverage of the results (e.g. "analysts expected $X, according to LSEG"). Log the article in the Source log with Tier C, Cost Free and **Redistribute on site? = No**; put the publisher and the consensus provider named in the article in Notes. The app shows the colour and the variance, never the consensus number itself (only reviewers see it on /review). If no article quotes a figure for a signal, leave it for the Thesis row.
- **Thesis** rows (scored only when there is no Consensus row): our own estimate for signals that have no consensus (e.g. TSMC monthly YoY, inventory, DSO, supply commitments, capex). Say in Notes how it was set (guidance, run-rate, thesis discussion). Mark these as a draft for the owners: a Thesis row is approved when the owners import the sheet.
- **Management** rows: company guidance (midpoint; put the range in Notes).
- **Thesis** rows: our own base case from the thesis work, anchored as in Step 3.
- Include the **last reported period** with the pre-report consensus where you can find it, so the dashboard has colours before the next print.
- **No hindsight:** a base row for a period already reported may use only what was known before the result: the pre-report consensus, the company's prior guidance, or a rule fixed in advance (e.g. "at least the prior quarter", "prior quarter scaled by guided revenue growth", "8-quarter average"). Never set it from the result. Write the rule in the row's Notes (NVDA, 2026-11-09).
- **Guidance in another currency or basis** (e.g. TSMC guides in US$, reports monthly in NT$): convert with the company's own stated assumption and say so in Notes.
- Period labels: company fiscal labels (`Q3 FY27`) for company metrics, calendar labels (`Q3 CY26`) for cross-company metrics, and `Oct 2026` for monthly ones. Exactly the same label in Base case and Scoring log.

### 5. Event ladder (Event ladder tab)

One row per step, with **Kind**:
- **Disclosure**: a metric the company should disclose at a natural occasion (an earnings call). If the occasion passes without it, set Status = Failed (RED) and add a Scoring log row with Withheld = Y (House Rule).
- **Falsification test**: one per driver where possible, dated and checkable ("X by date").
- **Thesis breaker**: the observable conditions from Master Prompt 1 Section 4.
- **Catalyst**: dated events from Section 6 (earnings, launches, rulings).
- **Milestone**: steps of an event-ladder signal.
Target date = the base-case date; leave blank when the base case expects it not to happen.

### 6. Source log and Scoring log

- Source log: one row per document actually opened: name, URL, date accessed, tier, access method, cost, terms note, **Redistribute on site?** (`Yes` for SEC filings and company releases, `No` for paywalled or aggregator data).
- Scoring log: the latest reported reading per numeric signal (and the prior one or two for the arrow), with base case version, period, source, and arrow (Accelerating / Flat / Decelerating / n/a). Withheld = Y only after a natural disclosure occasion has been skipped.

### 7. Write, check, report

1. Write `research/[TICKER]/driver_spec.json` in the shape documented at the top of `worker/sheet_writer.py`. README: ticker, archetype, `owner_note` = `Draft by agent <date>, unreviewed`.
2. Run `python -m worker.sheet_writer research/[TICKER]/driver_spec.json inputs/[TICKER]_driver_sheet.xlsx`. Fix every `[ERROR]`; read every `[WARNING]` and either fix it or explain it in the report.
3. Report to the owners in the reply, briefly: drivers with type and binding constraint; which signals are scored now vs. GREY and why; every **Gap** (number not found, consensus missing, disclosure uncertain); every **conflict** between sources; decisions the owners must make. Do not import; the owners review first.

## Starting from an owners' base case file

The owners may hand over their own research file for a ticker (first case: `research/GRAB/GRAB_Base_Case_and_Dashboard.md`, Nov 2026): a base case, a driver dashboard with signals, readings, history, thresholds, sources, and often a machine-readable JSON appendix. Treat it as the research for Steps 1–6, not as the sheet. Worked example: `research/GRAB/research_notes.md` and `research/GRAB/driver_spec.json`.

1. **Keep the file** in `research/[TICKER]/` unchanged, as the record. It may contain ratings, prices and fair values; they stay there (Hard rule 1).
2. **Check the numbers against primary sources** before using them: open the filings (SEC 10-Q / 10-K, or 6-K Exhibit 99.1 press releases for foreign issuers) for the latest quarter and every history point. Use the filing's figure; list every correction, every `[VERIFY]` you resolved, and every definition change you found in the research notes. Re-source history rows to the filing that reported them; date each reading with the filing date.
3. **Map the base case** by the file's own labels (its JSON `base_type` field, or "(consensus)" / "(our est.)" in the tables):
   - consensus → **Consensus** row (source logged per decision 1: Tier C, Redistribute = No). Conflicting consensus figures: one Consensus row (the one quoted as consensus), the other as a Management or note.
   - figures implied by company guidance → **Management** row (midpoint; range in Notes). If the file uses them as the base case for the next print and no consensus exists, add a **Thesis** row with the same value.
   - our estimate with a green line ("≥20%", "at least $2.0B") → **Thesis** row = that line, for the latest period and the next one.
   - a red, breach or thesis-break line → **tolerance** = |base − line| / |base| (Threshold anchor says where it came from). A breach line with no green line → Thesis row = the breach line, tolerance 0 or as stated.
   - "no base case" → no row (GREY), even if the file shows a colour; put any alert line in Threshold anchor.
   - no red line given → propose a tolerance anchored to the metric's own history or the guidance range, and say "Proposed by Claude; owners to confirm" in Threshold anchor and in the report. Once the owners accept, change it to "Set by Claude, accepted by the owners <date>" (GRAB, 2026-11-08).
   - conflicting lines in the owners' notes (e.g. a thesis-break threshold that moved) → use the latest one, note the other, and log it in `research/OPEN_DECISIONS.md` with the owner who will settle it.
4. **Non-numeric signals** (regulation, ratings, index reviews, deal approvals): polarity Event ladder. Breach conditions are **Thesis breaker** steps (Status Failed = it happened, RED; Pending = not yet); dated events are **Catalyst** or **Milestone** steps. Put past negative events in Notes, not as Occurred steps (an Occurred step shows GREEN).
5. **The file's thesis-break and catalyst tables** become Event ladder steps on the matching signals; disclosure gaps become **Disclosure** steps (House Rule).
6. **Respect the sheet's limits:** at most 5 signals per driver as a guideline (drop context-only or stale signals first and list them; if a driver is still over, report it and suggest which to drop; the owners may keep more, as for GRAB D1 on 2026-11-08, and the app then shows an "over cap" tag), never a stock-level score, Share of price blank unless the file gives a share of *price* (a share of EBITDA or of value is not one).
7. **Compare colours.** Import the sheet into a throwaway local database (`worker/tests` setup, `app.today` = today), list each signal's app colour next to the file's, and explain every difference in the report (the app rule wins; usually the file's yellow reflects a trend or judgment, not a line).
8. **Feeds:** say which signals an existing feed can read (US 10-Q/10-K XBRL) and which need the agents or hand entry (6-K releases have no XBRL).

## Mapping from the bundle's dashboard to the sheet

| Bundle concept | Sheet |
|---|---|
| Driver, type, share of price, dependency | Drivers A–I, N, O, P |
| Indicator, source, cadence | Signals C, D, F |
| Evidence grade | Signals E (Tier A/B/C) |
| ⭐ binding constraint / KS kill switch / anchor | Signals N / O / P |
| Methodology trap, definition change | Signals M / L |
| 🟡 base-case threshold | Base case value (Consensus scored; Thesis scored when no Consensus) |
| 🔴 threshold | Signals I tolerance = distance from base to red, as a fraction |
| ⚪ no data (first cycle) | Scoring log row left out, or value blank → GREY |
| Withheld on a natural occasion → 🔴 | Scoring log P = Y → RED; Event ladder Disclosure step Failed |
| Falsification test, thesis-breaker, catalyst | Event ladder, Kind column |
| Reading (date, grade) | Scoring log |
| Rating, fair value, scenarios, probabilities, zones, thesis colour | Not in the sheet (Hard rule 1) |
