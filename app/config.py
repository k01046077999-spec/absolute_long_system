import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    scan_market: str = os.getenv("SCAN_MARKET", "ALL")
    scan_limit: int = int(os.getenv("SCAN_LIMIT", "250"))
    min_avg_trading_value: int = int(os.getenv("MIN_AVG_TRADING_VALUE", "2000000000"))
    target_return: float = float(os.getenv("TARGET_RETURN", "0.10"))
    ohlcv_days: int = int(os.getenv("OHLCV_DAYS", "320"))
    dart_api_key: str = os.getenv("DART_API_KEY", "")

settings = Settings()
