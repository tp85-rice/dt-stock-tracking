# Information Extraction Guide: Turning a Deep Stock Thread into Blog-Ready Source Material

**Trigger phrase:** "Extract information" (optionally with a ticker, date range, or focus).
**Output:** one markdown file combining (1) a discussion compilation and (2) a probability-and-valuation timeline, plus a short chat summary of what is in it and what is missing.
**Built from:** the MRNA Claude discussion compilation and the MRNA probability-of-success and valuation timeline.

---

## 1. What this guide is for

You discuss a company in depth with Claude over weeks or months. The thread becomes the record of how your thinking evolved: what you believed, what changed, which probabilities and valuations you assigned, and why. The blog needs that record in a form that is dated, sourced and honest about gaps. This guide defines how to extract it.

The extraction is **evidence of your reasoning, not proof that its facts are right.** It must never invent a trade, motive, quote, metric, return or anecdote.

---

## 2. Before extracting: checks

1. **Search the whole thread first.** Look for every dated analysis, scenario table, probability estimate, valuation range, price target, trim/add discussion and catalyst list. Do not write from the most recent messages alone.
2. **Assume compaction may have happened.** Long threads get summarized. If a detail (a probability, a table weight, a date) is not actually in the available record, do not reconstruct it. Mark it **[NOT RETAINED]** and say what is missing.
3. **Separate three kinds of content:**
   - what the user said, did or decided;
   - what the assistant suggested or estimated;
   - what an outside source reported.
   Suggestions are not trades. Say so in the file.
4. **Anchor every item to a date.** If the exact date is uncertain, give the best range and flag it in the open-items section. Cross-check dates against price context (for example, a table labeled with one date but built at a price that matches another).
5. **Use the user's pasted text when the record lacks it.** If the user quotes a past exchange, include it as **[QUOTED]** and state that the surrounding conversation was not retained.
6. **Ask only what blocks the file.** If a material date, action or motive cannot be resolved, ask one short question at the end rather than stalling the extraction. Mark minor gaps in brackets and continue.

---

## 3. Source tags (use on every retained claim that could be challenged)

| Tag | Meaning |
|---|---|
| **[QUOTED]** | Text the user pasted from an earlier exchange that is not in the current record |
| **[RETAINED]** | Present in the available record; rationale as summarized |
| **[NOT RETAINED]** | Existed but the number, weights or reasoning were lost; not reconstructed |
| **[DOCUMENTED] / [INFERRED] / [UNKNOWN]** | Optional, for the user's own reasoning behind an action when a trade CSV is attached |

Probabilities, targets and scenario values are **judgment estimates**, not model outputs or company guidance. Say so in the header.

---

## 4. Output structure

One file, named `[TICKER]_discussion_compilation_[YEAR].md`. Use the sections below in order. Drop a section only if the thread has nothing for it, and say "no material retained" instead of leaving it silently absent.

### Header
- Title, coverage period, purpose (blog source material).
- A short paragraph on how it was built (consolidated reconstruction, not a verbatim export; compaction caveat if relevant).
- The sourcing rules and tags from Section 3.

### Part 1: Discussion compilation

1. **Conversation map**: table of date | discussion/scope | substance, in order. Include price at each date when known.
2. **Core investment thesis**: the legs of the thesis, the framework results (scarce complement, billing-unit test, grid cell, market framing where the project instructions call for it), and **what could break the case**.
3. **Financials, costs and financing**: table of topic | points retained. Revenue, cash path, debt and converts, settlements, breakeven targets, and an assessment of any financing.
4. **Core business or franchise sections** (rename per company): for a biotech, the respiratory/commercial franchise; for others, segments, KPIs, unit economics, TAM. Include partnerships and contracts as a table.
5. **Pipeline or growth assets**: one block per major asset: how it works in plain English, key data with numbers, dated catalysts, moat assessment ranked strongest to weakest, and a table of the other programs with status and how the thesis treats each.
6. **Bear cases examined**: for each, the argument, what holds, what doesn't, and the effect on valuation. Include the strongest version of the bear case, not only the rebuttal.
7. **Management**: graded dimensions with evidence, governance flags, how to use the assessment (what to discount, what to take at face value).
8. **Valuation history and bull/bear analysis by date**: one subsection per dated analysis (see Part 2 for the format), plus peer checks, implied-expectations math, and Street targets over time.
9. **Probability-of-success register**: table of catalyst | estimate | outcome (see Part 2 for the full timeline).
10. **Catalyst framework and calendar**: completed events in date order; open events in a table; what to read in each upcoming data release.
11. **Technical analysis**: structure, key levels, support and resistance map with specific numbers, and the post-event "tell" that would change the read.
12. **Options and position-management discussions**: marked **PRIVATE, DO NOT PUBLISH**. Instruments, strikes, structures compared, the user's positions as discussed, the assessment, tax and holding-period issues, and what information is still needed from the user.
13. **How the calls held up**: right calls, wrong or early calls, and corrections made during the thread. Record this plainly.
14. **What changed from earlier theses**: table of earlier question | later answer (use when a prior compilation exists, for example from another platform).
15. **Blog-ready throughline**: a three-to-five sentence arc and a suggested post sequence.
16. **Publication checklist and data gaps**: what to verify against primary sources, what was not retained, and open data gaps.

### Part 2: Probability and valuation timeline

**Part A: Probability-of-success timeline**
- **The method in one paragraph:** start with a base rate, adjust for specific evidence, state the offsetting caution.
- **One entry per date**, each with: the event or evidence; the prior or base rate; the adjusted estimate; the rationale for each adjustment; the offsetting caution; the result when known.
- Use this table where it fits:

