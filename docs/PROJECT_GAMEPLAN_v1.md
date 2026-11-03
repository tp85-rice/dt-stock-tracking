# AI Stock Driver Tracker: Evaluation, Game Plan and Hand-off

Exported 2026-10-21 from the working session. Source draft: `project-1.md` (exported 2026-10-14).
Nothing in this file has been run in Excel or deployed. Per-ticker facts in `project-1.md` were not re-verified here.

---

## 1. What the product is

A web app where the user enters a ticker and gets:

1. A map of the key growth drivers that could rerate the stock over 1-5 years.
2. A dashboard of signals per driver, coloured against a base case, with a momentum arrow.
3. Financial charts (segment revenue, margins, valuation history).

Hard rules: no price targets, no buy/sell language. The app only reports whether each signal is ahead of or behind a base case, and its momentum.

---

## 2. Evaluation of the draft (summary)

**Strong:** no advice language; the LLM explains alerts but rules and statistics decide whether they fire; per-driver polarity; versioned base cases; definition-change flags; event ladders; grey for missing or stale data; manual-first on 11 names.

**Weak:**

1. Nothing tests whether the signals lead anything. The central claim is never tested.
2. The user (retail, analyst or fund) is undefined. It drives legal posture, data licensing and pricing.
3. The 11-name universe is narrative-heavy (TSLA, COIN, RKLB, MRNA, KTOS). It is not a fair rigor test.
4. Most hard signals are quarterly, so there is little to alert on between earnings.
5. The first deliverable is a spreadsheet, so 5-10 days pass before learning whether anyone wants it.
6. Source quality is mixed. Several are AI-summary aggregators. Treat them as leads and re-source every number to the SEC filing or press release.
7. The vizualstocks-style charts are underspecified.

### Suggested changes to the plan

1. Run a backtest harness and 5-8 user interviews before the 11-name spreadsheets (about a week).
2. Pilot a mixed set: NVDA and AMZN or GOOG (clean hard signals), SE (strong disclosure), one template-breaker (MRNA). Keep TSLA as a demo only, not as a rigor test.
3. Decide the user and the refresh cadence now. Daily with delayed data is cheaper and safer than real-time.
4. Ship the financial charts first. They work for any ticker and bring users in while curated driver pages grow.
5. Define a kill criterion up front. Example: if no tested signal beats a naive baseline, reposition as a research-organization tool, not an alerting tool.

---

## 3. Additional resources recommended

1. **Sharadar bundle (already in the workspace):** prices, fundamentals, insider trades, corporate actions, news, SEC text. Query via the finance-data skill. See the read-only rule in section 8.
2. **Backtest harness in Python:** test 2-3 signal types with long, clean history (hyperscaler capex vs NVDA revenue, TSMC monthly revenue, short interest, insider buying, estimate revisions). Use point-in-time data and control for lookahead and survivorship bias.
3. **Existing skills:** `two-stage-dcf` / `dcf` for quantified base-case paths; `dataviz` and `frontend-design` before dashboard work; `web-app` for the server rules; `claude-api` for the LLM layer.
4. **User research:** mock up an NVDA driver dashboard and show it to 5-8 target users. Ask what they would check weekly and what they would pay for.
5. **Free primary sources:** SEC EDGAR full-text search and XBRL `companyfacts`; FRED; USAspending, SAM.gov and DSCA; TSMC monthly revenue; NHTSA and FCC filings; on-chain USDC supply.
6. **LLM evaluation:** a hand-labeled gold set (20-30 cases) and a scoring sheet, to measure hallucination and citation accuracy.
7. **Legal review before any public launch:** a securities attorney or clinic, on whether "positivity and momentum alerts" are advisory, and on data redistribution terms.
8. **Paid transcripts (Quartr or similar):** only if the pilot shows Q&A clustering adds value.

---

## 4. Files delivered so far (in `/home/tp85/workspace/app2/`)

| File | What it is |
|---|---|
| `project-1.md` | Your original draft |
| `stock_driver_template.xlsx` | Per-ticker driver sheet. One copy per ticker |
| `llm_eval_scorecard.xlsx` | LLM extraction scorecard (gold set, runs, summary) |
| `build_templates.py` | Regenerates both workbooks if you want to change the layout |
| `PROJECT_GAMEPLAN.md` | This file |

**Caveat:** LibreOffice is not installed on this machine, so the formulas in both workbooks have never been evaluated. I checked the colour rules by hand against sample values (a 5% miss, a 20% miss, stale data, blank tolerance) and they gave the expected results. Open both files in Excel once and enter a test row to confirm.

### 4.1 `stock_driver_template.xlsx` (the five-tab sheet, plus an event ladder)

