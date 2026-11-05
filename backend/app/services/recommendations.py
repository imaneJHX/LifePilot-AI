from app.schemas.contracts import (
    Factor,
    ProfileInput,
    Program,
    RankedProgram,
    RecommendationResponse,
    Weights,
)
from app.services.topsis import Criterion, rank_topsis

DISCLAIMER = (
    "All institutions, programs, costs and indices are synthetic demonstration data. "
    "TOPSIS scores are relative decision-ranking scores, never admission probabilities. "
    "Verify actual costs and requirements with official institutions before making decisions."
)
LABELS = ("Annual cost", "Academic alignment", "Career outlook", "Student experience")


def recommend(
    profile: ProfileInput, catalog: tuple[Program, ...], weights: Weights, limit: int
) -> RecommendationResponse:
    priorities = weights.model_dump()
    total = sum(priorities.values())
    normalized_weights = {key: value / total for key, value in priorities.items()}
    preferred = [
        p
        for p in catalog
        if p.study_area == profile.study_area
        and (not profile.countries or p.country in profile.countries)
    ]
    eligible = [p for p in preferred if p.annual_cost <= profile.annual_budget_eur]
    # GPA is a smooth illustrative curriculum-alignment signal, not an entry requirement.
    # The desired academic intensity grows from 60 to 100 with the supplied GPA.
    target = 60 + 10 * profile.gpa
    matrix = [
        [
            float(p.annual_cost),
            max(0, 100 - abs(p.academic_index - target)),
            p.career_index,
            p.experience_index,
        ]
        for p in eligible
    ]
    criteria = [
        Criterion(key, value, "cost" if key == "affordability" else "benefit")
        for key, value in priorities.items()
    ]
    ranking = rank_topsis(matrix, criteria)
    results = []
    for position, ranked in enumerate(ranking[:limit], start=1):
        program = eligible[ranked.index]
        factors = []
        for j, (key, label) in enumerate(zip(priorities, LABELS, strict=True)):
            value = matrix[ranked.index][j]
            explanations = [
                f"EUR {program.annual_cost:,}/year including living costs; "
                f"EUR {profile.annual_budget_eur - program.annual_cost:,} below your cap.",
                f"{value:.1f}/100 illustrative alignment with your GPA-derived intensity "
                f"target ({target:.0f}/100); this does not measure eligibility.",
                f"{program.career_index:.0f}/100 synthetic career index; not employment data.",
                f"{program.experience_index:.0f}/100 synthetic student-experience index.",
            ]
            factors.append(
                Factor(
                    criterion=key,
                    label=label,
                    value=value,
                    weight=normalized_weights[key],
                    ideal_distance_component=ranked.ideal_components[j],
                    anti_ideal_distance_component=ranked.anti_ideal_components[j],
                    explanation=explanations[j],
                )
            )
        # Explain weighted criteria closest to the ideal first; expose all distance components.
        factors.sort(
            key=lambda f: f.anti_ideal_distance_component - f.ideal_distance_component,
            reverse=True,
        )
        results.append(
            RankedProgram(
                rank=position,
                program=program,
                score=ranked.score,
                annual_cost_eur=program.annual_cost,
                budget_remaining_eur=profile.annual_budget_eur - program.annual_cost,
                factors=factors,
            )
        )
    return RecommendationResponse(
        results=results,
        considered=len(eligible),
        excluded_over_budget=len(preferred) - len(eligible),
        excluded_preferences=len(catalog) - len(preferred),
        weights=normalized_weights,
        methodology=(
            "Hard filters: study area, selected countries, annual tuition + living budget. "
            "TOPSIS: vector normalization, normalized priority weights, cost/benefit ideals, "
            "Euclidean distances, score = distance from worst / sum of distances. "
            "Scores depend on the candidate set; ties preserve catalog order. "
            "Identical or single alternatives score 0.5. Goals are assistant context only."
        ),
        disclaimer=DISCLAIMER,
    )
