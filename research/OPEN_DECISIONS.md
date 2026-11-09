# Open decisions and reminders

Things the owners (Thao, Duong) need to come back to. Each has Claude's suggestion; nothing here is decided until you tick it and say so. Newest first.

## Before the NVDA sheet can show colours

Decisions 1-3 were taken on 2026-11-07. They may change as we use them; each entry says where it lives and how to reverse it, and the change log in `docs/STATUS.html` has the dated line.

- [x] **1. Where consensus comes from (Source R8).** *Decided 2026-11-07 (owners took the suggestion).* Each quarter, type in the consensus quoted in news coverage of the results (e.g. "analysts expected $X, according to LSEG") as a Consensus row, with the article in the Source log (Tier C, Redistribute = No). The app shows the colour and variance, never the consensus number (only reviewers see it on /review). First use: the NVDA refresh after 2026-11-17. Needs reuters.com or cnbc.com allowed in the environment's network settings if Claude is to fetch the articles; otherwise an owner pastes the figure and link. *Where it lives:* `.claude/skills/driver-sheet-builder/SKILL.md` (Base case section). *To change:* edit that section; no code change.
- [x] **2. Signals that have no consensus at all** (S2 TSMC monthly YoY, S7 inventory, S8 DSO, S9 supply commitments, S1 capex). *Decided 2026-11-07 (owners took the suggestion).* A reading with no Consensus row for its version and period is scored against the Thesis row (our own estimate) and the app labels it "vs our estimate". Consensus always wins when both exist; Management rows stay reference only. These signals stay GREY until Thesis rows are added (the thesis session, decision 5). *Where it lives:* `app.scoring_base()` in `supabase/migrations/20261107000100_thesis_fallback.sql`, and the Scoring log formula (column F, plus a new "Scored against" column Q) in `templates/build_templates.py`; the golden test keeps both in step. *To reverse:* a new migration making `app.scoring_base()` return Consensus only, and the old column F formula.
- [x] **3. S5 gross margin tolerance.** *Decided 2026-11-07 (owners took the suggestion).* 2% -> 0.7% of base (about 0.5 points on a 74% margin), so YELLOW = inside NVIDIA's guided band and RED = below it. This also recolours past S5 readings. *Where it lives:* `research/NVDA/driver_spec.json` / the NVDA sheet (Signals, Tolerance), and a one-row update in the same migration. *To change:* edit the sheet and re-import, or update `signals.tolerance`.
- [x] ~~4. Keep S4 (non-hyperscale demand)?~~ Resolved 2026-11-05: NVIDIA discloses the "AI Clouds, Industrial & Enterprise" split, so S4 stays (with a definition-change flag for the recasts).

## NVDA base case draft (2026-11-09)

- [ ] **12. Approve the NVDA base case draft, then re-import.** 19 new v1 rows (18 Thesis, 1 Management), all anchored to SEC filings; table and colours in `research/NVDA/research_notes.md` ("Base case draft"). Result: S1, S2, S4, S5 green; S7 yellow; S8 (DSO) and S9 (supply commitments) red. **Base case rows cannot be changed after import** (only replaced by a v2), so approve or edit first. Then: Terminal guide C2 (`python -m worker.import_xlsx inputs/NVDA_driver_sheet.xlsx --dry-run`, then without `--dry-run`).
- [ ] **13. Gross-margin consensus (decision 1) still missing.** cnbc.com and reuters.com are blocked here. *Suggestion:* after Nov 17, paste the article link and the quoted figure in chat, or allow those sites in the environment's network settings so Claude can read them.

## GRAB driver sheet (draft 2026-11-08, from the owners' Nov 7 base case file)

Draft: `inputs/GRAB_driver_sheet.xlsx`; notes and checks: `research/GRAB/research_notes.md`. Nothing is imported until the owners say so.

