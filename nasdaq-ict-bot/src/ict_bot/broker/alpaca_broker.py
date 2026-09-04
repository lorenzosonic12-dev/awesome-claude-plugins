"""Alpaca execution backend.

Alpaca doesn't offer CME NASDAQ futures, so this trades an equity proxy
(QQQ by default) with Alpaca's bracket orders (entry + stop-loss +
take-profit in one submission). Defaults to the paper-trading endpoint;
pass paper=False only after you've validated the strategy on paper.
"""
from __future__ import annotations

import os

from ict_bot.broker.base import Broker, OrderResult
from ict_bot.core.structure import Direction


class AlpacaBroker(Broker):
    def __init__(self, api_key: str | None = None, secret_key: str | None = None, paper: bool = True) -> None:
        try:
            from alpaca.trading.client import TradingClient
        except ImportError as exc:
            raise ImportError(
                "AlpacaBroker requires the 'alpaca-py' package: pip install alpaca-py"
            ) from exc

        api_key = api_key or os.environ.get("ALPACA_API_KEY")
        secret_key = secret_key or os.environ.get("ALPACA_SECRET_KEY")
        if not api_key or not secret_key:
            raise ValueError("Alpaca API credentials not provided (ALPACA_API_KEY / ALPACA_SECRET_KEY)")

        self.client = TradingClient(api_key, secret_key, paper=paper)

    def get_equity(self) -> float:
        account = self.client.get_account()
        return float(account.equity)

    def get_open_position_count(self, symbol: str) -> int:
        from alpaca.common.exceptions import APIError

        try:
            self.client.get_open_position(symbol)
            return 1
        except APIError:
            return 0

    def submit_bracket_order(
        self,
        symbol: str,
        direction: Direction,
        quantity: float,
        entry: float,
        stop: float,
        target: float,
    ) -> OrderResult:
        from alpaca.trading.enums import OrderClass, OrderSide, TimeInForce
        from alpaca.trading.requests import LimitOrderRequest, StopLossRequest, TakeProfitRequest

        side = OrderSide.BUY if direction == Direction.BULLISH else OrderSide.SELL
        request = LimitOrderRequest(
            symbol=symbol,
            qty=round(quantity),
            side=side,
            time_in_force=TimeInForce.DAY,
            limit_price=round(entry, 2),
            order_class=OrderClass.BRACKET,
            stop_loss=StopLossRequest(stop_price=round(stop, 2)),
            take_profit=TakeProfitRequest(limit_price=round(target, 2)),
        )
        order = self.client.submit_order(request)
        return OrderResult(order_id=str(order.id), status=str(order.status))
