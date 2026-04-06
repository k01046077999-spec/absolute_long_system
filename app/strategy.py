from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

from .indicators import Pivot, ema, pct_change, pivot_lows, rsi, safe_round


@dataclass
class Signal:
    symbol: str
    timeframe: str
    entry: float
    stop_loss_pct: float
    take_profit_1_pct: float
    take_profit_2_pct: float
    score: int
    regime_score: int
    signal_name: str
    reasons: List[str]
    meta: Dict[str, float | str | bool | None]


@dataclass
class CandleSeries:
    ts: List[int]
    open: List[float]
    high: List[float]
    low: List[float]
    close: List[float]
    volume: List[float]


@dataclass
class MarketRegime:
    allowed: bool
    score: int
    reasons: List[str]
    meta: Dict[str, float | str | bool | None]


def to_series(ohlcv: List[List[float]]) -> CandleSeries:
    return CandleSeries(
        ts=[int(x[0]) for x in ohlcv],
        open=[float(x[1]) for x in ohlcv],
        high=[float(x[2]) for x in ohlcv],
        low=[float(x[3]) for x in ohlcv],
        close=[float(x[4]) for x in ohlcv],
        volume=[float(x[5]) for x in ohlcv],
    )


def _bullish_divergence_lows(lows: List[float], rsi_values: List[Optional[float]]) -> Tuple[bool, List[Pivot], Dict[str, float | bool | None]]:
    pivots = pivot_lows(lows, left=3, right=3)
    if len(pivots) < 2:
        return False, pivots, {"three_pivot_linked": False}

    valid: List[Pivot] = []
    for p in pivots:
        rv = rsi_values[p.index]
        if rv is not None:
            valid.append(p)
    if len(valid) < 2:
        return False, valid, {"three_pivot_linked": False}

    recent = valid[-3:]
    first, second = recent[-2], recent[-1]
    rsi_first = rsi_values[first.index]
    rsi_second = rsi_values[second.index]
    regular = bool(
        second.value < first.value and
        rsi_first is not None and
        rsi_second is not None and
        rsi_second > rsi_first
    )
    linked = False
    if len(recent) == 3:
        a, b, c = recent
        ra = rsi_values[a.index]
        rb = rsi_values[b.index]
        rc = rsi_values[c.index]
        linked = bool(
            ra is not None and rb is not None and rc is not None and
            b.value <= a.value and c.value <= b.value and
            rb >= ra and rc >= rb
        )
    return regular, recent, {
        "three_pivot_linked": linked,
        "pivot1_price": first.value,
        "pivot2_price": second.value,
        "pivot1_rsi": rsi_first,
        "pivot2_rsi": rsi_second,
    }


def _wave_is_bullish(lows: List[float], highs: List[float]) -> Tuple[bool, Dict[str, float | bool | None]]:
    low_pivots = pivot_lows(lows, 3, 3)
    if len(low_pivots) < 2:
        return False, {"higher_low": False}
    last_two = low_pivots[-2:]
    higher_low = last_two[-1].value > last_two[-2].value
    recent_high = max(highs[last_two[-1].index:])
    prev_high = max(highs[last_two[-2].index:last_two[-1].index + 1])
    break_high_target = recent_high >= prev_high
    return bool(higher_low), {
        "higher_low": higher_low,
        "recent_low": last_two[-1].value,
        "previous_low": last_two[-2].value,
        "recent_high": recent_high,
        "previous_high": prev_high,
        "break_high_target": break_high_target,
    }


def _fib_zone(closes: List[float], highs: List[float], lows: List[float], lookback: int = 120) -> Dict[str, float | bool | None]:
    if len(closes) < 30:
        return {"in_fib_buy_zone": False}
    end = len(closes)
    start = max(0, end - lookback)
    swing_low = min(lows[start:end])
    swing_high = max(highs[start:end])
    if swing_high <= swing_low:
        return {"in_fib_buy_zone": False}
    diff = swing_high - swing_low
    fib_618 = swing_high - diff * 0.618
    fib_786 = swing_high - diff * 0.786
    fib_1 = swing_low
    price = closes[-1]
    in_zone = fib_786 <= price <= fib_618
    invalidated = price < fib_1
    return {
        "swing_low": swing_low,
        "swing_high": swing_high,
        "fib_618": fib_618,
        "fib_786": fib_786,
        "fib_1": fib_1,
        "in_fib_buy_zone": in_zone,
        "fib_invalidated": invalidated,
    }


