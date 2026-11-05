# Open decisions and reminders

Things the owners (Thao, Duong) need to come back to. Each has Claude's suggestion; nothing here is decided until you tick it and say so. Newest first.

## Before the NVDA sheet can show colours

- [ ] **1. Where consensus comes from (Source R8).** Colours are scored only against Consensus rows, and none exist yet, so every NVDA reading is GREY.
  *Suggestion:* each quarter, take the consensus quoted in news coverage of the results (e.g. "analysts expected $X, according to LSEG") and type it in as a Consensus row, with the article as the source and Redistribute = No. In the app (M2), show the colour and variance but not the raw consensus number. Needs one of reuters.com or cnbc.com allowed in the environment's network settings if Claude is to fetch it.
- [ ] **2. Signals that have no consensus at all:** S2 TSMC monthly YoY, S7 inventory, S8 DSO, S9 supply commitments (and S1 capex, where companies give only annual guidance).
  *Suggestion:* allow an owner-approved **Thesis** row to be scored when no Consensus row exists for that signal and period, and label it "vs our estimate" in the app. This is a small rule change in the database view and the spreadsheet formula; until then these signals stay GREY.
- [ ] **3. S5 gross margin tolerance.** It is 2% of base (about 1.5 points), wider than NVIDIA's guided band of ±0.5 points.
  *Suggestion:* 0.7%, so YELLOW = inside the guidance band, RED = below it.
- [x] ~~4. Keep S4 (non-hyperscale demand)?~~ Resolved 2026-11-05: NVIDIA discloses the "AI Clouds, Industrial & Enterprise" split, so S4 stays (with a definition-change flag for the recasts).

## Charts

- [ ] **6. A share-price source for valuation history** (P/E, EV/Sales over time). SEC filings have no prices, and
  Sharadar may not be shown on a hosted site.
  *Suggestion:* a free end-of-day price source whose terms allow showing derived ratios on an invite-only site
  (check the terms first), loaded daily; until then the charts show revenue and margins only.

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
