"""Independent TOPSIS audit checks and numerical stability regressions."""

import math
from decimal import Decimal, localcontext

import pytest
from pydantic import ValidationError

from app.repositories.catalog import get_catalog
from app.schemas.contracts import ProfileInput, Program, Weights
from app.services.recommendations import recommend
from app.services.topsis import Criterion, rank_topsis


def decimal_reference(matrix, weights, kinds):
    """Direct, 60-digit TOPSIS oracle without the production scaling strategy."""
    with localcontext() as context:
        context.prec = 60
        values = [[Decimal(str(value)) for value in row] for row in matrix]
        priorities = [Decimal(str(weight)) for weight in weights]
        priorities = [weight / sum(priorities) for weight in priorities]
        lengths = [sum(row[j] ** 2 for row in values).sqrt() for j in range(len(priorities))]
        weighted = [
            [
                value / lengths[j] * priorities[j] if lengths[j] else Decimal(0)
                for j, value in enumerate(row)
            ]
            for row in values
        ]
        best = [
            (min if kind == "cost" else max)(row[j] for row in weighted)
            for j, kind in enumerate(kinds)
        ]
        worst = [
            (max if kind == "cost" else min)(row[j] for row in weighted)
            for j, kind in enumerate(kinds)
        ]
        scores = []
        for row in weighted:
            positive = sum((value - best[j]) ** 2 for j, value in enumerate(row)).sqrt()
            negative = sum((value - worst[j]) ** 2 for j, value in enumerate(row)).sqrt()
            scores.append(float(negative / (positive + negative)) if positive + negative else 0.5)
        return scores


@pytest.fixture
def reference_profile():
    # Fixed synthetic-catalog regression scenario; no student records or live DB dependency.
    return ProfileInput(
        name="Regression example",
        study_area="Data Science",
        gpa=3.5,
        annual_budget_eur=25000,
        countries=["Germany", "Netherlands"],
        weights=Weights(
            affordability=71, academic_fit=30, career_outlook=20, student_experience=15
        ),
    )


def test_independent_three_alternative_hand_calculation():
    # Column lengths = 5; normalized weights = (3/4, 1/4).
    # Weighted rows = (.45, .20), (.60, .15), (0, 0).
    # Ideal = (0, .20); worst = (.60, 0).
    # Distances: A=(9/20,5/20), B=(sqrt(145)/20,3/20), C=(4/20,12/20).
    results = rank_topsis(
        [[3, 4], [4, 3], [0, 0]],
        [Criterion("cost", 3, "cost"), Criterion("quality", 1, "benefit")],
    )
    assert [result.index for result in results] == [2, 0, 1]
    expected = {0: 5 / 14, 1: 3 / (math.sqrt(145) + 3), 2: 3 / 4}
    for result in results:
        assert result.score == pytest.approx(expected[result.index], abs=1e-14)
    assert results[1].ideal_components == pytest.approx((0.45, 0))
    assert results[1].anti_ideal_components == pytest.approx((0.15, 0.20))


def test_identical_multicriterion_alternatives_have_no_distance_and_stable_ties():
    criteria = [
        Criterion("cost", 71, "cost"),
        Criterion("alignment", 30, "benefit"),
        Criterion("career", 20, "benefit"),
        Criterion("experience", 15, "benefit"),
    ]
    results = rank_topsis([[0, 95, 86, 79]] * 3, criteria)
    assert [result.index for result in results] == [0, 1, 2]
    for result in results:
        assert result.score == 0.5
        assert result.ideal_components == (0, 0, 0, 0)
        assert result.anti_ideal_components == (0, 0, 0, 0)


@pytest.mark.parametrize("row", [[0, 0], [14000, 95], [1.7e308, 5e-324]])
def test_single_alternative_is_neutral_for_mixed_criteria(row):
    result = rank_topsis([row], [Criterion("cost", 3, "cost"), Criterion("quality", 1, "benefit")])[
        0
    ]
    assert result.index == 0
    assert result.score == 0.5
    assert result.ideal_components == result.anti_ideal_components == (0, 0)


