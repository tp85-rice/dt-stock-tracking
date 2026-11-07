"""Plumbing for the AI analyst agents (M5). The AI calls themselves are not built yet.

What is here, so the agents can be plugged in later without touching the rest of the system:

* answers.py   - the shape of one agent answer (JSON lines) and its schema check.
* checks.py    - the code-level quote check: the quote must be in the source text, and the number in the quote.
* evaluate.py  - scores agent answers against the gold set in the LLM scorecard (templates/llm_eval_scorecard.xlsx)
                 and writes them into its Runs tab for a human to check.
* submit.py    - puts agent answers into the review queue (or only prints them with --dry-run).
                 Answers that fail the quote check go in as 'rejected_by_check', never as pending.
* budget.py    - the daily cost cap: refuses a model call that could take the day's spend over the cap.

Nothing an agent produces reaches the dashboard until a reviewer approves it on /review.
"""
