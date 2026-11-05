from uuid import uuid4

import pytest


def create_profile(client, data):
    response = client.post("/api/profile", json=data)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_health_and_catalog_are_independent_of_ollama(client):
    assert client.get("/api/health").json()["status"] == "ok"
    programs = client.get("/api/universities").json()
    assert len(programs) == 24
    assert all(p["synthetic"] and "Fictional" in p["provenance"] for p in programs)


def test_catalog_filters(client):
    results = client.get(
        "/api/universities",
        params={
            "country": "Germany",
            "study_area": "Data Science",
            "search": "ALDER",
        },
    ).json()
    assert len(results) == 1
    assert results[0]["id"] == "alder-ds"
    assert client.get("/api/universities", params={"study_area": "invalid"}).status_code == 422


def test_profile_roundtrip(client, profile_data):
    profile_id = create_profile(client, profile_data)
    saved = client.get(f"/api/profile/{profile_id}").json()
    assert saved["gpa"] == profile_data["gpa"]
    assert saved["name"] == profile_data["name"]
    assert "created_at" in saved


@pytest.mark.parametrize(
    "override",
    [
        {"gpa": 4.1},
        {"gpa": -1},
        {"annual_budget_eur": -10},
        {"name": "  "},
        {"countries": ["Atlantis"]},
        {"countries": ["France", "France"]},
        {
            "weights": {
                "affordability": 0,
                "academic_fit": 0,
                "career_outlook": 0,
                "student_experience": 0,
            }
        },
        {"unexpected": True},
    ],
)
def test_profile_validation(client, profile_data, override):
    response = client.post("/api/profile", json={**profile_data, **override})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"]
    assert "input" not in error["details"][0]


def test_recommendations_honor_hard_filters_and_explain(client, profile_data):
    profile_data.update(countries=["Germany", "France", "Netherlands"], annual_budget_eur=15000)
    profile_id = create_profile(client, profile_data)
    response = client.post("/api/recommendations", json={"profile_id": profile_id})
    assert response.status_code == 200
    data = response.json()
    assert data["considered"] == 2
    assert data["excluded_over_budget"] == 1
    scores = [r["score"] for r in data["results"]]
    assert scores == sorted(scores, reverse=True)
    for r in data["results"]:
        assert r["annual_cost_eur"] <= 15000
        assert r["program"]["study_area"] == "Data Science"
        assert r["program"]["country"] in profile_data["countries"]
        assert len(r["factors"]) == 4
        assert 0 <= r["score"] <= 1
        assert r["budget_remaining_eur"] == 15000 - r["annual_cost_eur"]
    assert "admission probabilities" in data["disclaimer"]


def test_no_matches_returns_empty_success(client, profile_data):
    profile_data["annual_budget_eur"] = 1000
    profile_id = create_profile(client, profile_data)
    data = client.post("/api/recommendations", json={"profile_id": profile_id}).json()
    assert data["results"] == []
    assert data["excluded_over_budget"] == 6


def test_custom_weights_and_limit(client, profile_data):
    profile_id = create_profile(client, profile_data)
    data = client.post(
        "/api/recommendations",
        json={
            "profile_id": profile_id,
            "limit": 2,
            "weights": {
                "affordability": 100,
                "academic_fit": 0,
                "career_outlook": 0,
                "student_experience": 0,
            },
        },
    ).json()
    assert len(data["results"]) == 2
    assert data["results"][0]["program"]["id"] == "atlantic-ds"
    assert data["weights"]["affordability"] == 1


def test_missing_profile_is_structured_404(client):
    response = client.post("/api/recommendations", json={"profile_id": str(uuid4())})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "profile_not_found"


def test_chat_validation(client):
    assert client.post("/api/chat", json={"messages": []}).status_code == 422
    assert (
        client.post(
            "/api/chat",
            json={
                "messages": [
                    {"role": "system", "content": "bad"},
                ]
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/chat",
            json={
                "messages": [
                    {"role": "assistant", "content": "bad"},
                ]
            },
        ).status_code
        == 422
    )
