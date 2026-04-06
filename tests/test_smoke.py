from app.indicators import rsi


def test_rsi_length():
    closes = [float(i) for i in range(1, 40)]
    values = rsi(closes, 14)
    assert len(values) == len(closes)
    assert values[-1] is not None
