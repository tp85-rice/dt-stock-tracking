---
name: "thesis-driver-dashboard"
description: "Build or refresh a stock's driver dashboard: key drivers, leading indicators with thresholds, bull/base/bear cases, and green/yellow/red roll-ups refreshed biweekly."
---

# Thesis Driver Dashboard

Turns an investment discussion thread into a monitoring system: what actually drives the stock over 1–3 years, which observable indicators lead those drivers, what each indicator must show for the bull, base or bear case, and a color roll-up that tells the owner in one glance whether the thesis is on track. Modeled on the TSLA Moonshot Dashboard (Optimus / Robotaxi / FSD / Merger tracks).

**Scope: the stock, not the owner's position.** The dashboard measures whether the thesis is on track. It does not contain, use or depend on holdings, cost basis, tax lots, entry or exit plans, sizing or options. If the thread contains any of that, leave it out entirely. The dashboard must be safe to publish on a page as is.

## Two modes

- **BUILD** — triggered by "Build dashboard for [TICKER]", "Dashboard [TICKER]", or a request to turn a thesis thread into a monitoring card. Produces the first full dashboard.
- **REFRESH** — triggered by "Update / Refresh [TICKER] dashboard" or a biweekly reminder. Re-reads the existing dashboard, pulls new data, re-colors, re-rolls-up, logs what moved.

If an existing dashboard exists in the project (`claude/[TICKER]_Dashboard.md`), REFRESH it rather than rebuilding. If project research instructions exist (e.g. Equity Research Master Instructions), read them first and stay consistent with their ratings vocabulary.

**Inputs, in priority order:** (1) `claude/[TICKER]_Thesis_State.md` if it exists — written by the thesis-discussion-loop skill, it is the source of truth for rating, conviction, scenarios, probabilities, thesis-breakers and the owner's judgment log; (2) `claude/House_Rules.md`, applied silently; (3) the discussion thread; (4) fresh web research. Do not re-derive what the state file already settles; if the dashboard work suggests the state file is wrong, say so and propose the change.

---

## BUILD procedure

### Step 1 — Mine the thread for drivers (1–3 year view)

