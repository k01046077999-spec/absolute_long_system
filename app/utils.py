from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd


def to_builtin(obj: Any) -> Any:
    """Convert pandas/numpy objects into JSON-safe Python primitives."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        return obj
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        val = float(obj)
        return None if math.isnan(val) or math.isinf(val) else val
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (datetime, date, pd.Timestamp)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): to_builtin(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_builtin(v) for v in obj]
    return str(obj)
