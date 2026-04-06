from __future__ import annotations

import os
from functools import lru_cache
from typing import List

import ccxt

DEFAULT_EXCHANGE = os.getenv('EXCHANGE_ID', 'upbit').lower()
DEFAULT_QUOTE = os.getenv('QUOTE', 'KRW').upper()
EXCLUDED_BASES = {'USDC', 'FDUSD', 'TUSD', 'USDP'}
HARD_BLOCK_BASES = {
    'DOGE', 'SHIB', 'PEPE', 'BONK', 'FLOKI', 'WIF', 'PENGU', 'BOME', '1000PEPE',
    '1000BONK', 'TRUMP', 'MELANIA', 'BRETT', 'MEME', 'TURBO', 'POPCAT'
}


def _volume_rank_value(market: dict) -> float:
    info = market.get('info', {}) or {}
    candidates = [
        info.get('quoteVolume'),
        info.get('acc_trade_price_24h'),
        info.get('acc_trade_price'),
        info.get('trade_price'),
    ]
    for value in candidates:
        try:
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


@lru_cache(maxsize=1)
def get_exchange() -> ccxt.Exchange:
    exchange_class = getattr(ccxt, DEFAULT_EXCHANGE)
    exchange = exchange_class({'enableRateLimit': True})
    exchange.load_markets()
    return exchange


def normalize_symbol(symbol: str, quote: str = DEFAULT_QUOTE) -> str:
    exchange = get_exchange()
    raw = symbol.strip().upper().replace('-', '/')
    if raw in exchange.markets:
        return raw
    if '/' not in raw:
        candidate = f'{raw}/{quote}'
        if candidate in exchange.markets:
            return candidate
    raise ValueError(f'unsupported_symbol_for_{DEFAULT_EXCHANGE}: {symbol}')


def _is_allowed_market(symbol: str, market: dict, quote: str) -> bool:
    if not market.get('active', True):
        return False
    if market.get('spot') is not True:
        return False
    if str(market.get('quote', '')).upper() != quote.upper():
        return False
    base = str(market.get('base', '')).upper()
    if base in EXCLUDED_BASES or base in HARD_BLOCK_BASES:
        return False
    return True


def get_symbols(limit: int = 80, quote: str = DEFAULT_QUOTE, min_quote_volume_krw: float = 5_000_000_000) -> List[str]:
    exchange = get_exchange()
    markets = exchange.markets
    ranked: List[tuple[str, float]] = []
    for symbol, market in markets.items():
        if not _is_allowed_market(symbol, market, quote):
            continue
        score = _volume_rank_value(market)
        if score < min_quote_volume_krw:
            continue
        ranked.append((symbol, score))
    ranked.sort(key=lambda x: x[1], reverse=True)
    return [symbol for symbol, _ in ranked[:limit]]


def fetch_ohlcv(symbol: str, timeframe: str = '1h', limit: int = 300) -> List[List[float]]:
    exchange = get_exchange()
    normalized = normalize_symbol(symbol)
    return exchange.fetch_ohlcv(normalized, timeframe=timeframe, limit=limit)
