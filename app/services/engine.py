from __future__ import annotations

import asyncio
from time import perf_counter

from app.core.config import settings
from app.core.schemas import RiskPlan, ScanResponse, ScanSignal
from app.services.divergence import detect_bullish
from app.services.fibonacci import bullish_fib, zone_status
from app.services.indicators import enrich
from app.services.pivots import mark_pivots, recent_pivot_lows
from app.services.scoring import compute_grade
from app.services.upbit_client import UpbitClient


class ScannerEngine:
    def __init__(self) -> None:
        self.client = UpbitClient()

    async def _frames(self, market: str):
        df1h, df15m, df4h = await asyncio.gather(
            self.client.candles(market, 60, settings.candles_limit_1h),
            self.client.candles(market, 15, settings.candles_limit_15m),
            self.client.candles(market, 240, settings.candles_limit_4h),
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

    def _resistance_room(self, df) -> float:
        current = float(df['close'].iloc[-1])
        recent_high = float(df['high'].tail(50).max())
        return round((recent_high / current - 1.0) * 100.0, 2)

    def _overheated(self, df, mode: str) -> bool:
        val = float(df['pct_from_20_low'].iloc[-1])
        threshold = settings.hot_move_exclude_pct_main if mode == 'main' else settings.hot_move_exclude_pct_sub
        return val >= threshold

    def _risk(self, current: float, fib: dict, room_pct: float) -> RiskPlan:
        invalidation = float(fib['fib_1'])
        stop_loss_pct = (invalidation / current - 1.0) * 100.0
        tp1_price = current * (1.0 + max(room_pct, 4.0) / 100.0)
        tp2_price = current * (1.0 + max(room_pct * 1.8, 8.0) / 100.0)
        tp1_pct = (tp1_price / current - 1.0) * 100.0
        tp2_pct = (tp2_price / current - 1.0) * 100.0
        stop_abs = abs(stop_loss_pct) if stop_loss_pct != 0 else 999.0
        rr1 = round(tp1_pct / stop_abs, 2)
        rr2 = round(tp2_pct / stop_abs, 2)
        return RiskPlan(
            entry_reference=round(current, 8),
            fib_0618=round(float(fib['fib_0618']), 8),
            fib_0786=round(float(fib['fib_0786']), 8),
            invalidation_price=round(invalidation, 8),
            invalidation_rule='fib_1_break',
            stop_loss_pct=round(stop_loss_pct, 2),
            tp1_price=round(tp1_price, 8),
            tp1_pct=round(tp1_pct, 2),
            tp2_price=round(tp2_price, 8),
            tp2_pct=round(tp2_pct, 2),
            rr_tp1=rr1,
            rr_tp2=rr2,
        )

    def _passes_filters(self, mode: str, current: float, fib: dict, zone: str, volume_ratio: float, overheated: bool, room_pct: float, risk: RiskPlan, div_kind: str) -> tuple[bool, list[str]]:
        rejected: list[str] = []
        fib_0618 = float(fib['fib_0618'])
        fib_0786 = float(fib['fib_0786'])
        upper = max(fib_0618, fib_0786)

        if mode == 'main' and div_kind != 'chain':
            rejected.append('main_requires_chain_divergence')
        if mode == 'main' and zone == 'out_zone':
            rejected.append('fib_zone_miss')
        if mode == 'sub' and zone == 'out_zone':
            rejected.append('fib_zone_far')

        late_entry_buffer = settings.late_entry_buffer_pct_main if mode == 'main' else settings.late_entry_buffer_pct_sub
        if current > upper * (1 + late_entry_buffer / 100.0):
            rejected.append('late_long_entry')

        min_volume_ratio = settings.min_volume_ratio_main if mode == 'main' else settings.min_volume_ratio_sub
        if volume_ratio < min_volume_ratio:
            rejected.append('weak_volume')

        if overheated:
            rejected.append('overheated_after_rally')

        min_room = settings.resistance_min_room_pct_main if mode == 'main' else settings.resistance_min_room_pct_sub
        if room_pct < min_room:
            rejected.append('too_close_to_resistance')

        min_rr = settings.min_rr_main if mode == 'main' else settings.min_rr_sub
        if risk.rr_tp2 < min_rr:
            rejected.append('rr_too_low')
        if risk.stop_loss_pct >= 0:
            rejected.append('invalid_stop_structure')
        return len(rejected) == 0, rejected

    def _state_for_mode(self, mode: str, passed: bool) -> str:
        if passed:
            return 'candidate'
        return 'watch' if mode == 'sub' else 'rejected'

    async def analyze_symbol(self, symbol: str, mode: str) -> ScanSignal | None:
        try:
            df1h, df15m, df4h = await self._frames(symbol)
            if min(len(df1h), len(df15m), len(df4h)) < 80:
                return None

            current = float(df1h['close'].iloc[-1])
            rsi1h = float(df1h['rsi'].iloc[-1])
            rsi15m = float(df15m['rsi'].iloc[-1])

            bull1h = detect_bullish(recent_pivot_lows(df1h), settings.pivot_min_gap, settings.pivot_max_gap, settings.min_chain_span)
            bull15m = detect_bullish(recent_pivot_lows(df15m), settings.pivot_min_gap, settings.pivot_max_gap, settings.min_chain_span)
            bull4h = detect_bullish(recent_pivot_lows(df4h), settings.pivot_min_gap, settings.pivot_max_gap, settings.min_chain_span)

            long_score = 0.0
            if bull1h['found']:
                long_score += 42 if bull1h['kind'] == 'chain' else 26
            if bull15m['found']:
                long_score += 10 if bull15m['kind'] == 'chain' else 6
            if bull4h['found']:
                long_score += 14 if bull4h['kind'] == 'chain' else 8
            if 22 <= rsi1h <= 45:
                long_score += 8

            if mode == 'main' and not bull1h['found']:
                return None
            if mode == 'sub' and not (bull1h['found'] or bull15m['found'] or bull4h['found']):
                return None

            div = bull1h if bull1h['found'] else (bull15m if bull15m['found'] else bull4h)
            fib = bullish_fib(df1h)
            fib_tolerance = settings.fib_tolerance_pct_main if mode == 'main' else settings.fib_tolerance_pct_sub
            zone = zone_status(current, fib['fib_0618'], fib['fib_0786'], fib_tolerance)
            if zone == 'in_zone':
                long_score += 16
            elif zone == 'near_zone':
                long_score += 8
            elif mode == 'sub':
                long_score += 2

            volume_ratio = self._volume_ratio(df1h)
            if volume_ratio >= 1.25:
                long_score += 8
            elif volume_ratio >= 1.05:
                long_score += 4
            elif mode == 'sub' and volume_ratio >= 0.92:
                long_score += 2

            room_pct = self._resistance_room(df1h)
            overheated = self._overheated(df1h, mode)
            risk = self._risk(current, fib, room_pct)
            passed, rejected = self._passes_filters(mode, current, fib, zone, volume_ratio, overheated, room_pct, risk, div['kind'])
            grade = compute_grade(long_score)

            reasons = [
                f'1h 상승 다이버전스 {bull1h["kind"] if bull1h["found"] else "none"}',
                f'피보나치 {zone}',
                f'거래량비 {volume_ratio}',
                f'손절 {risk.stop_loss_pct}%',
                f'1차익절 +{risk.tp1_pct}%',
                f'2차익절 +{risk.tp2_pct}%',
                '피보나치 1 이탈 시 무효',
            ]
            if bull15m['found']:
                reasons.append('15분 보조확인')
            if bull4h['found']:
                reasons.append('4시간 방향보조')
            if mode == 'sub' and rejected:
                reasons.append('서브 탐색후보')

            return ScanSignal(
                symbol=symbol,
                mode=mode,
                side='bullish',
                score=round(long_score, 2),
                grade=grade,
                state=self._state_for_mode(mode, passed),
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
        limit = settings.scan_market_limit_main if mode == 'main' else settings.scan_market_limit_sub
        markets = await self.client.top_markets(limit, mode=mode)
        tasks = [self.analyze_symbol(market, mode) for market in markets]
        analyzed = [x for x in await asyncio.gather(*tasks) if x is not None]
        analyzed.sort(key=lambda x: (x.filters_passed, x.score, x.risk.rr_tp2), reverse=True)
        passed = [x for x in analyzed if x.filters_passed]
        if mode == 'main':
            top_picks = passed[:settings.top_pick_count]
        else:
            top_picks = (passed[:settings.top_pick_count] or analyzed[:settings.top_pick_count])
        return ScanResponse(
            mode=mode,
            scanned_symbols=len(markets),
            matched_symbols=len(passed),
            elapsed_seconds=round(perf_counter() - started, 2),
            top_picks=top_picks,
            signals=analyzed[: max(settings.top_pick_count, 20)],
        )
