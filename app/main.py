from __future__ import annotations

import os
from typing import Dict, List, Tuple

from fastapi import FastAPI, HTTPException, Query

from .market import DEFAULT_EXCHANGE, DEFAULT_QUOTE, fetch_ohlcv, get_symbols, normalize_symbol
from .strategy import (
    analyze_long_signal,
    coarse_symbol_score,
    evaluate_market_regime,
    signal_to_dict,
)

app = FastAPI(title='Presidential Gilsu Long System Upbit', version='2.4.1')

DEFAULT_TIMEFRAMES = os.getenv('SCAN_TIMEFRAMES', '1h').split(',')
DEFAULT_UNIVERSE_LIMIT = int(os.getenv('SCAN_UNIVERSE_LIMIT', '70'))
DEFAULT_SHORTLIST_LIMIT_MAIN = int(os.getenv('SCAN_SHORTLIST_LIMIT_MAIN', '14'))
DEFAULT_SHORTLIST_LIMIT_SUB = int(os.getenv('SCAN_SHORTLIST_LIMIT_SUB', '20'))
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


def _build_shortlist(symbols: List[str], timeframe: str, shortlist_limit: int) -> Tuple[List[str], List[dict], int]:
    ranked: List[Tuple[str, int]] = []
    errors: List[dict] = []
    coarse_scanned = 0
    for symbol in symbols:
        try:
            coarse_ohlcv = fetch_ohlcv(symbol, timeframe=timeframe, limit=90)
            score = coarse_symbol_score(coarse_ohlcv)
            coarse_scanned += 1
            ranked.append((symbol, score))
        except Exception as exc:
            errors.append({'symbol': symbol, 'timeframe': timeframe, 'stage': 'coarse', 'error': str(exc)})
    ranked.sort(key=lambda x: x[1], reverse=True)
    shortlist = [symbol for symbol, score in ranked if score >= 20][:shortlist_limit]
    if not shortlist:
        shortlist = [symbol for symbol, _ in ranked[:shortlist_limit]]
    return shortlist, errors, coarse_scanned


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
    universe_limit: int = Query(DEFAULT_UNIVERSE_LIMIT, ge=20, le=160),
    shortlist_limit: int = Query(DEFAULT_SHORTLIST_LIMIT_MAIN, ge=5, le=40),
    timeframes: str = Query(','.join(DEFAULT_TIMEFRAMES)),
) -> dict:
    frames = [x.strip() for x in timeframes.split(',') if x.strip()]
    primary_tf = frames[0] if frames else '1h'
    try:
        universe = get_symbols(limit=universe_limit)
        regime = _load_regime()
        shortlist, errors, coarse_scanned = _build_shortlist(universe, timeframe=primary_tf, shortlist_limit=shortlist_limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'market_load_failed: {exc}') from exc

    signals: List[dict] = []
    for symbol in shortlist:
        for tf in frames:
            try:
                ohlcv = fetch_ohlcv(symbol, timeframe=tf, limit=320)
                signal = analyze_long_signal(symbol, tf, ohlcv, regime['obj'], strict=True)
                if signal is not None:
                    signals.append(signal_to_dict(signal))
            except Exception as exc:
                errors.append({'symbol': symbol, 'timeframe': tf, 'stage': 'detail', 'error': str(exc)})

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
        'universe_symbols': len(universe),
        'coarse_scanned_symbols': coarse_scanned,
        'shortlisted_symbols': len(shortlist),
        'timeframes': frames,
        'errors': errors[:20],
    }


@app.get('/scan/sub')
def scan_sub(
    universe_limit: int = Query(DEFAULT_UNIVERSE_LIMIT, ge=20, le=160),
    shortlist_limit: int = Query(DEFAULT_SHORTLIST_LIMIT_SUB, ge=8, le=60),
    timeframe: str = Query('1h'),
) -> dict:
    try:
        universe = get_symbols(limit=universe_limit)
        regime = _load_regime()
        shortlist, errors, coarse_scanned = _build_shortlist(universe, timeframe=timeframe, shortlist_limit=shortlist_limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'market_load_failed: {exc}') from exc

    signals: List[dict] = []
    for symbol in shortlist:
        try:
            ohlcv = fetch_ohlcv(symbol, timeframe=timeframe, limit=320)
            signal = analyze_long_signal(symbol, timeframe, ohlcv, regime['obj'], strict=False)
            if signal is not None:
                signals.append(signal_to_dict(signal))
        except Exception as exc:
            errors.append({'symbol': symbol, 'timeframe': timeframe, 'stage': 'detail', 'error': str(exc)})

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
        'signals': signals[:25],
        'universe_symbols': len(universe),
        'coarse_scanned_symbols': coarse_scanned,
        'shortlisted_symbols': len(shortlist),
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