Start from the state file if it exists. Then read the whole discussion thread for the ticker before searching anything. Extract:
- The thesis as the owner holds it about the business, and what the current price already implies (what's priced in).
- Every distinct source of value or risk discussed: core business economics, new businesses/options, balance sheet/capital allocation, competitive position, regulatory exposure, corporate events (M&A, spin, lockups).
- Armed thesis-breakers already set (dates and levels).

Then refresh current facts with web search: price, latest quarter, guidance, recent news. Anything describing the world now is looked up, never recalled.

Collapse into **3–6 key drivers**. A good driver is something that, if it went right or wrong, would move fair value by a meaningful amount within 1–3 years. Classify each:
- **Core** — the business that funds everything (TSLA: auto margin + cash flow).
- **Option** — not yet in earnings, carries a big share of the valuation (TSLA: Robotaxi, Optimus).
- **Mechanism** — an enabler several drivers depend on (TSLA: FSD reliability underlies both Robotaxi and Optimus). Name dependencies explicitly; a red mechanism caps every driver that sits on it.
- **Event** — a dated binary (TSLA: SpaceX merger, lockup expiry).

For each driver, estimate roughly what share of the current price it represents (sum-of-parts: value of what's provable vs. option value). This tells the owner where the price is most exposed.

### Step 2 — Break each driver into indicators

2–5 indicators per driver. Rules, learned from the TSLA build:

1. **Prefer leading over lagging.** Ask "what has to be true before this driver shows up in earnings?" TSLA lesson: cities announced, vehicles built and geofence maps were lagging vanity metrics; the gating metric was crash rate per mile and disengagement rate.
2. **Find the binding constraint.** Identify which single indicator actually gates the driver (the bottleneck), mark it ⭐ and weight it highest.
3. **Every indicator needs a public, repeatable source and a cadence** that fits a biweekly refresh: company filings/IR, regulator databases, government registries, industry trackers, community trackers, earnings calls. Record the source with the indicator.
4. **Label the evidence grade** of each reading: company-confirmed / third-party data / supply-chain report or rumor. A rumor never moves an indicator to green on its own.
5. **Watch for methodology traps** and note them next to the indicator: small samples after a new release, definitional changes (TSLA redefined FSD subscriptions), authorization vs. operation (registrations ≠ cars on the road), self-selected community data. Wait a minimum period after any new release before trusting a reading.
6. **Treat disclosure behavior as data.** If the company withholds a metric that peers publish, that is a signal. Rule: an indicator with no disclosure is ⚪ for one cycle; after the company passes on a natural chance to disclose (an earnings call, a launch event), it goes 🔴. (TSLA: four consecutive calls with no Optimus unit count = red.)
7. Include **one falsification test per driver** where possible: a dated, specific, checkable prediction (TSLA: "1,500+ Texas registrations by mid-October if the year-end claim is real").

### Step 3 — Scenarios, then thresholds

If the state file holds scenarios and probabilities, use them. Otherwise build **bear / base / bull** price cases over 12–18 months (and note the 3-year view):
- For each case state what each driver does, the valuation method (multiple, sum-of-parts, DCF shorthand), the price range, and a probability.
- Compute the **probability-weighted fair value** and compare to the current price. Say plainly whether the price is above, near or below it, and give valuation zones (attractive below $X, fair $Y–Z, stretched above $W) derived from the scenarios, not from anyone's cost basis.
- If there is a dated event (merger, approval), compute an event-weighted value separately (probability × deal value + (1 − p) × standalone).

Then set thresholds per indicator so the colors map to scenarios:
- 🟢 **Green** = tracking the bull case or the upper half of base.
- 🟡 **Yellow** = tracking base.
- 🔴 **Red** = tracking the bear case, or a kill condition hit.

Anchor every threshold to something external, never a round number picked from the air: a revealed industry benchmark (TSLA: Waymo removed safety drivers at ~30,000 city miles per critical disengagement), company guidance, a competitor's disclosed figure, the stock's own history, or the level at which the base-case valuation breaks. State the anchor next to the threshold.

Mark **kill-switch indicators** (KS): conditions that are red regardless of everything else (a fatal incident, a recall on the core technology, a covenant draw while cash flow is negative).

### Step 4 — Roll-up logic (indicator → driver → thesis)

Score indicators: 🟢 = 2, 🟡 = 1, 🔴 = 0, ⚪ (no data, first cycle) = excluded.

**Driver color:**
1. Any kill-switch indicator red → driver 🔴.
2. The ⭐ binding-constraint indicator red → driver cannot be better than 🟡.
3. Otherwise weighted average (⭐ indicator weight 2, others 1): ≥ 1.5 → 🟢; 0.75–1.49 → 🟡; < 0.75 → 🔴.
4. A red **mechanism** driver caps every driver that depends on it at 🟡.

**Thesis status:** weight drivers by their share of the current price (from Step 1). Same bands. Report it as a one-line verdict plus the count (e.g. "🟡 — 2 green, 2 yellow, 1 red; the red driver is 30% of the price").

Always show the arithmetic briefly so the owner can audit the color.

### Step 5 — Signals and watch-next

Translate colors into what they say about the thesis, not about any position:
- **Thesis status read:** intact (🟢), under review (🟡), or breaking (🔴), and which drivers carry that verdict.
- **Probability implications:** which color changes should move bear/base/bull probabilities and in which direction (e.g. "two Option drivers turning green shifts 10 points from base to bull"). In a session with the owner, propose the change to the state file; in an unattended run, record it as pending.
- **Armed thesis-breakers** with their resolution dates and status.
- **What would upgrade or downgrade the rating:** the specific color combinations or thresholds that would move the stance toward Buy or toward Sell, and the price-versus-fair-value condition that goes with them.
- **Watch-next list:** the next 3–5 dated events or data releases that will resolve the most uncertain indicators.

### Step 6 — Deliver

Write the dashboard as Markdown using the template below, including the machine summary (section 9). Save it to the project with `project_write` at `claude/[TICKER]_Dashboard.md`. If a state file exists, write back `drivers[].color`, `thesis_color` and `dashboard` in its YAML header (read → merge → write the full file). Send the dashboard file to the user, and offer (once) a biweekly calendar reminder whose description carries the refresh checklist.

---

## REFRESH procedure (biweekly)

1. `project_read` the existing dashboard and the state file if it exists. Note the last update date and every open watch-next item.
2. Search for what changed since that date: price, filings, earnings, guidance, regulator actions, registry/tracker data, competitor moves, analyst actions. Re-verify every number that drives a color; record source and date.
3. Update each indicator's reading and evidence grade. Apply thresholds mechanically. If a threshold now looks wrong because the world changed (new benchmark, company redefined the metric), change it explicitly and log why — never quietly.
4. Re-run the roll-up. Mark every color change with an arrow (⬆ / ⬇) and the prior color.
5. Re-check scenario probabilities and the weighted fair value; adjust only on evidence, and say what moved them. Probabilities, rating and conviction live in the state file: in a session with the owner, show the proposed change and update the state file; in an **unattended run** (scheduled task, nobody present), do not change them — write the proposal into the state file's Pending review section and set `review_status: draft-unreviewed`.
6. Write the **What moved** table (✅ positive / ⚠️ negative / ➖ unchanged / 🆕 structural) and a short honest read — including where price moved for reasons the indicators don't support.
7. Check falsification tests whose dates have passed: pass / fail / partial, with the number.
8. Update the signals section and calendar; carry forward any open watch-next item and flag it as overdue when it has slipped a cycle.
9. Append a dated line to the Change Log and update the machine summary. Save with `project_write` to the same path, write colors back to the state file header, and send the file.

Keep the reply short: price vs. valuation zones, thesis color and what changed it, the 2–4 color changes that matter, and what to watch next. The file holds the detail.

---

## Dashboard template

```markdown
# [TICKER] DRIVER DASHBOARD
**Last update:** [date] ([context, e.g. post-Q3]) | **Cadence:** biweekly | **Thesis status:** 🟢/🟡/🔴 | **Review:** reviewed / draft-unreviewed

## 0. Thesis snapshot
| | |
|---|---|
| Price | $X (date) vs. valuation zones |
| Rating / conviction | |
| Weighted fair value | $X (bear $a–b p% · base $c–d p% · bull $e–f p%) |
| Valuation zones | attractive below $X · fair $Y–Z · stretched above $W |
| Armed thesis-breakers | condition → resolution date → status |

## 1. Key driver dashboard
| Driver | Type | Share of price | Color | Δ | Why (one line) |
|---|---|---|---|---|---|

Dependencies: [mechanism] → [drivers it caps]

## 2. Indicator dashboards (one table per driver)
### 2.x [Driver name]
| # | Indicator | Source / cadence | 🟢 | 🟡 | 🔴 | Anchor | Reading (date, grade) | Color |
|---|---|---|---|---|---|---|---|---|
Roll-up arithmetic: …
Falsification test: [claim] by [date] → status
Methodology notes: …

## 3. Scenarios & valuation
| Case | What drivers do | Method | Price | Prob |
|---|---|---|---|---|
Weighted value: $X vs. price $Y → [above / near / below]

## 4. What moved since last update
| Direction | Item |
|---|---|
Honest read: …

## 5. Signals and watch-next
- Thesis status read and what drives it
- Probability implications of color changes
- What would upgrade or downgrade the rating
- Next 3–5 dated events and the indicators they resolve

## 6. Calendar
| Date | Event | Indicator it resolves |

## 7. Refresh checklist
- [ ] …

## 8. Change log
- [date]: …

## 9. Machine summary (keep field names stable; read by the webpage)
```yaml
ticker: XXX
as_of: YYYY-MM-DD
price: 0.00
thesis_color: green | yellow | red
review_status: reviewed | draft-unreviewed
weighted_fv: 0
drivers:
  - id: D1
    name: ""
    type: Core | Option | Mechanism | Event
    share_of_price: 0.00
    color: green | yellow | red | none
    delta: up | down | none
    indicators:
      - {id: "1.1", name: "", star: false, kill_switch: false, green: "", yellow: "", red: "", anchor: "", reading: "", reading_date: YYYY-MM-DD, grade: company | third-party | rumor, color: green | yellow | red | none}
falsification_tests:
  - {claim: "", due: YYYY-MM-DD, status: open | pass | fail | partial}
```
```

---

## Reference: how the TSLA dashboard maps to this skill

- **Drivers:** Core auto & cash (Core) · Robotaxi (Option) · Optimus (Option) · FSD reliability (Mechanism, caps Robotaxi and Optimus) · SpaceX merger (Event).
- **Binding constraint for Robotaxi:** crash rate per mile (⭐), not fleet size or city count.
- **Benchmark-anchored threshold:** FSD city miles per critical disengagement vs. Waymo's revealed ~30,000 before removing safety drivers.
- **Disclosure rule in action:** Optimus unit count withheld on four calls → red.
- **Falsification test:** Texas registrations ≥1,500 by mid-October → failed on date, partial on trajectory (1,051 by Oct 27); year-end estimate revised up.
- **Kill switches:** serious unsupervised incident; recall on the camera-only stack.
- **Armed thesis-breakers:** auto gross margin ex-credits <15% for a second quarter (cleared at 18.1%); first credit-line draw while FCF negative (de-escalated).
- **Event weighting:** merger value ≈ 52% × ~$490 + 48% × ~$345 standalone ≈ $420 vs. price ~$407 → near fair, little edge.
- **Signals, not trades:** with Core green and both Options yellow, the thesis reads "under review"; a red FSD Mechanism would cap Robotaxi and Optimus at yellow and shift probability from bull to base.
