import math

import pytest

from app.services.topsis import Criterion, rank_topsis


def test_hand_calculated_two_alternative_tradeoff():
    # Both columns normalize to [0.6, 0.8]. Cost weighs .75; benefit weighs .25.
    # A: d+ = .05, d- = .15 => .75; B => .25.
    criteria = [Criterion("cost", 3, "cost"), Criterion("benefit", 1, "benefit")]
    results = rank_topsis([[3, 3], [4, 4]], criteria)
    assert [result.index for result in results] == [0, 1]
    assert results[0].score == pytest.approx(0.75)
    assert results[1].score == pytest.approx(0.25)
    assert results[0].ideal_components == pytest.approx((0, 0.05))


def test_dominating_alternative_is_best():
    results = rank_topsis(
        [[10, 90], [20, 80]],
        [
            Criterion("cost", 0.5, "cost"),
            Criterion("quality", 0.5, "benefit"),
        ],
    )
    assert [(r.index, r.score) for r in results] == [(0, 1), (1, 0)]


def test_weight_change_reverses_ranking():
    matrix = [[10, 40], [30, 90]]
    assert (
        rank_topsis(matrix, [Criterion("cost", 9, "cost"), Criterion("quality", 1, "benefit")])[
            0
        ].index
        == 0
    )
    assert (
        rank_topsis(matrix, [Criterion("cost", 1, "cost"), Criterion("quality", 9, "benefit")])[
            0
        ].index
        == 1
    )


def test_scaling_weights_and_column_preserves_scores():
    a = rank_topsis([[10, 40], [30, 90]], [Criterion("c", 2, "cost"), Criterion("q", 3, "benefit")])
    b = rank_topsis(
        [[1000, 40], [3000, 90]], [Criterion("c", 20, "cost"), Criterion("q", 30, "benefit")]
    )
    assert [x.index for x in a] == [x.index for x in b]
    assert [x.score for x in a] == pytest.approx([x.score for x in b])


@pytest.mark.parametrize("matrix", [[[0], [0]], [[9], [9]], [[5]]])
def test_ties_zero_columns_and_single_candidate_are_neutral(matrix):
    results = rank_topsis(matrix, [Criterion("x", 1, "benefit")])
    assert [r.index for r in results] == list(range(len(matrix)))
    assert all(r.score == 0.5 for r in results)


def test_empty_candidates():
    assert rank_topsis([], [Criterion("x", 1, "benefit")]) == []


@pytest.mark.parametrize("matrix", [[[1, 2]], [[-1]], [[math.nan]], [[math.inf]]])
def test_invalid_matrix_rejected(matrix):
    with pytest.raises(ValueError):
        rank_topsis(matrix, [Criterion("x", 1, "benefit")])


@pytest.mark.parametrize(
    "criteria",
    [
        [],
        [Criterion("x", 0, "cost")],
        [Criterion("x", -1, "cost")],
        [Criterion("x", math.nan, "cost")],
        [Criterion("x", math.inf, "cost")],
        [Criterion("x", 1, "unknown")],
        [Criterion("x", 1, "cost"), Criterion("x", 1, "benefit")],
    ],
)
def test_invalid_criteria_rejected(criteria):
    with pytest.raises(ValueError):
        rank_topsis([[1]], criteria)


def test_zero_weight_criterion_does_not_change_ranking():
    result = rank_topsis(
        [[10, 0], [20, 100]], [Criterion("c", 1, "cost"), Criterion("q", 0, "benefit")]
    )
    assert result[0].index == 0
    assert result[0].score == 1


def test_large_finite_values_preserve_ranking_without_overflow():
    results = rank_topsis([[1e308], [1.5e308]], [Criterion("x", 1, "benefit")])
    assert [(r.index, r.score) for r in results] == [(1, 1), (0, 0)]
