"""Daily cost cap for AI calls.

Every agent run is a row in the runs table (job starting with 'agent'), which already has input_tokens,
output_tokens and cost_usd. Before each model call the agent asks Budget.reserve() with the most the call could
cost (its input plus max_tokens of output); if that could take today's spend (UTC) over the cap, the call is
refused with BudgetExceeded and the run stops. After the call it records what was actually used.

The cap is AGENT_DAILY_USD_CAP (default 1.00 US dollars). Prices are per million tokens, Anthropic first-party
API list prices as of 2026-10-06; check https://www.anthropic.com/pricing before relying on them and update the
table when they change. A model not in the table is refused, so a typo cannot bypass the cap.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# model: (input $ per 1M tokens, output $ per 1M tokens)
PRICES: dict[str, tuple[float, float]] = {
    "claude-fable-5-1": (10.00, 50.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.50, 2.50),  # list price is $0.10 / $0.50 up to 100K-token prompts; the higher rate is used to stay safe
}
DEFAULT_CAP_USD = 1.00


class BudgetExceeded(RuntimeError):
    pass


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    if model not in PRICES:
        raise BudgetExceeded(f"no price for model {model!r}: add it to worker/agents/budget.py PRICES first")
    pin, pout = PRICES[model]
    return (input_tokens * pin + output_tokens * pout) / 1e6


def cap_from_env() -> float:
    raw = os.environ.get("AGENT_DAILY_USD_CAP", "").strip()
    return float(raw) if raw else DEFAULT_CAP_USD


@dataclass
class Budget:
    """conn=None keeps the count in memory only (dry runs and tests)."""
    conn: object | None = None
    cap: float = field(default_factory=cap_from_env)
    run_id: int | None = None
    _local: float = 0.0  # spend recorded through this object

    def spent_today(self) -> float:
        if self.conn is None:
            return self._local
        row = self.conn.execute(
            """select coalesce(sum(cost_usd), 0) from runs
               where job like 'agent%%' and (started_at at time zone 'utc')::date = (now() at time zone 'utc')::date"""
        ).fetchone()
        return float(row[0])

    def reserve(self, model: str, input_tokens: int, max_output_tokens: int) -> float:
        """Call before the model call. Returns the worst-case cost; raises BudgetExceeded if it does not fit."""
        worst = cost_usd(model, input_tokens, max_output_tokens)
        spent = self.spent_today()
        if spent + worst > self.cap:
            raise BudgetExceeded(f"daily AI cap ${self.cap:.2f} reached: spent ${spent:.4f} today, "
                                 f"this call could cost up to ${worst:.4f}")
        return worst

    def record(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Call after the model call with the usage it reported."""
        cost = cost_usd(model, input_tokens, output_tokens)
        self._local += cost
        if self.conn is not None and self.run_id is not None:
            self.conn.execute(
                """update runs set input_tokens = input_tokens + %s, output_tokens = output_tokens + %s,
                                   cost_usd = cost_usd + %s where id = %s""",
                (input_tokens, output_tokens, cost, self.run_id))
        return cost
