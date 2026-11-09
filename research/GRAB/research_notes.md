# GRAB research notes (driver sheet v1, 2026-11-08)

**Input:** the owners' base case and dashboard file, `GRAB_Base_Case_and_Dashboard.md` (last updated Nov 7 2026,
kept in this folder as the record). **Output:** `driver_spec.json` → `inputs/GRAB_driver_sheet.xlsx`, a draft for the
owners to review before import. Method: `.claude/skills/driver-sheet-builder/SKILL.md`, section "Starting from an
owners' base case file".

## 1. What was checked against SEC filings (opened 2026-11-08)

Grab files its quarterly results as 6-K press releases (Exhibit 99.1), without XBRL tags. Six releases were opened
(R1, R11-R15) and every quarterly figure in the sheet comes from them.

| Item | Owners' file | 6-K | Result |
|---|---|---|---|
| Q3 2026 revenue / adj. EBITDA / margin | $1,112M / $237M / 21.3% | same | Matches |
| On-demand GMV growth, Q3 2026 | 22% CC, 18% reported | same | Matches |
| Mobility margin (segment EBITDA ÷ GMV) | 8.9% | $207M ÷ $2,335M = 8.87% | Matches (computed; not stated in the release) |
| Deliveries margin | 2.7% | 2.7% (stated) | Matches |
| Mobility revenue growth | +10% (+12% CC) | same | Matches |
| FS segment adj. EBITDA | +$12M; Q3 2025 -$28M | same | Matches |
| NPLs / reserve cover / gross loan book / deposits | 2.6% / 2.4x / $2.7B / $2.7B | same | Matches |
| Net cash liquidity | $5.0B (Sep 30), gross $7.1B | same | Matches |
| Buybacks | $174M in Q3; $400M Sep-Oct; $500M left | same (cash flow statement and text) | Matches |
| TTM adj. free cash flow | Q1 489, Q2 450, Q3 533 | same | Matches |
| **Q4 2025 adj. EBITDA** | ~$149M [VERIFY] | **$148M** | Corrected |
| Q4 2025 revenue | ~$906M [VERIFY] | $906M | Confirmed |
| **"Net cash $5.4B (May 19)"** [VERIFY] | | $5.4B was at Dec 31 2025 and again at Jun 30 2026; $5.0B at Mar 31 2026 | Replaced by quarter-end figures |
| Q2 2026 mobility growth, margins (not retained) | – | mobility revenue +12%; mobility margin 8.63%; deliveries 2.3% | Filled in |
| Q4 2025 FS EBITDA (not retained) | – | -$25M (Q1 2025: -$30M) | Filled in |
| **Loan book history** | ~$2.3B earlier point, date approximate | $2.318B at Jun 30 2026; $1.438B at Mar 31 2026 | Filled in. **Definition change:** from Q1 2026 the release reports "Gross loan portfolio" (Q3 2025 restated $821M → $903M), so the series starts at Q1 2026 (House Rule) |
| **Advertising +44% (Q1 2026)** | "Advertising growth" | 44% is the growth in *average spend of self-serve advertisers*, not ad revenue | Signal S8 left out (see 3) |
| **Adjusted FCF definition** | – | From Q2 2026 it excludes net changes in FS treasury liquidity | Definition change noted on S20 |

Not checked (not in the 6-Ks): FY26 guidance and the 2028 target (call, R2), consensus (R10), Indonesia macro
(R4-R6), Vietnam share (R7), insider buys (R8).

## 2. How the owners' base case maps to the sheet

