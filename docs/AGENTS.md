# AI agents (M5): what is built and how to use it

The AI model calls are **not built yet**; they wait for Duong's gold set (20-30 hand-labelled cases in
`templates/llm_eval_scorecard.xlsx`, tab "Gold set"). Everything around them is built and tested, so an agent only
has to produce answers in one agreed shape (`worker/agents/answers.py`).

## 1. Score an agent against the gold set

```bash
python -m worker.agents.evaluate templates/llm_eval_scorecard.xlsx answers.jsonl --version junior-v0.1 --out scored.xlsx
```

- Prints value accuracy, citation, hallucination and schema rates with PASS / FAIL against the targets on the
  scorecard's Summary tab (90% / 95% / 2% / 99% today).
- Writes one Runs row per gold case into `scored.xlsx` (a copy; the scorecard itself is not changed).
- "Citation valid" is only pre-filled by the code (quote is word for word in the passage). A person must confirm
  the quote supports the claim, as the scorecard asks; the row's Notes say so.
- The script reads columns by position. If the scorecard's columns change, update `GOLD` and `RUNS` in
  `worker/agents/evaluate.py` (and its test).

## 2. Send answers to the review queue

```bash
python -m worker.agents.submit answers.jsonl --dry-run
```

```bash
python -m worker.agents.submit answers.jsonl
```

- `--dry-run` prints what would be proposed and writes nothing. Without it, answers go to `/review` like the daily feeds.
- Only signals the owners defined are accepted. A reading already recorded or proposed is skipped.
- The **quote check** runs in code: the quote must be in the fetched source text and the number must be in the quote.
  A failing answer is stored as "rejected by check" with the reasons and never shown as pending.
- A new source found by an agent is logged as Tier C with unknown terms, for the reviewer to correct.

## 3. Daily cost cap

- `AGENT_DAILY_USD_CAP` (default $1.00 a day, UTC). Before each model call an agent asks
  `Budget.reserve(model, input_tokens, max_output_tokens)`; a call that could go over the cap is refused.
- Spend is the `cost_usd` of today's `runs` rows whose job starts with `agent`.
- Prices per model are in `worker/agents/budget.py` (list prices as of 2026-10-06). A model not in that table is
  refused, so the cap cannot be bypassed by a typo. Update the table when prices change.

## Order for M5

1. Gold set filled (Duong), scored by two people on about 20% of rows.
2. Junior agent written to produce `answers.jsonl` for the gold cases; score it with step 1 until it passes.
3. Run it on real filings with `--dry-run`, then for real into the review queue. Owners approve every reading.