def _volume_ok(volume: List[float], closes: List[float]) -> Dict[str, float | bool | None]:
    if len(volume) < 25:
        return {"volume_ok": False}
    avg20 = sum(volume[-20:]) / 20
    avg5 = sum(volume[-5:]) / 5
    rising = avg5 > avg20 * 1.10
    price_change_5 = pct_change(closes[-6], closes[-1]) if len(closes) >= 6 else 0.0
    return {
        "avg_volume_5": avg5,
        "avg_volume_20": avg20,
        "volume_ok": rising,
        "price_change_5": price_change_5,
    }


def _overextended(closes: List[float], highs: List[float], lows: List[float]) -> Dict[str, float | bool | None]:
    fib = _fib_zone(closes, highs, lows, lookback=120)
    price = closes[-1]
    swing_high = fib.get("swing_high")
    swing_low = fib.get("swing_low")
    if not swing_high or not swing_low:
        return {"overextended": False}
    traveled = pct_change(swing_low, price)
    near_top = price >= float(swing_high) * 0.97
    return {
        "overextended": bool(traveled > 28 or near_top),
        "traveled_from_swing_low_pct": traveled,
        "near_top": near_top,
    }


def evaluate_market_regime(btc_1h: List[List[float]], btc_4h: List[List[float]]) -> MarketRegime:
    s1 = to_series(btc_1h)
    s4 = to_series(btc_4h)
    e20_1h = ema(s1.close, 20)
    e60_1h = ema(s1.close, 60)
    e20_4h = ema(s4.close, 20)
    e60_4h = ema(s4.close, 60)
    rsi_1h = rsi(s1.close, 14)
    rsi_4h = rsi(s4.close, 14)

    score = 0
    reasons: List[str] = []
    price_1h = s1.close[-1]
    price_4h = s4.close[-1]
    if e20_1h[-1] is not None and e60_1h[-1] is not None and float(e20_1h[-1]) > float(e60_1h[-1]):
        score += 25
        reasons.append('BTC 1h EMA20>EMA60')
    if e20_4h[-1] is not None and e60_4h[-1] is not None and float(e20_4h[-1]) > float(e60_4h[-1]):
        score += 25
        reasons.append('BTC 4h EMA20>EMA60')
    if e60_1h[-1] is not None and price_1h > float(e60_1h[-1]):
        score += 15
        reasons.append('BTC 1h price>EMA60')
    if e60_4h[-1] is not None and price_4h > float(e60_4h[-1]):
        score += 15
        reasons.append('BTC 4h price>EMA60')
    if rsi_1h[-1] is not None and float(rsi_1h[-1]) >= 47:
        score += 10
        reasons.append('BTC 1h RSI>=47')
    if rsi_4h[-1] is not None and float(rsi_4h[-1]) >= 50:
        score += 10
        reasons.append('BTC 4h RSI>=50')

    allowed = score >= 60
    meta = {
        'btc_price_1h': safe_round(price_1h),
        'btc_price_4h': safe_round(price_4h),
        'btc_ema20_1h': safe_round(e20_1h[-1]),
        'btc_ema60_1h': safe_round(e60_1h[-1]),
        'btc_ema20_4h': safe_round(e20_4h[-1]),
        'btc_ema60_4h': safe_round(e60_4h[-1]),
        'btc_rsi_1h': safe_round(rsi_1h[-1], 2),
        'btc_rsi_4h': safe_round(rsi_4h[-1], 2),
    }
    return MarketRegime(allowed=allowed, score=score, reasons=reasons, meta=meta)