| Owners' file | Sheet |
|---|---|
| `base_type: consensus` (S1 $193M, S2 $1,080M for Q3 2026) | Consensus rows, source R10 (Tier C, Redistribute = No, decision 1). The app shows colour and variance only |
| Guide-implied figures (S2 ~$1,050M before the print; Q4 2026 $231-241M and $1,086-1,136M) | Management rows (reference). For Q4 2026 also Thesis rows at the midpoint, because the owners use them as the next-print base case |
| `base_type: our estimate` with a green line (≥20%, ≥8.5%, ≥$150M, ...) | Thesis row = the green line, for Q3 2026 and Q4 2026 |
| A red / breach / thesis-break line | Tolerance = distance from the base to that line, as a fraction |
| A breach line only (NPL 4%, net cash floor $2.0B) | Thesis row = that line; tolerance as stated or 0 |
| `base_type: none` | No base case row (GREY); any alert line goes in Threshold anchor |
| Non-numeric signals (fee cap, MSCI, ratings, Atome, flows) | Polarity "Event ladder"; breach conditions as Thesis breaker steps (Failed = happened, RED), dated events as Catalysts |
| Thesis-break table (1.4) | Thesis breaker steps on S3, S9, S14, S18, S27, S28; S13 Disclosure step |
| Catalyst table (1.6) | Catalyst / Milestone steps (S1, S14, S16, S19, S22, S27) |
| History arrays | Scoring log rows, re-sourced to the 6-Ks; only Q3 2026 (and Q4 2026 macro readings) have a base, so older rows show GREY |

**Left out on purpose** (hard rules of the app): price, market cap, EV and multiples; the rating and conviction; fair
value, scenarios and probabilities; Street price targets; the 2028 bridge per-share values; driver roll-up scores and
the thesis colour; "share of value" percentages (they are shares of the 2028 EBITDA lift, not of the price; Share of
price stays blank until decision 5). They remain in the owners' file only.

## 3. Signals: kept, dropped, changed

- **Kept 26 of 28.** Dropped **S7 MTUs** (context only, no threshold; 57.2M in Q3 2026) and **S8 Advertising** (stale,
  and the 44% figure is advertiser spend, not ad revenue). D1 still has 6 signals (cap 5): owners to drop one (below).
- **S21 insider buying:** the owners' notes cite Form 4, but Grab is a foreign private issuer and its insiders do not
  usually file Form 4. Kept as a GREY reading with a [VERIFY]; source R8 has no link.
- **S15 Vietnam share:** stale (Dec 2025) and conflicting (Mordor vs Rakuten); kept GREY.

## 4. Colours: app vs owners' file (app rule wins, per the earlier owner decision)

| Signal | Owners' file | App | Why |
|---|---|---|---|
| S1-S4, S6, S9-S12, S15-S23, S25 | as in the file | same | |
| S5 mobility revenue growth | 🟡 | GREY | The file says "no base case"; the yellow comes from the slowdown. Add a Thesis row (e.g. 8% alert line) to score it |
| S14 Indonesia fee cap | 🟡 | Event steps pending | The watch comes from the new delivery guidelines; no step has happened yet |
| S24 USD/IDR | 🟡 | GREEN | 18,143 is inside the owners' base range (17,500-18,500); the yellow reflects the trend |
| S26 flows | 🔴 | Thesis breaker step RED | Same meaning, shown on the milestones list |
| S27 MSCI, S28 rating | 🟡 | Event steps pending | Nothing has happened yet; the dates are on the ladder |

## 5. Owner decisions (2026-11-08)

- D1 keeps all six signals (S1-S6), one over the usual cap; the app's "over cap" tag on D1 is expected.
- S3 GMV thesis-break line: 15% for now; Duong to confirm or change (12% would be tolerance 0.40).
- Claude's proposed tolerances accepted: S1 5%, S2 3%, S4 5%, S6 35%, S9 red below -$20M, S11 10%.
- Still open: a base case for S5 (decision 11).

## 6. Gaps

- No URLs for R4-R8 (macro dashboard, Mordor, insider filings).
- Q4 2025 buybacks not checked; S19 has no Q4 2025 row.
- Consensus for Q4 2026 not available; the next print uses the guide-implied Thesis rows until one is typed in.
- Price history (R9) not used: valuation history waits on decision 6.
- No data feed for GRAB yet: 6-Ks have no XBRL, so S1-S20 need the AI agents (M5) or hand entry on /review.
- Charts (M4b) stay empty for GRAB: they read US-GAAP XBRL from 10-Q filings, which Grab does not file.
