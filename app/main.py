from __future__ import annotations

import os
from typing import List

from fastapi import FastAPI, HTTPException, Query

from .market import DEFAULT_EXCHANGE, DEFAULT_QUOTE, fetch_ohlcv, get_symbols, normalize_symbol
from .strategy import analyze_long_signal, evaluate_market_regime, signal_to_dict

app = FastAPI(title='Presidential Gilsu Long System Upbit', version='2.2.0')

DEFAULT_TIMEFRAMES = os.getenv('SCAN_TIMEFRAMES', '1h').split(',')
DEFAULT_SYMBOL_LIMIT = int(os.getenv('SCAN_SYMBOL_LIMIT', '40'))
BTC_BENCHMARK = os.getenv('BTC_BENCHMARK', 'BTC/KRW')


def _load_regime() -> dict:
    btc_1h = fetch_ohlcv(BTC_BENCHMARK, timeframe='1h', limit=320)
    btc_4h = fetch_ohlcv(BTC_BENCHMARK, timeframe='4h', limit=320)
    regime = evaluate_market_regime(btc_1h, btc_4h)
    return {
        'allowed': regime.allowed,
        'score': regime.score,
        'reasons': regime.reasons,
        'meta': regime.meta,
        'obj': regime,
    }


@app.get('/health')
def health() -> dict:
    regime = _load_regime()
    return {
        'status': 'ok',
        'service': 'presidential-gilsu-long-system',
        'exchange': DEFAULT_EXCHANGE,
        'quote': DEFAULT_QUOTE,
        'mode': 'long_only',
        'btc_regime_allowed': regime['allowed'],
        'btc_regime_score': regime['score'],
    }


@app.get('/scan/main')
def scan_main(
    symbol_limit: int = Query(DEFAULT_SYMBOL_LIMIT, ge=5, le=200),
    timeframes: str = Query(','.join(DEFAULT_TIMEFRAMES)),
) -> dict:
    frames = [x.strip() for x in timeframes.split(',') if x.strip()]
    try:
        symbols = get_symbols(limit=symbol_limit)
        regime = _load_regime()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'market_load_failed: {exc}') from exc

    signals: List[dict] = []
    errors: List[dict] = []

    for symbol in symbols:
        for tf in frames:
            try:
                ohlcv = fetch_ohlcv(symbol, timeframe=tf, limit=320)
                signal = analyze_long_signal(symbol, tf, ohlcv, regime['obj'], strict=True)
                if signal is not None:
                    signals.append(signal_to_dict(signal))
            except Exception as exc:
                errors.append({'symbol': symbol, 'timeframe': tf, 'error': str(exc)})

    signals = sorted(signals, key=lambda x: (x['score'], x['regime_score'], -x['stop_loss_pct']), reverse=True)
    return {
        'strategy': 'presidential_gilsu_long_upbit',
        'mode': 'main',
        'exchange': DEFAULT_EXCHANGE,
        'quote': DEFAULT_QUOTE,
        'btc_regime_allowed': regime['allowed'],
        'btc_regime_score': regime['score'],
        'btc_regime_reasons': regime['reasons'],
        'btc_regime_meta': regime['meta'],
        'count': len(signals),
        'signals': signals[:20],
        'scanned_symbols': len(symbols),
        'timeframes': frames,
        'errors': errors[:20],
    }


@app.get('/scan/sub')
def scan_sub(
    symbol_limit: int = Query(DEFAULT_SYMBOL_LIMIT, ge=5, le=200),
    timeframe: str = Query('1h'),
) -> dict:
    try:
        symbols = get_symbols(limit=symbol_limit)
        regime = _load_regime()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'market_load_failed: {exc}') from exc

    signals: List[dict] = []
    errors: List[dict] = []

    for symbol in symbols:
        try:
            ohlcv = fetch_ohlcv(symbol, timeframe=timeframe, limit=320)
            signal = analyze_long_signal(symbol, timeframe, ohlcv, regime['obj'], strict=False)
            if signal is not None:
                signals.append(signal_to_dict(signal))
        except Exception as exc:
            errors.append({'symbol': symbol, 'timeframe': timeframe, 'error': str(exc)})

    signals = sorted(signals, key=lambda x: (x['score'], x['regime_score'], -x['stop_loss_pct']), reverse=True)
    return {
        'strategy': 'presidential_gilsu_long_upbit',
        'mode': 'sub',
        'exchange': DEFAULT_EXCHANGE,
        'quote': DEFAULT_QUOTE,
        'btc_regime_allowed': regime['allowed'],
        'btc_regime_score': regime['score'],
        'btc_regime_reasons': regime['reasons'],
        'btc_regime_meta': regime['meta'],
        'count': len(signals),
        'signals': signals[:20],
        'scanned_symbols': len(symbols),
        'timeframe': timeframe,
        'errors': errors[:20],
    }


@app.get('/scan/single')
def scan_single(symbol: str, timeframe: str = '1h', mode: str = 'main') -> dict:
    try:
        normalized_symbol = normalize_symbol(symbol)
        regime = _load_regime()
        ohlcv = fetch_ohlcv(normalized_symbol, timeframe=timeframe, limit=320)
        strict = mode.lower() != 'sub'
        signal = analyze_long_signal(normalized_symbol, timeframe, ohlcv, regime['obj'], strict=strict)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'scan_failed: {exc}') from exc

    return {
        'strategy': 'presidential_gilsu_long_upbit',
        'mode': mode.lower(),
        'exchange': DEFAULT_EXCHANGE,
        'quote': DEFAULT_QUOTE,
        'btc_regime_allowed': regime['allowed'],
        'btc_regime_score': regime['score'],
        'signal': signal_to_dict(signal) if signal else None,
    }