- [ ] **7. Review and import the GRAB sheet.** *Suggestion:* read section 4 of the research notes (colour differences), then `python -m worker.import_xlsx inputs/GRAB_driver_sheet.xlsx --dry-run` and, if clean, the same without `--dry-run`.
- [x] **8. D1 has 6 signals (cap 5).** *Decided 2026-11-08:* keep all six. The cap of 5 is a guideline; the owners may keep more on a driver when each signal earns its place. The app shows an "over cap" tag on GRAB D1 and the import prints a warning; both are expected. *Precedent for future tickers:* report the overflow, suggest which to drop, and keep them all if the owners say so.
- [ ] **9. GMV thesis-break line: 15% or 12%?** *Interim 2026-11-08:* 15% for now (S3 tolerance 0.25). **Owner: Duong** to confirm or change. To change: S3 tolerance in the GRAB sheet (12% would be 0.40) and the S3 thesis-breaker step, then re-import.
- [x] **10. Tolerances proposed by Claude** (S1 5%, S2 3%, S4 5%, S6 35%, S9 red below -$20M, S11 10%). *Decided 2026-11-08:* accepted as proposed. Each is anchored in the sheet's Threshold anchor column. *Precedent:* where an owners' file gives no red line, Claude proposes one anchored to the metric's history or guidance range and the owners accept or change it.
- [x] **11. S5 mobility revenue growth had no base case.** *Decided 2026-11-08:* a Thesis row at the owners' 8% alert line (tolerance 0: green at or above 8%, red below). Q3 2026 (+10%) shows green; the file showed yellow because of the slowdown, which the arrow (Decelerating) still shows.

## Charts

- [ ] **6. A share-price source for valuation history** (P/E, EV/Sales over time). SEC filings have no prices, and
  Sharadar may not be shown on a hosted site.
  *Research 2026-11-07* (from search results; the vendors' pages could not be opened from this environment, so
  re-read the clauses before deciding): no mainstream free tier clearly allows showing data, or values derived from
  it, to other people. Every free tier is "personal" or "internal" use. Polygon (now Massive) says derived figures shown
  to others need its Business plan (about $2,499/month). Financial Modeling Prep and EODHD need custom display
  agreements. Stooq and Yahoo (yfinance) have no usable licence and break often. IEX Cloud shut down in 2024.
  *Shortlist:*
  1. **Tiingo** (official API, deep history; free tier is enough for one daily call). Its terms say data is for
     internal and personal use and that showing it on "a website or app" needs permission from sales. *Suggestion:*
     email Tiingo describing the site (invite-only, a few users, no fees, only P/E and EV/Sales shown) and ask for a
     written OK or a quote. https://api.tiingo.com/documentation/general
  2. **Marketstack Basic** (about $9.99/month), reported to be the cheapest plan allowing commercial use; display
     rights are not stated, so confirm in writing first. https://marketstack.com/pricing
  3. **Alpha Vantage free** (official API, 25 calls a day). Personal, non-commercial use only; showing data to others
     is reportedly treated as commercial. Ask before relying on it. https://www.alphavantage.co/terms_of_service/
  Until one is agreed, the charts show revenue and margins only.
  *Asked 2026-11-08: could an agent read prices from Yahoo Finance?* Technically yes, but Yahoo's terms forbid
  automated collection and showing its data to others, the unofficial libraries (yfinance) say "personal use only"
  and break often, and a scraped source cannot be relied on for a daily job. Not recommended for the site. The same
  applies to stockanalysis.com (R9 in the GRAB file).

## Thesis work

- [ ] **5. Share of price per driver** (Drivers column O) is blank.
  *Suggestion:* run a thesis-discussion session on NVDA with Duong after the Q3 FY27 print, using `thesis-research-bundle/skills/thesis-discussion-loop`. It fills share of price and the Thesis base case rows.

## Dated reminders

- [ ] **2026-11-17, NVIDIA Q3 FY27 results.** Refresh the sheet ("Refresh NVDA driver sheet"): add the Q3 readings, score the falsification test on gross margin (guide 73.5%–74.5%), and check the Rubin disclosure step. If no Rubin figure is given, mark the step Failed and add a Withheld row for S3 (RED, per House Rule). Add base case v2 after the print.
- [ ] **Around 2026-11-10, TSMC October revenue** (S2).

## Project

- [x] ~~Merge into `main`~~ Done 2026-11-05 (pull request #1); template v2 live on Supabase.
- [ ] Re-export the game plan Google Doc (the Claude doc has newer changes).
- [x] ~~Google Docs connector~~ Not allowed by the organization; the status doc is published as numbered versions (v-0, v-1, ...) instead. Delete old versions by hand.