Yellow cells are for you to type in. Grey cells are formulas. Do not overwrite them.

| Tab | Purpose |
|---|---|
| README | Ticker, order of work, how colours are decided |
| Drivers | One row per driver. Counts its signals and flags "narrative-only" (no Tier A/B signal) or "over cap (5)" |
| Signals | Tier, cadence, unit, polarity, tolerance band, max staleness in days, definition-change note |
| Base case | Versioned, dated values by signal and period. Colours are scored against the Consensus rows. Management rows are a reference line only |
| Event ladder | Ordered milestones with target dates and a status. Colours come from status and days late |
| Source log | URL, access method, cost, terms-of-service note, redistribution flag |
| Scoring log | **Where you score.** See below |

**Scoring log: what you type and what fills in**

- You type: date observed, Signal ID, observed value, base case version, period, momentum arrow, source ID.
- Filled in: base case value, variance, polarity, tolerance, max staleness, data status, colour.

**How colour is decided**

- Variance = (observed − base) ÷ |base|.
- Higher is better: GREEN at or above base; YELLOW within the tolerance band below; RED beyond.
- Lower is better: the same rule, flipped.
- GREY: value missing, observation older than the signal's max staleness, or no matching base case row. The Data status column says which. Grey never means "in line".
- Green means ahead of the base case, not "the stock goes up".

**Order of work:** Drivers (D1, D2, ...) → Signals (S1, S2, ..., max 5 per driver, at least one Tier A or B) → Base case → Event ladder → Source log → Scoring log.

### 4.2 `llm_eval_scorecard.xlsx`

| Tab | Purpose |
|---|---|
| README | How to score and how to build the gold set |
| Summary | Pass rates by prompt/model version and by task type. Targets are editable |
| Gold set | You enter a verbatim passage, the task, and the correct answer **before** running the model |
| Runs | **Where you score.** One row per case per prompt/model version |

Score each run 1 or 0 on: value correct, event/type correct, citation valid, hallucination, schema valid.

Default pass targets: value correct at least 90%, citation valid at least 95%, hallucination at most 2%, schema valid at least 99%.

Rules for the gold set:

- 20-30 cases, at least 20% hard (restated numbers, definition changes, negations, no-answer passages).
- At least 4 cases per task type, across 5 or more tickers and 3 or more document types.
- Never edit gold labels after seeing model output. Add new cases instead.
- Prefer passages dated after the model's knowledge cutoff.
- Have a second person score about 20% of rows blind.

---

## 5. Game plan

### Phase 0: Settle decisions (days 1-2)

| Decision | Default if undecided |
|---|---|
| Who is the user? | Personal / internal only |
| Base case definition | Consensus-anchored, management case as a reference line |
| Refresh cadence | Daily, delayed data |
| Sharadar licence: may any derived data be hosted publicly? | No. Hosted version uses free sources only |
| FastAPI or Next.js for hosting | FastAPI (same code runs in the lab and on Vercel) |
| Pilot names | NVDA, AMZN or GOOG, SE, MRNA. TSLA as demo only |

### Phase 1: Validate the idea (week 1)

1. Open both templates in Excel and enter test rows to confirm the formulas.
2. Check what the Sharadar bundle actually contains (read-only SELECTs, CSV into `data/`).
3. Build the backtest harness for 2-3 signal types. Record whether any lead a naive baseline.
4. Show an NVDA mock-up to 5-8 target users.
5. **Go / no-go.** Apply the kill criterion from section 2.

### Phase 2: Fill the sheets (weeks 1-3)

1. Fill one sheet per pilot name from the templates. Budget half a day to a day each the first time.
2. Re-source every number to a filing or press release.
3. Snapshot pre-earnings state as base case v1, then freeze each base case right after that company's Q3 print (most report late October to mid-November).
4. Fix the template after the first three, then batch the rest.
5. Build the 20-30 case gold set in parallel.

### Phase 3: Build the app in the lab (about 3-4 days)

Steps 0-9 of the build guide are in section 6. Run it in the lab's App tab first.

### Phase 4: Host it (about 1-2 days)

Move to Supabase Postgres and Vercel. See section 7. Do this only after the licensing question is answered.

### Phase 5: Only if Phases 1-4 hold up

1. Move the remaining names into the app.
2. Add free auto-fetch adapters, one source at a time: EDGAR `companyfacts`, FRED, USAspending, TSMC monthly revenue.
3. Add the LLM layer on the Claude API to propose drivers and events from filings. Score it with `llm_eval_scorecard.xlsx` before showing its output to anyone.
4. Consider alerts, only if the backtest supported them.

---

## 6. Web app build guide (lab version)

**Layout**

