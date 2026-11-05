import pytest


@pytest.mark.parametrize("path", ["/api/health", "/api/universities", "/api/not-found"])
def test_api_responses_are_not_cacheable(client, path):
    response = client.get(path)
    assert response.headers["cache-control"] == "no-store"


def test_profile_and_validation_responses_are_not_cacheable(client, profile_data):
    created = client.post("/api/profile", json=profile_data)
    assert created.status_code == 201
    assert created.headers["cache-control"] == "no-store"
    restored = client.get(f"/api/profile/{created.json()['id']}")
    assert restored.status_code == 200
    assert restored.headers["cache-control"] == "no-store"
    invalid = client.post("/api/chat", json={})
    assert invalid.status_code == 422
    assert invalid.headers["cache-control"] == "no-store"
