from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = '완전무결매매법 코인 검색기'
    app_version: str = '2.2.1-upbit-long-render-safe'
    upbit_base_url: str = 'https://api.upbit.com'

    rsi_period: int = 14
    pivot_left: int = 3
    pivot_right: int = 3
    pivot_min_gap: int = 5
    pivot_max_gap: int = 80
    min_chain_span: int = 12

    scan_market_limit_main: int = 60
    scan_market_limit_sub: int = 140
    candles_limit_1h: int = 250
    candles_limit_15m: int = 220
    candles_limit_4h: int = 220
    top_pick_count: int = 8

    fib_tolerance_pct_main: float = 1.5
    fib_tolerance_pct_sub: float = 3.0
    late_entry_buffer_pct_main: float = 2.5
    late_entry_buffer_pct_sub: float = 5.0
    min_volume_ratio_main: float = 1.05
    min_volume_ratio_sub: float = 0.92
    hot_move_exclude_pct_main: float = 35.0
    hot_move_exclude_pct_sub: float = 50.0
    resistance_min_room_pct_main: float = 4.0
    resistance_min_room_pct_sub: float = 2.0
    min_rr_main: float = 1.5
    min_rr_sub: float = 0.75

    min_daily_acc_trade_price_krw_main: float = 3_000_000_000
    min_daily_acc_trade_price_krw_sub: float = 1_000_000_000
    exclude_markets: str = ''


settings = Settings()
