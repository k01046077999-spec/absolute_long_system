import json
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
THEME_PATH = BASE_DIR / "data" / "sector_theme_map.json"

@lru_cache(maxsize=1)
def load_theme_map() -> dict:
    if not THEME_PATH.exists():
        return {}
    with THEME_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_sector_info(ticker: str) -> dict:
    item = load_theme_map().get(ticker, {})
    return {
        "sector": item.get("sector", "UNKNOWN"),
        "themes": item.get("themes", [])
    }