@pytest.mark.parametrize("kind", ["benefit", "cost"])
@pytest.mark.parametrize("values", [[0, 1e308, 1.7e308], [5e-324, 1e-323, 1.5e-323]])
def test_extreme_columns_match_independent_single_criterion_ratios(kind, values):
    results = rank_topsis([[value] for value in values], [Criterion("x", 1, kind)])
    # For one varying criterion, closeness is the position between min and max.
    with localcontext() as context:
        context.prec = 60
        exact = [Decimal.from_float(value) for value in values]
        expected = [(value - min(exact)) / (max(exact) - min(exact)) for value in exact]
        if kind == "cost":
            expected = [1 - score for score in expected]
    for result in results:
        assert math.isfinite(result.score)
        assert result.score == pytest.approx(float(expected[result.index]), abs=1e-14)


@pytest.mark.parametrize(
    "weights",
    [
        (1, 0),
        (0, 1),
        (1, 1),
        (9, 1),
        (1, 9),
        (35, 30),
        (5e-324, 5e-324),
        (5e-324, 1e-323),
        (1e-323, 1.5e-323),
    ],
)
def test_weight_configurations_match_independent_decimal_reference(weights):
    matrix = [[3, 4], [4, 3], [0, 0]]
    expected = decimal_reference(matrix, weights, ["cost", "benefit"])
    results = rank_topsis(
        matrix,
        [Criterion("cost", weights[0], "cost"), Criterion("quality", weights[1], "benefit")],
    )
    assert [result.index for result in results] == sorted(range(3), key=lambda i: -expected[i])
    for result in results:
        assert result.score == pytest.approx(expected[result.index], abs=1e-14)


def test_reference_dashboard_score_and_distance_components(reference_profile):
    response = recommend(reference_profile, get_catalog(), reference_profile.weights, 6)
    assert (response.considered, response.excluded_preferences, response.excluded_over_budget) == (
        2,
        22,
        0,
    )
    assert [result.program.id for result in response.results] == ["alder-ds", "canal-ds"]
    expected = decimal_reference(
        [[14000, 95, 86, 79], [25000, 92, 93, 92]],
        [71, 30, 20, 15],
        ["cost", "benefit", "benefit", "benefit"],
    )
    assert [result.score for result in response.results] == pytest.approx(expected, abs=1e-14)
    best = response.results[0]
    assert best.score == pytest.approx(0.9332145171603622, abs=1e-14)
    assert f"{best.score * 100:.1f}" == "93.3"
    assert best.annual_cost_eur == 14000
    assert best.budget_remaining_eur == 11000
    assert [factor.value for factor in sorted(best.factors, key=lambda f: f.criterion)] == [
        95,
        14000,
        86,
        79,
    ]
    assert math.hypot(*(f.ideal_distance_component for f in best.factors)) == pytest.approx(
        0.014347507374520281, abs=1e-14
    )
    assert math.hypot(*(f.anti_ideal_distance_component for f in best.factors)) == pytest.approx(
        0.2004822245444785, abs=1e-14
    )
    assert sum(response.weights.values()) == pytest.approx(1)


@pytest.mark.parametrize(
    ("budget", "ids", "excluded"),
    [
        (13999, [], 2),
        (14000, ["alder-ds"], 1),
        (24999, ["alder-ds"], 1),
        (25000, ["alder-ds", "canal-ds"], 0),
    ],
)
def test_real_catalog_budget_boundaries(reference_profile, budget, ids, excluded):
    profile = reference_profile.model_copy(update={"annual_budget_eur": budget})
    response = recommend(profile, get_catalog(), profile.weights, 6)
    assert [result.program.id for result in response.results] == ids
    assert response.excluded_over_budget == excluded
    assert response.considered + excluded + response.excluded_preferences == len(get_catalog())
    assert all(result.annual_cost_eur <= budget for result in response.results)
    if len(ids) == 1:
        assert response.results[0].score == 0.5


def test_over_budget_dominant_program_is_removed_before_normalization(reference_profile):
    catalog = get_catalog()
    baseline = recommend(reference_profile, catalog, reference_profile.weights, 6)
    data = catalog[0].model_dump()
    data.update(
        id="audit-over-budget",
        study_area="Data Science",
        tuition_eur=25001,
        living_cost_eur=0,
        academic_index=95,
        career_index=100,
        experience_index=100,
    )
    expensive = Program.model_validate(data)
    response = recommend(reference_profile, (*catalog, expensive), reference_profile.weights, 6)
    assert response.results == baseline.results
    assert response.considered == baseline.considered
    assert response.excluded_over_budget == baseline.excluded_over_budget + 1


