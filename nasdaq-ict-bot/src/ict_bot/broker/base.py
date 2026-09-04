"""Abstract broker interface every execution backend implements."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ict_bot.core.structure import Direction


@dataclass
class OrderResult:
    order_id: str
    status: str


class Broker(ABC):
    @abstractmethod
    def get_equity(self) -> float:
        ...

    @abstractmethod
    def get_open_position_count(self, symbol: str) -> int:
        ...

    @abstractmethod
    def submit_bracket_order(
        self,
        symbol: str,
        direction: Direction,
        quantity: float,
        entry: float,
        stop: float,
        target: float,
    ) -> OrderResult:
        ...