```
webapp/
  app.py            # FastAPI routes
  scoring.py        # colour rules (pure functions)
  db.py             # database access
  import_xlsx.py    # sheet -> database
  data/             # CSVs from Sharadar, plus the local database
  static/           # app.js, style.css, chart library (saved locally)
  templates/        # index.html, ticker.html
  tests/test_scoring.py
```

**Steps**

0. **Set up.** Create `app2/webapp/`. Check `fastapi`, `uvicorn`, `pandas`, `openpyxl`, `duckdb` import (I could not complete this check). Run with `uvicorn app:app --host 0.0.0.0 --port 8000`. Restart with `kill $(lsof -t -i:8000)` first. This is the command `CLAUDE.md` requires.
1. **Layout** as above.
2. **Database.** One table per spreadsheet tab plus a `ticker` column: `drivers`, `signals`, `base_case`, `event_ladder`, `sources`, `scores`. Put the colour rules in `scoring.py` and compute colour when the page loads, not at write time. A changed tolerance then re-colours old observations.
3. **Import.** `import_xlsx.py` reads only the yellow input cells with openpyxl. The grey formula cells have no cached values. Keep filling in Excel until the in-app forms replace it.
4. **Market data.** Use the finance-data skill, SELECT-only, save CSVs to `webapp/data/`. The app reads CSVs and never connects to `md:ndl`. Show EV/Sales instead of P/E when earnings are negative, and label which. Type segment revenue by hand for the pilot names. Refresh with a script you run yourself.
5. **Routes**

| Route | Purpose |
|---|---|
| `GET /` | Ticker box and list of covered tickers |
| `GET /t/{ticker}` | Ticker page |
| `GET /api/{ticker}/drivers` | Drivers, signals, latest colour and arrow |
| `GET /api/{ticker}/financials` | Chart series |
| `POST /api/{ticker}/scores` | Add an observation |
| `POST /api/{ticker}/basecase` | Add a new base case version |
| `GET /api/{ticker}/signals/{id}/history` | Observation history for a sparkline |

   An uncovered ticker still gets the financial charts and a "no driver map yet" note. Keep each request well under the 60-second proxy limit.

6. **Frontend.** Plain HTML and JavaScript, one chart library saved under `static/`. **Use relative URLs only** (`fetch("api/NVDA/drivers")`, never `fetch("/api/...")`). Page order: header with ticker and base case version/date; driver cards with colour, arrow and "narrative-only" flag; "last updated" age on every signal; financial charts; collapsible source log. Include the explainer: "Green means ahead of the base case, not that the stock goes up." Load `frontend-design` and `dataviz` before styling.
7. **Test.** Unit-test `scoring.py` for higher/lower polarity, tolerance boundary, blank tolerance, stale, missing, no base case, zero base case. Put the same hand-worked rows in the Excel scoring log and the app. If colours differ, fix it before trusting either.
8. **Personal-use basics.** Single user, no login in the lab. Back up the database by copying the file. Keep the no-advice rule in the code (no "buy", "sell" or "target" text) with a fixed footer saying the app measures signals against a base case and is not investment advice.
9. **Demo script (5 minutes).** Open NVDA and show real colours; add an observation and show a colour flip; show a grey signal and explain why grey is not green; show an event-ladder name with a slipped milestone (MRNA or RKLB); show an uncovered ticker with only charts.

---

## 7. Hosting on Vercel with Supabase

### Two issues to settle first

1. **Sharadar data cannot go on a public site.** `md:ndl` is licensed to the course. Copying its prices or fundamentals into Supabase and serving them from Vercel is redistribution, which licences like this normally prohibit. Check the licence terms or ask your instructor. Until then, put only publishable data in Supabase: SEC EDGAR `companyfacts`, FRED, and your own hand-entered drivers, signals and base cases. Or keep Sharadar-derived charts in the lab version only. Either way, put a login in front of the whole site.
2. **Never put the `md:ndl` token in Vercel or Supabase settings.** That token can write, and the only protection for the shared database is that nobody does.

SQLite does not work on Vercel (no persistent disk), so the database moves to Supabase Postgres.

### What changes from the lab version

| Lab | Hosted |
|---|---|
| SQLite file | Supabase Postgres |
| Colours computed in `scoring.py` on request | A Postgres view mirroring the spreadsheet formulas, plus the same unit tests |
| Chart data from CSVs | Chart data in Supabase tables, loaded by a local script |
| No login | Supabase Auth, limited to your email |
| `uvicorn app:app --port 8000` | The platform runs it |

### A to Z

