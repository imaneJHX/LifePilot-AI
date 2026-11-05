"""Vector-normalized TOPSIS with explicit benefit/cost criteria; no ML dependencies."""

from dataclasses import dataclass
from math import hypot, isfinite
from typing import Literal


@dataclass(frozen=True)
class Criterion:
    name: str
    weight: float
    kind: Literal["benefit", "cost"]


@dataclass(frozen=True)
class TopsisResult:
    index: int
    score: float
    ideal_components: tuple[float, ...]
    anti_ideal_components: tuple[float, ...]


def rank_topsis(matrix: list[list[float]], criteria: list[Criterion]) -> list[TopsisResult]:
    if not criteria or len({item.name for item in criteria}) != len(criteria):
        raise ValueError("Criteria must be nonempty and uniquely named.")
    if any(
        not isfinite(item.weight) or item.weight < 0 or item.kind not in ("benefit", "cost")
        for item in criteria
    ):
        raise ValueError("Weights must be finite and nonnegative; kinds must be benefit or cost.")
    total_weight = sum(item.weight for item in criteria)
    if not isfinite(total_weight) or total_weight <= 0:
        raise ValueError("Weights must have a finite positive sum.")
    # Divide first: multiplying by raw subnormal weights can underflow before
    # division by their sum restores the intended criterion proportions.
    normalized_weights = [item.weight / total_weight for item in criteria]
    if any(
        len(row) != len(criteria) or any(not isfinite(x) or x < 0 for x in row) for row in matrix
    ):
        raise ValueError("Every row must contain one finite, nonnegative value per criterion.")
    if not matrix:
        return []
    # Scaling each column first preserves vector normalization and avoids overflow
    # when finite input values have an unrepresentable Euclidean norm.
    scales = [max(row[j] for row in matrix) for j in range(len(criteria))]
    scaled = [
        [value / scales[j] if scales[j] else 0 for j, value in enumerate(row)] for row in matrix
    ]
    norms = [hypot(*(row[j] for row in scaled)) for j in range(len(criteria))]
    normalized = [
        [
            (row[j] / norms[j] if norms[j] else 0) * weight
            for j, weight in enumerate(normalized_weights)
        ]
        for row in scaled
    ]
    ideal, anti_ideal = [], []
    for j, criterion in enumerate(criteria):
        values = [row[j] for row in normalized]
        best, worst = max(values), min(values)
        ideal.append(best if criterion.kind == "benefit" else worst)
        anti_ideal.append(worst if criterion.kind == "benefit" else best)
    results = []
    for i, row in enumerate(normalized):
        positive = tuple(abs(x - y) for x, y in zip(row, ideal, strict=True))
        negative = tuple(abs(x - y) for x, y in zip(row, anti_ideal, strict=True))
        d_positive, d_negative = hypot(*positive), hypot(*negative)
        distance = d_positive + d_negative
        results.append(
            TopsisResult(i, d_negative / distance if distance else 0.5, positive, negative)
        )
    # Stable input order resolves ties. Identical/single alternatives receive 0.5.
    return sorted(results, key=lambda result: -result.score)
