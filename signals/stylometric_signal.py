import re


def _sentence_lengths(text: str) -> list[int]:
    sentences = re.split(r'[.!?]+', text)
    return [len(s.split()) for s in sentences if s.strip()]


def _variance_score(lengths: list[int]) -> float:
    """Low sentence-length variance → AI. Normalized against a 15-word std-dev ceiling."""
    if len(lengths) < 2:
        return 0.5  # not enough sentences to measure, stay neutral
    mean = sum(lengths) / len(lengths)
    std_dev = (sum((x - mean) ** 2 for x in lengths) / len(lengths)) ** 0.5
    return max(0.0, 1.0 - min(std_dev / 15.0, 1.0))


def _ttr_score(text: str) -> float:
    """Low type-token ratio → AI (repetitive vocabulary). Score = 1 - TTR."""
    words = text.lower().split()
    if not words:
        return 0.5
    ttr = len(set(words)) / len(words)
    return max(0.0, 1.0 - ttr)


def _punct_density_score(text: str) -> float:
    """Low punctuation density → AI (too clean). Normalizes against an 8% human baseline."""
    if not text:
        return 0.5
    punct = set('.,;:!?—–-\'"()[]{}')
    density = sum(1 for c in text if c in punct) / len(text)
    return max(0.0, 1.0 - min(density / 0.08, 1.0))


def get_stylometric_score(text: str) -> float:
    """
    Combines three heuristics into one AI-probability score (0.0–1.0).
    Each sub-score is weighted equally; higher = more AI-like.
    """
    lengths = _sentence_lengths(text)
    sub_scores = [
        _variance_score(lengths),
        _ttr_score(text),
        _punct_density_score(text),
    ]
    return round(sum(sub_scores) / len(sub_scores), 4)
