from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = '완전무결매매법 코인 검색기'
    app_version: str = '2.0.0'
    binance_base_url: str = 'https://api.binance.com'

    rsi_period: int = 14
    pivot_left: int = 3
    pivot_right: int = 3
    pivot_min_gap: int = 5
    pivot_max_gap: int = 80
    min_chain_span: int = 12

    scan_symbol_limit_main: int = 60
    scan_symbol_limit_sub: int = 120
    klines_limit_1h: int = 250
    klines_limit_15m: int = 220
    klines_limit_4h: int = 220
    top_pick_count: int = 8

    fib_tolerance_pct: float = 1.5
    late_entry_buffer_pct: float = 2.5
    min_volume_ratio: float = 1.05
    hot_move_exclude_pct: float = 35.0
    resistance_min_room_pct: float = 4.0
    min_rr_main: float = 1.5
    min_rr_sub: float = 1.0

    max_notional_rank: int = 160
    min_daily_quote_volume_usdt: float = 8_000_000
    exclude_symbols: str = 'USDCUSDT,FDUSDUSDT,TUSDUSDT,USDPUSDT,EURUSDT,AEURUSDT,BUSDUSDT'


settings = Settings()
