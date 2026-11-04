---
name: "thesis-discussion-loop"
description: "Run the interactive stock discussion in the Investment Thesis project to establish a base case, and save each session's view changes, evidence and Duong's judgment calls to a per-ticker state file."
---

# Thesis Discussion Loop

This is the interactive part of the research process: the back-and-forth where the owner questions, pushes back, drops in evidence and adds judgment, and the view on a stock gets tuned over weeks. The model's weights never change, so the tuning only survives if it is written down and read back. This skill makes that happen.

**Scope: the stock, not the owner's position.** The output is a base case for the business and the stock, with bull and bear cases around it, plus the monitoring plan. It does not depend on what the owner holds, his cost basis, entry or exit plans, sizing, tax lots or options. Those never enter the rating, the fair value, the probabilities or any file this skill writes (see Position-neutral rule).

This skill does **not** decide what a thesis contains. The Equity Research Master Instructions do (Master Prompt 1 Sections 1–6 and 8, Section 1.8 AI leverage, the suppression test, behavioral notes). Skip their position-dependent parts (Section 7 Options & Positioning Overlay, entry tickets). This skill adds the process layer: every session starts from the saved current view and ends by writing what changed, why, and who changed it.

Pipeline:

```
discussion (this skill) -> claude/[TICKER]_Thesis_State.md -> thesis-driver-dashboard -> claude/[TICKER]_Dashboard.md -> webpage / blog extraction
```

## Position-neutral rule

- The rating answers one question: **at today's price, with no position, is this stock worth owning, and on what evidence?** Buy = price sits meaningfully below the probability-weighted fair value with the evidence trending right; Hold = near fair value or evidence mixed; Sell = price above fair value or the thesis is breaking.
- If the owner mentions his holdings, basis, lots, covered calls, trims, entries or exits, do not use them in the analysis and do not write them to the state file or the dashboard. If the message is only about execution ("what expiry for the puts?", "which lot to trim?"), say in one line that this is outside these skills, answer it as a normal question if useful, and write nothing to the state file.
- Judgment about the **business** ("I think the market underrates X") is in scope and gets captured. Judgment about **what to do with his shares** is not.
- The state file and dashboard must be safe to show on a page without redaction.

## Files

| File | Role | Written by |
|---|---|---|
| `claude/[TICKER]_Thesis_State.md` | Current view: the single source of truth for rating, conviction, scenarios, probabilities, predictions, judgment log | this skill |
| `claude/House_Rules.md` | Cross-ticker analysis rules learned from the owner's pushback | this skill, only after the owner says yes |
| `claude/[TICKER]_Dashboard.md` | Drivers, indicators, thresholds, colors | thesis-driver-dashboard |
| Equity Research Master Instructions | What each analysis contains | owner |

## Start of every session

1. Identify the ticker. `project_read` the state file and `claude/House_Rules.md` if they exist. Apply House Rules silently.
2. If there is no state file but the thread already holds work on the ticker, run **Bootstrap** (below) before answering.
3. Read the Master Instructions if they have not been read in this conversation.
4. Search for the current price and anything new since the state file's `as_of`. Never present the saved price or saved facts as current.
5. If the state file and the thread disagree, the newer dated item wins; flag the conflict in one line.
6. Classify the message into a session type. Do not announce the classification.

## Session types