def test_result_limit_does_not_change_candidate_set_or_scores(reference_profile):
    full = recommend(reference_profile, get_catalog(), reference_profile.weights, 6)
    limited = recommend(reference_profile, get_catalog(), reference_profile.weights, 1)
    assert limited.considered == full.considered == 2
    assert limited.results == full.results[:1]


def test_api_weight_override_is_temporary_and_reproduces_both_scores(client, reference_profile):
    created = client.post("/api/profile", json=reference_profile.model_dump(mode="json"))
    assert created.status_code == 201
    profile_id = created.json()["id"]
    stored = client.post("/api/recommendations", json={"profile_id": profile_id})
    override = client.post(
        "/api/recommendations",
        json={"profile_id": profile_id, "weights": Weights().model_dump()},
    )
    assert stored.status_code == override.status_code == 200
    assert stored.json()["results"][0]["score"] == pytest.approx(0.9332145171603622)
    assert override.json()["results"][0]["score"] == pytest.approx(0.8733364995217769)
    restored = client.get(f"/api/profile/{profile_id}")
    assert restored.status_code == 200
    assert restored.json()["weights"] == reference_profile.weights.model_dump()


@pytest.mark.parametrize("criterion", list(Weights.model_fields))
@pytest.mark.parametrize("multiplier", [0.99, 1.01])
def test_reference_profile_ranking_is_stable_under_one_percent_weight_changes(
    reference_profile, criterion, multiplier
):
    priorities = reference_profile.weights.model_dump()
    priorities[criterion] *= multiplier
    response = recommend(reference_profile, get_catalog(), Weights(**priorities), 6)
    assert [result.program.id for result in response.results] == ["alder-ds", "canal-ds"]
    assert abs(response.results[0].score - 0.9332145171603622) < 0.001


@pytest.mark.parametrize(("weights", "winner"), [((0.501, 0.499), 0), ((0.499, 0.501), 1)])
def test_small_changes_can_reverse_a_near_tie(weights, winner):
    # Stability is a property of the decision margin, not a global TOPSIS guarantee.
    results = rank_topsis(
        [[3, 3], [4, 4]],
        [Criterion("cost", weights[0], "cost"), Criterion("quality", weights[1], "benefit")],
    )
    assert results[0].index == winner
    assert results[0].score == pytest.approx(0.501)


@pytest.mark.parametrize("field", ["academic_index", "career_index", "experience_index"])
@pytest.mark.parametrize("invalid", [None, math.nan, math.inf])
def test_missing_or_nonfinite_program_indices_are_rejected(field, invalid):
    data = get_catalog()[0].model_dump()
    data[field] = invalid
    with pytest.raises(ValidationError):
        Program.model_validate(data)


def test_absent_required_criterion_is_rejected():
    data = get_catalog()[0].model_dump()
    del data["career_index"]
    with pytest.raises(ValidationError):
        Program.model_validate(data)


def test_subnormal_common_weight_scaling_should_preserve_scores():
    results = rank_topsis([[1], [2], [3]], [Criterion("benefit", 5e-324, "benefit")])
    assert [result.index for result in results] == [2, 1, 0]
    assert [result.score for result in results] == pytest.approx([1, 0.5, 0])


def test_api_subnormal_weights_should_match_equivalent_unit_weights(client, reference_profile):
    data = reference_profile.model_dump(mode="json")
    data["countries"] = []
    created = client.post("/api/profile", json=data)
    assert created.status_code == 201
    request = {
        "profile_id": created.json()["id"],
        "weights": {
            "affordability": 1,
            "academic_fit": 0,
            "career_outlook": 0,
            "student_experience": 0,
        },
    }
    ordinary = client.post("/api/recommendations", json=request)
    assert ordinary.status_code == 200
    request["weights"]["affordability"] = 5e-324
    tiny = client.post("/api/recommendations", json=request)
    assert tiny.status_code == 200
    assert tiny.json()["weights"] == ordinary.json()["weights"]
    assert [row["program"]["id"] for row in tiny.json()["results"]] == [
        row["program"]["id"] for row in ordinary.json()["results"]
    ]
    assert [row["score"] for row in tiny.json()["results"]] == pytest.approx(
        [row["score"] for row in ordinary.json()["results"]], abs=1e-14
    )
