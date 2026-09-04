"""In-memory paper broker for dry-running the live loop without any real
brokerage connection."""
from __future__ import annotations

import uuid

from ict_bot.broker.base import Broker, OrderResult
from ict_bot.core.structure import Direction


class PaperBroker(Broker):
    def __init__(self, starting_equity: float = 100_000.0) -> None:
        self.equity = starting_equity
        self._open_positions: dict[str, int] = {}
        self.orders: list[dict] = []

    def get_equity(self) -> float:
        return self.equity

    def get_open_position_count(self, symbol: str) -> int:
        return self._open_positions.get(symbol, 0)

    def submit_bracket_order(
        self,
        symbol: str,
        direction: Direction,
        quantity: float,
        entry: float,
        stop: float,
        target: float,
    ) -> OrderResult:
        order_id = str(uuid.uuid4())
        self._open_positions[symbol] = self._open_positions.get(symbol, 0) + 1
        self.orders.append(
            {
                "id": order_id,
                "symbol": symbol,
                "direction": direction.value,
                "quantity": quantity,
                "entry": entry,
                "stop": stop,
                "target": target,
            }
        )
        return OrderResult(order_id=order_id, status="accepted")
