from __future__ import annotations

import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query

from .market import fetch_ohlcv, get_symbols
from .strategy import analyze_long_signal, signal_to_dict

app = FastAPI(title='Absolute Long System', version='1.0.0')

DEFAULT_TIMEFRAMES = os.getenv('SCAN_TIMEFRAMES', '1h,4h').split(',')
DEFAULT_SYMBOL_LIMIT = int(os.getenv('SCAN_SYMBOL_LIMIT', '40'))


@app.get('/health')
def health() -> dict:
    return {'status': 'ok', 'service': 'absolute-long-system'}


@app.get('/scan/long')
def scan_long(
    symbol_limit: int = Query(DEFAULT_SYMBOL_LIMIT, ge=5, le=200),
    timeframes: str = Query(','.join(DEFAULT_TIMEFRAMES)),
) -> dict:
    frames = [x.strip() for x in timeframes.split(',') if x.strip()]
    try:
        symbols = get_symbols(limit=symbol_limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'market_load_failed: {exc}') from exc

    signals: List[dict] = []
    errors: List[dict] = []

    for symbol in symbols:
        for tf in frames:
            try:
                ohlcv = fetch_ohlcv(symbol, timeframe=tf, limit=320)
                signal = analyze_long_signal(symbol, tf, ohlcv)
                if signal is not None:
                    signals.append(signal_to_dict(signal))
            except Exception as exc:
                errors.append({'symbol': symbol, 'timeframe': tf, 'error': str(exc)})

    signals = sorted(signals, key=lambda x: (x['score'], x['take_profit_2_pct']), reverse=True)
    return {
        'strategy': 'absolute_long_system',
        'mode': 'long_only',
        'count': len(signals),
        'signals': signals[:20],
        'scanned_symbols': len(symbols),
        'timeframes': frames,
        'errors': errors[:20],
    }


@app.get('/scan/single')
def scan_single(symbol: str, timeframe: str = '1h') -> dict:
    try:
        ohlcv = fetch_ohlcv(symbol, timeframe=timeframe, limit=320)
        signal = analyze_long_signal(symbol, timeframe, ohlcv)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'scan_failed: {exc}') from exc

    return {
        'strategy': 'absolute_long_system',
        'mode': 'long_only',
        'signal': signal_to_dict(signal) if signal else None,
    }