| Type | Recognize by | What to do |
|---|---|---|
| **Initiate** | "Thesis on X" or "Full analysis on X" and no state file | Run Master Prompt 1 Sections 1–6 and 8 (skip Section 7). Create the state file. Pre-register 3–5 dated predictions. Offer the dashboard build. |
| **Interrogate** | A why/how question about the business ("Why can't Tesla scale robotaxi if Waymo can?") | Answer from first principles; find the binding constraint. Then say explicitly whether the answer moves anything: a driver, a probability, a threshold, or nothing. Most answers sharpen an indicator rather than the price; hand those to the dashboard. |
| **Evidence drop** | Screenshot, tweet, article or data point, often with a reliability caveat ("take with a grain of salt") | Grade the source (company-confirmed / third-party data / rumor or social). Check internal consistency (does the claim contradict its own numbers?). Run both branches: if true, what changes; if false, what changes. Name the observable that would confirm it within weeks and add it as a dated falsification test. Rumor-grade evidence may nudge a probability by a few points at most and never changes the rating. |
| **Event update** | Earnings, launch event, regulatory ruling, deal news | Score the pre-registered predictions first (pass / fail / partial, with the number), before any narrative. Then update. Separate what happened in the business from how the price reacted. |
| **Judgment input** | The owner disagrees, reweights or asserts a view about the business ("the market is underpricing X", "that bear case is overdone") | Follow **Capturing the owner's judgment** below. The most important type. |
| **Stress test** | "Bear case for X", "stress test the valuation" | Steel-man the strongest bear; state the probability it gets and what the smart bears who are right would point to. |
| **Monitoring** | "Build a card", "update the dashboard" | Hand off to thesis-driver-dashboard; it reads the state file. |
| **Side question** | Comparison, sector or macro question that touches the ticker | Answer. Write to the state file only if it moves something. |
| **Out of scope** | Entry, exit, sizing, options, tax lots, lending | See Position-neutral rule. One line, no file writes. |

## Capturing the owner's judgment

When the owner gives a view rather than a fact:

1. **Restate it as a testable claim**: what would be observably true if he is right, and by when.
2. **Steel-man the other side** in 2–4 sentences with the evidence. The Master Instructions ask for challenge, not confirmation.
3. **Decide, and say which:**
   - **Adopt**: his argument or evidence is stronger. Update the view. Source tag `[owner judgment]`.
   - **Adopt with a marker**: a weighting call the evidence cannot settle (how much option value to pay for, how long to give management). Use his weighting, tag `[owner weighting]`, and write the condition that would reverse it.
   - **Hold the disagreement**: the evidence contradicts it. Keep the analytical view, record both views side by side with the test that settles it. Never quietly cave; never quietly ignore.
4. **Classify the input:**
   - A **fact** goes to the evidence log.
   - A **ticker-specific judgment** goes to the Judgment Log in the state file.
   - A **general rule** about how to analyze any stock (examples from TSLA: registrations are authorizations, not operating cars; a metric the company withholds on a natural disclosure occasion is a signal; social-media data gets the if-true analysis but cannot move the rating) is proposed for `claude/House_Rules.md` at the end of the session. Add it only on his yes.
5. **Score judgments later.** At every event update or "Thesis review", resolve open Judgment Log entries: who was right, the owner or the analysis, and by how much. This scorecard is the calibration record. It shows where the owner's judgment adds edge and where it is bias. Be strict where conviction has run ahead of evidence.

## Disciplines (learned on TSLA)

- Anything that describes the world now is looked up, never recalled.
- Separate footprint metrics (cities, units built, announcements) from validation metrics (crash rate, disengagement rate, unit economics). Footprint lags; validation leads.
- Disclosure behavior is data. Note what the company stops reporting or redefines (TSLA redefined FSD subscriptions in Q3).
- Conflicting figures are shown side by side and flagged, never reconciled silently.
- Keep standalone value and event-weighted value (merger, approval) separate, and show the weighting arithmetic.
- Before every known event, pre-register predictions with probabilities. The predictions table is the scoring sheet.
- Call out price moves that the drivers do not support, in both directions.
- When an earlier statement of mine was wrong (bad assumption, stale data), log it as `[correction]` with what was wrong. Do not smooth the record.

## End of every session: state delta

If anything changed, end the reply with this block, then save:

```
State delta — [TICKER] — [date]
Rating: Hold → Hold | Conviction: Medium → Medium
Weighted FV: $X → $Y  [source tag] why
Probabilities: bull a% → b% · base … · bear …  [source tag] why
Drivers / thresholds: … (dashboard refresh needed: yes/no)
Predictions: new … by [date] · scored …
Judgment log: [adopted | marker | disagreement] …
House-rule candidate: "…" — add? (yes/no)
```

Source tags: `[evidence]` `[owner judgment]` `[owner weighting]` `[analysis]` `[correction]`.

