from __future__ import annotations


def compute_grade(score: float) -> str:
    if score >= 85:
        return 'S'
    if score >= 72:
        return 'A'
    if score >= 60:
        return 'B'
    if score >= 48:
        return 'C'
    return 'D'
