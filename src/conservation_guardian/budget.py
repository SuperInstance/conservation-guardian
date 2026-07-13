"""Budget enforcement for workflow runs."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class WorkflowBudget:
    """Token, cost, and node-count limits for workflow execution."""

    max_tokens_per_run: int = 500_000
    max_cost_per_day: float = 50.0
    max_nodes_per_workflow: int = 100

    _daily_spend: dict[date, float] = field(default_factory=dict, repr=False)
    _run_token_counts: list[int] = field(default_factory=list, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    price_input_per_1k: float = 0.03
    price_output_per_1k: float = 0.06

    def record_run(self, input_tokens: int, output_tokens: int) -> float:
        total = input_tokens + output_tokens
        cost = self._cost(input_tokens, output_tokens)
        today = date.today()
        with self._lock:
            self._run_token_counts.append(total)
            self._daily_spend[today] = self._daily_spend.get(today, 0.0) + cost
        return cost

    def _cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * self.price_input_per_1k + output_tokens * self.price_output_per_1k) / 1_000

    def is_within_budget(self, input_tokens: int, output_tokens: int) -> bool:
        total = input_tokens + output_tokens
        if total > self.max_tokens_per_run:
            return False
        cost = self._cost(input_tokens, output_tokens)
        today = date.today()
        with self._lock:
            if self._daily_spend.get(today, 0.0) + cost > self.max_cost_per_day:
                return False
        return True

    def check_node_count(self, node_count: int) -> bool:
        return node_count <= self.max_nodes_per_workflow

    def daily_spend(self, day: Optional[date] = None) -> float:
        with self._lock:
            return self._daily_spend.get(day or date.today(), 0.0)

    def avg_tokens_per_run(self) -> float:
        with self._lock:
            if not self._run_token_counts:
                return 0.0
            return sum(self._run_token_counts) / len(self._run_token_counts)