Save by `project_read` → merge → `project_write` of the full state file (there is no partial patch). Update `as_of`, `last_session`, and the session log. Rating and conviction never change without appearing in the delta.

If nothing changed, add one session-log line and say "No change to the view" in one line. No block.

## Bootstrap (existing threads without a state file)

1. Mine the thread with the extraction-guide method, condensed: the latest dated thesis, rating, conviction, fair value, scenarios and probabilities, open predictions, thesis-breakers, and every point where the owner pushed back or added judgment about the business. Leave out anything about his holdings or trades.
2. Tag each item `[RETAINED]` or `[NOT RETAINED]`. Never reconstruct a missing number.
3. Write the state file with `review_status: pending-owner`, show the owner the header and the Judgment Log, and ask him to confirm or fix them in one pass. Then set `reviewed`.

## Automation rules

- `review_status` is `reviewed` only after a session with the owner. Unattended runs (scheduled refresh, cold start on a new ticker) set `draft-unreviewed`.
- Unattended runs may update price, readings, colors and the evidence log. They may **not** change rating, conviction, scenario probabilities or the Judgment Log. They write proposed changes into the **Pending review** section; the next owner session accepts or rejects each one.
- A cold-start thesis on a new ticker is labeled "No owner judgment yet" until a discussion session runs.
- The YAML header is the contract with the dashboard skill and the webpage. Keep field names stable; add fields, do not rename them.
- Nothing in the state file is private position data, so any file can be rendered on a page as is.

## State file template

```markdown
---
ticker: XXX
company: Name
as_of: YYYY-MM-DD
price: 0.00
price_date: YYYY-MM-DD
rating: Buy | Hold | Sell
conviction: High | Medium | Low
horizon: 12-24m
stage: Early Hypergrowth | Growth | Maturing Growth | Mature/Value
suppression_read: temporary | structural | unclear | n/a
grid_cell: e.g. Owned-Strong x Emerging (ALPHA CELL)
market_framing: AI winner | neutral | loser
fair_value:
  weighted: 0
  standalone: [0, 0]
  event_weighted: null
  zones: {attractive_below: 0, fair: [0, 0], stretched_above: 0}
scenarios:
  - {case: bear, range: [0, 0], prob: 0.00}
  - {case: base, range: [0, 0], prob: 0.00}
  - {case: bull, range: [0, 0], prob: 0.00}
drivers:
  - {id: D1, name: "", type: Core | Option | Mechanism | Event, share_of_price: 0.00, color: green | yellow | red | none}
thesis_color: green | yellow | red | none
thesis_breakers:
  - {condition: "", resolves_by: YYYY-MM-DD, status: armed | cleared | triggered}
next_event: {date: YYYY-MM-DD, event: ""}
review_status: reviewed | pending-owner | draft-unreviewed
last_session: YYYY-MM-DD
dashboard: claude/XXX_Dashboard.md
---

# [TICKER] Thesis State

## 1. Current view
- 5 one-sentence bullets
- What's priced in at today's price
- Suppression read: temporary or structural, and what the bears who are right would point to

## 2. Thesis legs and breakers
| # | Leg | Conviction rank | Breaker (observable, dated) |

## 3. Scenarios and valuation
| Case | What the drivers do | Method | Price | Prob |
Weighted value arithmetic; event weighting if any; valuation zones and the logic behind them.

## 4. Pre-registered predictions
| # | Claim | Prob | Set on | Resolves by | Outcome |

## 5. Open questions
| Question | Why it matters | What resolves it | Due |

## 6. Judgment log
| Date | Owner view | Analysis view | Resolution (adopted / marker / disagreement) | Test | Outcome | Who was right |

## 7. Evidence log (graded, key items only)
| Date | Item | Grade | Effect |

## 8. Pending review (written by unattended runs)
| Date | Proposed change | Reason | Accept / reject |

## 9. Session log
| Date | Type | Trigger | Delta summary |
```

## House Rules file format

```markdown
# House Rules
- [date] Rule. Origin: [TICKER], [one-line example].
```

Read at the start of every session on any ticker; apply without comment.