| Step | Number | Rationale |
|---|---|---|
| Industry base rate | | |
| Sector adjustment | | |
| Company-specific adjustment | | |
| Offsetting caution | | |

- **Benchmark triangulation table** when outside sources set a bar: source | benchmark | how it moved the estimate.
- **Adjacent catalyst estimates**: catalyst | estimate | date set | rationale.
- **Summary ladder**: date | question being answered | estimate | what moved it. Include the pending item to be scored later.
- Include **pre-registered predictions** (probabilities written before an event) in a clearly labeled table. These are the scoring sheet for the later "what changed?" post.

**Part B: Valuation timeline**
- **One entry per dated analysis**, each with: date and price; market cap and EV when known; the method (sum of the parts, scenarios, reverse DCF, peer check); the building blocks and assumptions; the table; the probability-weighted expected value; what it implied; how it aged.
- **Floors, collected**: floor | value | basis. Include balance-sheet floors, bear-case floors, and technical support.
- **Summary ladder**: date | price | weighted value | floor | main logic.

**Part C: Lessons to carry into the posts**
- The best single exhibit of the reasoning method.
- Right logic with wrong levels, where that happened.
- Calls that were right and calls that were early.
- Which probabilities were set before the evidence and moved on a stated rationale.
- A reminder not to invent missing pieces.

**Part D: Open items before publishing**
- Dates to confirm, original wording to check, figures to re-verify, trades to add from the brokerage record, and predictions to score once the event resolves.

---

## 5. Rules for the content

**Dating and hindsight**
- Preserve what was knowable at each date. Do not use later results to justify an earlier call.
- When a call aged badly or well, record that in a separate "how it aged" line, not in the original entry.
- Show uncertainty, mistakes and changed opinions. Do not smooth them.

**Rationale**
- Every probability, valuation and recommendation gets its reason. A number with no reason is a gap and should be tagged.
- Show direction of each adjustment (up or down) and its cause.

**Numbers**
- Keep figures exactly as discussed. Do not round, reconcile or "correct" them silently. If two figures conflict, show both and flag the conflict.
- Distinguish a company claim, a Street estimate and the user's or assistant's own judgment.
- Mark anything sourced from social media or trade sites as lower reliability.

**Missing data**
- Never fill a gap with a plausible guess. Write **[NOT RETAINED]** and, if useful, what would resolve it.
- List what the user must supply (trade dates, sizes, prices, portfolio weight).

**Privacy**
- Share counts, contract counts, cost basis, tax figures, portfolio percentages and account locations go only in the private section, labeled **PRIVATE, DO NOT PUBLISH**.
- Public sections use direction and proportion, not private figures.

**Cross-platform records**
- If another compilation exists (for example from a different AI platform), cross-reference it and flag any figure that conflicts.

**Style**
- Plain-language explanation first, then supporting numbers. Explain a specialized term briefly the first time it matters.
- Compact tables over long prose for scenarios and ladders.
- No hype, no disclaimers beyond a single closing line ("research notes for writing purposes, not individualized investment advice").

---

## 6. Quality checklist before delivering

- [ ] Every dated analysis in the thread appears, in order.
- [ ] Every probability and valuation has a date, a rationale and (when known) an outcome.
- [ ] Pre-event predictions are in a labeled table that can be scored later.
- [ ] Every retained claim is tagged, and every gap is marked **[NOT RETAINED]**.
- [ ] Right calls, early or wrong calls, and corrections are all recorded.
- [ ] Private details appear only in the private section.
- [ ] Conflicts between figures or dates are flagged, not resolved silently.
- [ ] The open-items list says exactly what to verify, confirm or add.
- [ ] The chat reply states what is in the file, what is missing, and any date or figure that needs checking.

---

## 7. Adapting to non-biotech companies

Swap the biotech-specific parts and keep the rest:

| Biotech section | Replace with |
|---|---|
| Pipeline and clinical data | Product lines, segments, KPIs (DAU, NRR, GMV, bookings), unit economics |
| Probability of clinical success and base rates | Probability of the key catalyst (guidance hit, margin inflection, regulatory ruling, M&A close), with a base rate where one exists |
| Hazard-ratio benchmarks | Consensus and whisper numbers for the key metric |
| Phase 3 / approval | The binary event that decides the thesis |
| Regulatory calendar | Earnings, investor days, product launches, contract renewals |

For AI-leverage names, include the Section 1.8 results from the master instructions (scarce complement, billing-unit test, evidence rating, grid cell, market framing) in the thesis section. Keep the valuation timeline, floors and pre-registered predictions in the same format.

---

## 8. Paste-ready trigger prompt

```
Extract information on [TICKER] from this thread.

Follow the information extraction guide:
- One markdown file: Part 1 (discussion compilation, sections 1–16) and Part 2 (probability-of-success timeline, valuation timeline, lessons, open items).
- Dates on everything; rationale on every probability and valuation; pre-registered predictions in a labeled table.
- Tag claims [QUOTED], [RETAINED] or [NOT RETAINED]. Never reconstruct a missing number.
- Separate my actions from your suggestions; mark trades I executed as unknown unless I supply them.
- Put positions, strikes, share counts, cost basis and tax details only in a section marked PRIVATE, DO NOT PUBLISH.
- Record right calls, wrong or early calls, and corrections.
- Flag date or figure conflicts. End with a publication checklist and open items.
Then tell me in chat what is in the file, what is missing, and what I need to supply.
```

Optional additions to the prompt: a date range ("May–October only"), a focus ("valuation and probabilities only"), or a target post ("for the pre-event decision journal").