- **A. Accounts:** Supabase, Vercel, GitHub.
- **B. Supabase project:** create it, run a `schema.sql` (tables above plus `financials`), then add a `v_scores` view that joins each score to its signal rules and the consensus base case and computes variance, data status and colour.
- **C. Database security:** turn on Row Level Security on every table; allow reads and writes only for your authenticated user; keep the service-role key on the server only. The anon key is public by design, so RLS is the real protection.
- **D. Login:** Supabase Auth with email magic link, public sign-ups disabled. The backend checks the token on every API call.
- **E. Local import:** `import_xlsx.py` upserts the yellow input cells into Supabase. Keep connection details in a git-ignored `.env`.
- **F. Financial data loader:** `refresh_data.py` pulls from the allowed sources (EDGAR and FRED to start) into `financials`. Run it by hand.
- **G. App changes:** use the Supabase **transaction pooler** connection string, keep all frontend URLs relative, keep server dependencies small (no pandas).
- **H. Vercel config:** `requirements.txt`, point Vercel at the FastAPI app, static files where Vercel serves them.
- **I. GitHub:** push with `.env` excluded. Check `git status` before the first commit.
- **J. Deploy:** import the repo in Vercel, add the environment variables (database URL, Supabase URL, anon key, service key) in its settings, deploy, and check login and one ticker page.
- **K. Smoke test:** repeat the demo script on the live site; compare hand-worked rows against the view's output.
- **L. Keep it alive:** Supabase's free plan pauses a project after about a week of inactivity. Check the site is awake before a demo, or add a small scheduled ping.
- **M. Limits:** from what I last knew, the free plan has a small database limit (around 500 MB) and Vercel Hobby is for non-commercial use. Check the current pricing pages.

I can prepare the repo, `schema.sql`, the import script and the Vercel config here, and test locally. You create the accounts and paste the keys yourself. I do not know whether this lab's network can reach Supabase, so that gets tested first.

---

## 8. Rules that apply throughout

- **Sharadar is read-only.** SELECT only against `md:ndl`. Never DROP, DELETE, INSERT, UPDATE, CREATE, ALTER, TRUNCATE, REPLACE or `COPY ... TO`. Save results to CSV under `data/` and transform them there. The database is shared by the whole class.
- **No advice.** No price targets, no buy/sell wording anywhere.
- **Definition changes.** When a company redefines a metric (for example Alphabet's backlog), note it in Signals and start a new Signal ID or base case version at the break. Do not splice the series.
- **Never overwrite old base case versions.** Add a new version after each earnings call.
- **No secrets in the repo.** Keys live in `.env` and in Vercel's settings.

---

## 9. Files you will provide next

Put them under `app2/inputs/` so everything is in one place.

| File | Contents | Needed by |
|---|---|---|
| `NVDA_driver_sheet.xlsx` | Copy of `stock_driver_template.xlsx`, filled in | Phase 2; app import |
| `AMZN_driver_sheet.xlsx` or `GOOG_driver_sheet.xlsx` | Same | Phase 2 |
| `SE_driver_sheet.xlsx` | Same | Phase 2 |
| `MRNA_driver_sheet.xlsx` | Same, with event-ladder signals | Phase 2 |
| `TSLA_driver_sheet.xlsx` | Same, demo only | Phase 2, after the Oct 21 call |
| `llm_eval_scorecard.xlsx` | Gold set filled in (20-30 cases) | Phase 5 LLM work |
| `segments.csv` (or a tab in each sheet) | Hand-typed segment revenue for the pilot names | App charts |
| `decisions.md` | Your answers to the Phase 0 table, including the Sharadar licence answer | Before Phase 3 |
| `vizualstocks_charts.md` | The chart types you want replicated (the draft says the pages were not opened) | App charts |

Files stay in your hands (do not paste them into chat):

- Supabase URL, anon key, service-role key and database URL: put in `.env` and Vercel settings only.
- The `md:ndl` token: stays where it is.

After each file arrives, the next step on my side is:

1. Check that the sheet follows the template.
2. Validate that every Signal ID, Driver ID and Source ID resolves.
3. Run the import.
4. Compare the app's colours with the sheet's.

---

## 10. Open questions and unverified items

- Who is the user: retail, analysts or funds? (Open question #1 in the draft.)
- Sharadar licence: does it allow any hosted, derived data?
- Real-time or daily refresh, and qualitative direction only or numeric forecasts?
- Any ticker or a curated universe at launch?
- Budget for licensed data (transcripts, alt data, app intelligence for DUOL)?
- From `project-1.md`: Indonesia's 8% commission cap rests on one source; GRAB-GoTo status is unclear; the Kratos Valkyrie ramp date conflicts across sources; Intismeran readout timing is management guidance only; the X API read cap differs between sources; all driver lists need re-checking against the Q3 calls; the legal posture has not been reviewed by counsel.
- Not done in this session: opening the templates in Excel, checking installed Python packages, checking what the Sharadar bundle contains, any deployment.