def analyze_long_signal(symbol: str, timeframe: str, ohlcv: List[List[float]], regime: MarketRegime, strict: bool = True) -> Optional[Signal]:
    series = to_series(ohlcv)
    if len(series.close) < 220:
        return None

    rsi_values = rsi(series.close, 14)
    ema20 = ema(series.close, 20)
    ema60 = ema(series.close, 60)
    ema200 = ema(series.close, 200)

    bull_div, pivots, div_meta = _bullish_divergence_lows(series.low, rsi_values)
    wave_ok, wave_meta = _wave_is_bullish(series.low, series.high)
    fib_meta = _fib_zone(series.close, series.high, series.low, 120)
    vol_meta = _volume_ok(series.volume, series.close)
    ext_meta = _overextended(series.close, series.high, series.low)

    price = series.close[-1]
    current_rsi = rsi_values[-1]
    ema20v = float(ema20[-1]) if ema20[-1] is not None else None
    ema60v = float(ema60[-1]) if ema60[-1] is not None else None
    ema200v = float(ema200[-1]) if ema200[-1] is not None else None

    above_ema20 = ema20v is not None and price >= ema20v
    above_ema60 = ema60v is not None and price >= ema60v
    above_ema200 = ema200v is not None and price >= ema200v * 0.90
    not_far_above_ema200 = ema200v is None or price <= ema200v * 1.12

    score = 0
    reasons: List[str] = []

    if bull_div:
        score += 30
        reasons.append('강세 RSI 다이버전스 확인')
    if div_meta.get('three_pivot_linked'):
        score += 20
        reasons.append('3꼭지 다이버전스 연계 확인')
    if fib_meta.get('in_fib_buy_zone'):
        score += 20
        reasons.append('가격이 0.618~0.786 되돌림 구간')
    elif not strict and fib_meta.get('in_relaxed_fib_buy_zone'):
        score += 12
        reasons.append('가격이 0.5~0.786 완화 되돌림 구간')
    if wave_ok and wave_meta.get('break_high_target'):
        score += 15
        reasons.append('상승 파동 higher low + 전고점 회복 시도')
    if vol_meta.get('volume_ok'):
        score += 10
        reasons.append('최근 거래량 평균이 20봉 대비 증가')
    if above_ema20:
        score += 5
        reasons.append('종가가 EMA20 위')
    if above_ema60:
        score += 5
        reasons.append('종가가 EMA60 위')
    if above_ema200:
        score += 5
        reasons.append('가격이 EMA200 대비 과도한 하락 아님')
    if current_rsi is not None and 28 <= current_rsi <= 48:
        score += 10
        reasons.append('RSI 위치가 롱 진입 부담이 과하지 않음')
    elif not strict and current_rsi is not None and 30 <= current_rsi <= 58:
        score += 6
        reasons.append('RSI 위치가 서브 후보 범위 안')

    hard_fail = False
    if strict and not regime.allowed:
        hard_fail = True
    if fib_meta.get('fib_invalidated'):
        hard_fail = True
    if ext_meta.get('overextended'):
        hard_fail = True
    if not not_far_above_ema200:
        hard_fail = True
    if strict and not fib_meta.get('in_fib_buy_zone'):
        hard_fail = True
    if strict and not bull_div:
        hard_fail = True
    if strict and not wave_ok:
        hard_fail = True

    sub_structure_ok = bool(
        bull_div or
        div_meta.get('three_pivot_linked') or
        wave_ok or
        fib_meta.get('in_relaxed_fib_buy_zone')
    )
    sub_trend_ok = bool(above_ema20 or above_ema60)

    min_score = 85 if strict else 52
    if not strict and not sub_structure_ok:
        return None
    if not strict and not sub_trend_ok:
        return None
    if hard_fail or score < min_score:
        return None

    swing_low = float(fib_meta['fib_1'])
    stop_loss_pct = abs(pct_change(price, swing_low))
    if strict and (stop_loss_pct < 2.5 or stop_loss_pct > 8.5):
        return None
    if not strict and stop_loss_pct > 12.5:
        return None
    if stop_loss_pct < 2.5:
        stop_loss_pct = 2.5

    take_profit_1_pct = round(stop_loss_pct * 2.0, 2)
    take_profit_2_pct = round(stop_loss_pct * 3.4, 2)

    meta: Dict[str, float | str | bool | None] = {
        'entry': safe_round(price),
        'current_rsi': safe_round(current_rsi, 2),
        'ema20': safe_round(ema20[-1]),
        'ema60': safe_round(ema60[-1]),
        'ema200': safe_round(ema200[-1]),
        'strict_mode': strict,
        'sub_structure_ok': sub_structure_ok if not strict else None,
        'sub_trend_ok': sub_trend_ok if not strict else None,
        'pivot_count': len(pivots),
    }
    meta.update({k: safe_round(v, 4) if isinstance(v, float) else v for k, v in div_meta.items()})
    meta.update({k: safe_round(v, 4) if isinstance(v, float) else v for k, v in wave_meta.items()})
    meta.update({k: safe_round(v, 4) if isinstance(v, float) else v for k, v in fib_meta.items()})
    meta.update({k: safe_round(v, 4) if isinstance(v, float) else v for k, v in vol_meta.items()})
    meta.update({k: safe_round(v, 4) if isinstance(v, float) else v for k, v in ext_meta.items()})
    meta.update({f'regime_{k}': v for k, v in regime.meta.items()})

    return Signal(
        symbol=symbol,
        timeframe=timeframe,
        entry=round(price, 6),
        stop_loss_pct=round(stop_loss_pct, 2),
        take_profit_1_pct=take_profit_1_pct,
        take_profit_2_pct=take_profit_2_pct,
        score=score,
        regime_score=regime.score,
        signal_name='presidential_gilsu_long_main' if strict else 'presidential_gilsu_long_sub',
        reasons=reasons + ([f'BTC 시장 필터 통과({regime.score})'] if regime.allowed else []),
        meta=meta,
    )


def signal_to_dict(signal: Signal) -> Dict[str, object]:
    return asdict(signal)
