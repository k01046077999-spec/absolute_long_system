from __future__ import annotations

import os
import time
from functools import lru_cache
from typing import Dict, List, Tuple

import ccxt

DEFAULT_EXCHANGE = os.getenv('EXCHANGE_ID', 'upbit').lower()
DEFAULT_QUOTE = os.getenv('QUOTE', 'KRW').upper()
EXCLUDED_BASES = {'USDC', 'FDUSD', 'TUSD', 'USDP'}
HARD_BLOCK_BASES = {
    'DOGE', 'SHIB', 'PEPE', 'BONK', 'FLOKI', 'WIF', 'PENGU', 'BOME', '1000PEPE',
    '1000BONK', 'TRUMP', 'MELANIA', 'BRETT', 'MEME', 'TURBO', 'POPCAT'
}
REQUEST_SLEEP = float(os.getenv('REQUEST_SLEEP', '0.28'))

_last_request_ts = 0.0

_OHLCV_CACHE: Dict[Tuple[str, str, int], Tuple[float, List[List[float]]]] = {}
_OHLCV_CACHE_TTL = float(os.getenv('OHLCV_CACHE_TTL', '25'))


def _cache_get(symbol: str, timeframe: str, limit: int):
    key = (symbol, timeframe, limit)
    item = _OHLCV_CACHE.get(key)
    if not item:
        return None
    ts, data = item
    if time.time() - ts > _OHLCV_CACHE_TTL:
        _OHLCV_CACHE.pop(key, None)
        return None
    return data


def _cache_set(symbol: str, timeframe: str, limit: int, data: List[List[float]]) -> None:
    _OHLCV_CACHE[(symbol, timeframe, limit)] = (time.time(), data)


def _throttle() -> None:
    global _last_request_ts
    now = time.time()
    wait = REQUEST_SLEEP - (now - _last_request_ts)
    if wait > 0:
        time.sleep(wait)
    _last_request_ts = time.time()


def _safe_float(value) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
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


def fetch_all_tickers() -> Dict[str, dict]:
    exchange = get_exchange()
    _throttle()
    return exchange.fetch_tickers()


def _ticker_rank_value(symbol: str, ticker: dict, market: dict) -> float:
    info = ticker.get('info', {}) or {}
    market_info = market.get('info', {}) or {}
    candidates = [
        ticker.get('quoteVolume'),
        ticker.get('baseVolume'),
        info.get('acc_trade_price_24h'),
        info.get('acc_trade_price'),
        market_info.get('acc_trade_price_24h'),
        market_info.get('acc_trade_price'),
        info.get('trade_price'),
        ticker.get('last'),
    ]
    for value in candidates:
        fv = _safe_float(value)
        if fv > 0:
            return fv
    return 0.0


def get_symbols(limit: int = 80, quote: str = DEFAULT_QUOTE, min_quote_volume_krw: float = 1_000_000_000) -> List[str]:
    exchange = get_exchange()
    tickers = fetch_all_tickers()
    ranked: List[tuple[str, float]] = []
    fallback: List[tuple[str, float]] = []
    for symbol, market in exchange.markets.items():
        if not _is_allowed_market(symbol, market, quote):
            continue
        ticker = tickers.get(symbol, {}) or {}
        score = _ticker_rank_value(symbol, ticker, market)
        if score >= min_quote_volume_krw:
            ranked.append((symbol, score))
        elif score > 0:
            fallback.append((symbol, score))

    ranked.sort(key=lambda x: x[1], reverse=True)
    fallback.sort(key=lambda x: x[1], reverse=True)
    chosen = ranked if ranked else fallback
    return [symbol for symbol, _ in chosen[:limit]]


def fetch_ohlcv(symbol: str, timeframe: str = '1h', limit: int = 300, use_cache: bool = True) -> List[List[float]]:
    exchange = get_exchange()
    normalized = normalize_symbol(symbol)
    if use_cache:
        cached = _cache_get(normalized, timeframe, limit)
        if cached is not None:
            return cached
    _throttle()
    data = exchange.fetch_ohlcv(normalized, timeframe=timeframe, limit=limit)
    if use_cache:
        _cache_set(normalized, timeframe, limit, data)
    return data
