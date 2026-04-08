from __future__ import annotations

import asyncio
from time import perf_counter

from app.core.config import settings
from app.core.schemas import RiskPlan, ScanResponse, ScanSignal
from app.services.binance_client import BinanceClient
from app.services.divergence import detect_bearish, detect_bullish
from app.services.fibonacci import bearish_fib, bullish_fib, zone_status
from app.services.indicators import enrich
from app.services.pivots import mark_pivots, recent_pivot_highs, recent_pivot_lows
from app.services.scoring import compute_grade


class ScannerEngine:
    def __init__(self) -> None:
        self.client = BinanceClient()

    async def _frames(self, symbol: str):
        df1h, df15m, df4h = await asyncio.gather(
            self.client.klines(symbol, '1h', settings.klines_limit_1h),
            self.client.klines(symbol, '15m', settings.klines_limit_15m),
            self.client.klines(symbol, '4h', settings.klines_limit_4h),
        )
        df1h = mark_pivots(enrich(df1h, settings.rsi_period), settings.pivot_left, settings.pivot_right)
        df15m = mark_pivots(enrich(df15m, settings.rsi_period), settings.pivot_left, settings.pivot_right)
        df4h = mark_pivots(enrich(df4h, settings.rsi_period), settings.pivot_left, settings.pivot_right)
        return df1h, df15m, df4h

    def _volume_ratio(self, df) -> float:
        row = df.iloc[-1]
        base = float(row['vol_ma_20']) if row['vol_ma_20'] == row['vol_ma_20'] else 0.0
        if base <= 0:
            return 0.0
        return round(float(row['vol_ma_5']) / base, 2)

    def _resistance_room(self, df, side: str) -> float:
        current = float(df['close'].iloc[-1])
        if side == 'bullish':
            recent_high = float(df['high'].tail(50).max())
            return round((recent_high / current - 1.0) * 100.0, 2)
        recent_low = float(df['low'].tail(50).min())
        return round((current / recent_low - 1.0) * 100.0, 2)

    def _overheated(self, df) -> bool:
        val = float(df['pct_from_20_low'].iloc[-1])
        return val >= settings.hot_move_exclude_pct

    def _risk(self, side: str, current: float, fib: dict, room_pct: float) -> RiskPlan:
        invalidation = float(fib['fib_1'])
        if side == 'bullish':
            risk_pct = ((invalidation / current) - 1.0) * 100.0
            tp1_price = current * (1.0 + max(room_pct, 4.0) / 100.0)
            tp2_price = current * (1.0 + max(room_pct * 1.8, 8.0) / 100.0)
            tp1_pct = (tp1_price / current - 1.0) * 100.0
            tp2_pct = (tp2_price / current - 1.0) * 100.0
        else:
            risk_pct = ((current / invalidation) - 1.0) * 100.0 * -1.0
            tp1_price = current * (1.0 - max(room_pct, 4.0) / 100.0)
            tp2_price = current * (1.0 - max(room_pct * 1.8, 8.0) / 100.0)
            tp1_pct = (current / tp1_price - 1.0) * 100.0
            tp2_pct = (current / tp2_price - 1.0) * 100.0
        stop_abs = abs(risk_pct) if risk_pct != 0 else 999.0
        rr1 = round(tp1_pct / stop_abs, 2)
        rr2 = round(tp2_pct / stop_abs, 2)
        return RiskPlan(
            entry_reference=round(current, 8),
            fib_0618=round(float(fib['fib_0618']), 8),
            fib_0786=round(float(fib['fib_0786']), 8),
            invalidation_price=round(invalidation, 8),
            invalidation_rule='fib_1_break',
            stop_loss_pct=round(risk_pct, 2),
            tp1_price=round(tp1_price, 8),
            tp1_pct=round(tp1_pct, 2),
            tp2_price=round(tp2_price, 8),
            tp2_pct=round(tp2_pct, 2),
            rr_tp1=rr1,
            rr_tp2=rr2,
        )

    def _passes_filters(self, mode: str, side: str, current: float, fib: dict, zone: str, volume_ratio: float, overheated: bool, room_pct: float, risk: RiskPlan, div_kind: str) -> tuple[bool, list[str]]:
        rejected: list[str] = []
        fib_0618 = float(fib['fib_0618'])
        fib_0786 = float(fib['fib_0786'])
        upper = max(fib_0618, fib_0786)
        lower = min(fib_0618, fib_0786)

        if mode == 'main' and div_kind != 'chain':
            rejected.append('main_requires_chain_divergence')
        if zone == 'out_zone' and mode == 'main':
            rejected.append('fib_zone_miss')
        if side == 'bullish' and current > upper * (1 + settings.late_entry_buffer_pct / 100.0):
            rejected.append('late_long_entry')
        if side == 'bearish' and current < lower * (1 - settings.late_entry_buffer_pct / 100.0):
            rejected.append('late_short_entry')
        if volume_ratio < settings.min_volume_ratio:
            rejected.append('weak_volume')
        if overheated and side == 'bullish':
            rejected.append('overheated_after_rally')
        if room_pct < settings.resistance_min_room_pct:
            rejected.append('too_close_to_resistance')
        min_rr = settings.min_rr_main if mode == 'main' else settings.min_rr_sub
        if risk.rr_tp2 < min_rr:
            rejected.append('rr_too_low')
        return len(rejected) == 0, rejected

    async def analyze_symbol(self, symbol: str, mode: str) -> ScanSignal | None:
        try:
            df1h, df15m, df4h = await self._frames(symbol)
            current = float(df1h['close'].iloc[-1])
            rsi1h = float(df1h['rsi'].iloc[-1])
            rsi15m = float(df15m['rsi'].iloc[-1])

            bull1h = detect_bullish(recent_pivot_lows(df1h), settings.pivot_min_gap, settings.pivot_max_gap, settings.min_chain_span)
            bear1h = detect_bearish(recent_pivot_highs(df1h), settings.pivot_min_gap, settings.pivot_max_gap, settings.min_chain_span)
            bull15m = detect_bullish(recent_pivot_lows(df15m), settings.pivot_min_gap, settings.pivot_max_gap, settings.min_chain_span)
            bear15m = detect_bearish(recent_pivot_highs(df15m), settings.pivot_min_gap, settings.pivot_max_gap, settings.min_chain_span)
            bull4h = detect_bullish(recent_pivot_lows(df4h), settings.pivot_min_gap, settings.pivot_max_gap, settings.min_chain_span)
            bear4h = detect_bearish(recent_pivot_highs(df4h), settings.pivot_min_gap, settings.pivot_max_gap, settings.min_chain_span)

            long_score = 0.0
            short_score = 0.0
            if bull1h['found']:
                long_score += 38 if bull1h['kind'] == 'chain' else 24
            if bull15m['found']:
                long_score += 10 if bull15m['kind'] == 'chain' else 6
            if bull4h['found']:
                long_score += 14 if bull4h['kind'] == 'chain' else 8
            if 22 <= rsi1h <= 45:
                long_score += 8

            if bear1h['found']:
                short_score += 38 if bear1h['kind'] == 'chain' else 24
            if bear15m['found']:
                short_score += 10 if bear15m['kind'] == 'chain' else 6
            if bear4h['found']:
                short_score += 14 if bear4h['kind'] == 'chain' else 8
            if 55 <= rsi1h <= 78:
                short_score += 8

            if max(long_score, short_score) == 0:
                return None

            side = 'bullish' if long_score >= short_score else 'bearish'
            score = long_score if side == 'bullish' else short_score
            div = bull1h if side == 'bullish' else bear1h
            fib = bullish_fib(df1h) if side == 'bullish' else bearish_fib(df1h)
            zone = zone_status(current, fib['fib_0618'], fib['fib_0786'], settings.fib_tolerance_pct)
            if zone == 'in_zone':
                score += 16
            elif zone == 'near_zone':
                score += 8

            volume_ratio = self._volume_ratio(df1h)
            if volume_ratio >= 1.25:
                score += 8
            elif volume_ratio >= 1.05:
                score += 4

            room_pct = self._resistance_room(df1h, side)
            overheated = self._overheated(df1h)
            risk = self._risk(side, current, fib, room_pct)
            passed, rejected = self._passes_filters(mode, side, current, fib, zone, volume_ratio, overheated, room_pct, risk, div['kind'])
            grade = compute_grade(score)

            reasons = [
                f"1h {('상승' if side == 'bullish' else '하락')} 다이버전스 {div['kind']}",
                f"피보나치 {zone}",
                f"거래량비 {volume_ratio}",
                '피보나치 1 이탈 시 무효',
            ]
            if bull15m['found'] or bear15m['found']:
                reasons.append('15분 보조확인')
            if bull4h['found'] or bear4h['found']:
                reasons.append('4시간 방향보조')

            return ScanSignal(
                symbol=symbol,
                mode=mode,
                side=side,
                score=round(score, 2),
                grade=grade,
                state='candidate' if passed else 'watch',
                current_price=round(current, 8),
                reason_summary=' | '.join(reasons),
                divergence_kind=div['kind'],
                chain_points=int(div.get('points', 0)),
                fib_zone_status=zone,
                volume_ratio=volume_ratio,
                rsi_1h=round(rsi1h, 2),
                rsi_15m=round(rsi15m, 2),
                resistance_room_pct=room_pct,
                risk=risk,
                filters_passed=passed,
                rejected_reasons=rejected,
            )
        except Exception:
            return None

    async def scan(self, mode: str) -> ScanResponse:
        started = perf_counter()
        limit = settings.scan_symbol_limit_main if mode == 'main' else settings.scan_symbol_limit_sub
        symbols = await self.client.top_symbols(limit)
        tasks = [self.analyze_symbol(symbol, mode) for symbol in symbols]
        analyzed = [x for x in await asyncio.gather(*tasks) if x is not None]
        analyzed.sort(key=lambda x: (x.filters_passed, x.score, x.risk.rr_tp2), reverse=True)
        passed = [x for x in analyzed if x.filters_passed]
        top_picks = passed[:settings.top_pick_count]
        return ScanResponse(
            mode=mode,
            scanned_symbols=len(symbols),
            matched_symbols=len(passed),
            elapsed_seconds=round(perf_counter() - started, 2),
            top_picks=top_picks,
            signals=analyzed[: max(settings.top_pick_count, 20)],
        )
