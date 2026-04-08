from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pandas as pd

from app.core.config import settings


class BinanceClient:
    def __init__(self) -> None:
        self.base_url = settings.binance_base_url.rstrip('/')
        self.timeout = httpx.Timeout(12.0, connect=6.0)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.get(f'{self.base_url}{path}', params=params)
            res.raise_for_status()
            return res.json()

    async def exchange_info(self) -> dict[str, Any]:
        return await self._get('/api/v3/exchangeInfo')

    async def tickers_24h(self) -> list[dict[str, Any]]:
        return await self._get('/api/v3/ticker/24hr')

    async def klines(self, symbol: str, interval: str, limit: int) -> pd.DataFrame:
        raw = await self._get('/api/v3/klines', params={'symbol': symbol, 'interval': interval, 'limit': limit})
        df = pd.DataFrame(raw, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume',
            'trade_count', 'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms', utc=True)
        return df.dropna().reset_index(drop=True)

    async def top_symbols(self, limit: int) -> list[str]:
        info, tickers = await asyncio.gather(self.exchange_info(), self.tickers_24h())
        tradable = {
            s['symbol']
            for s in info.get('symbols', [])
            if s.get('status') == 'TRADING' and s.get('quoteAsset') == 'USDT' and s.get('isSpotTradingAllowed')
        }
        excluded = {x.strip().upper() for x in settings.exclude_symbols.split(',') if x.strip()}
        ranked: list[tuple[str, float]] = []
        for t in tickers:
            symbol = t.get('symbol', '')
            if symbol not in tradable or symbol in excluded:
                continue
            if not symbol.endswith('USDT'):
                continue
            qv = float(t.get('quoteVolume') or 0.0)
            last = float(t.get('lastPrice') or 0.0)
            if qv < settings.min_daily_quote_volume_usdt or last <= 0:
                continue
            ranked.append((symbol, qv))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in ranked[:limit]]
