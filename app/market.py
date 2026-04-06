from __future__ import annotations

import os
from typing import List

import ccxt


DEFAULT_EXCHANGE = os.getenv('EXCHANGE_ID', 'binance')
DEFAULT_QUOTE = os.getenv('QUOTE', 'USDT')


def get_exchange() -> ccxt.Exchange:
    exchange_class = getattr(ccxt, DEFAULT_EXCHANGE)
    exchange = exchange_class({"enableRateLimit": True})
    exchange.load_markets()
    return exchange


def get_symbols(limit: int = 80, quote: str = DEFAULT_QUOTE) -> List[str]:
    exchange = get_exchange()
    markets = exchange.markets
    symbols: List[str] = []
    for symbol, market in markets.items():
        if not market.get('active', True):
            continue
        if market.get('spot') is not True:
            continue
        if market.get('quote') != quote:
            continue
        if market.get('base') in {'USDC', 'FDUSD', 'TUSD'}:
            continue
        symbols.append(symbol)
    # Use quote volume ranking when available.
    ranked = sorted(
        symbols,
        key=lambda s: float(markets[s].get('info', {}).get('quoteVolume') or 0.0),
        reverse=True,
    )
    return ranked[:limit]


def fetch_ohlcv(symbol: str, timeframe: str = '1h', limit: int = 300) -> List[List[float]]:
    exchange = get_exchange()
    return exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
