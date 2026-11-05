import pytest


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/api/health", "GET"),
        ("/api/universities", "GET"),
        ("/api/real-programs", "GET"),
        ("/api/profile", "POST"),
        ("/api/profile/00000000-0000-0000-0000-000000000000", "GET"),
        ("/api/recommendations", "POST"),
        ("/api/chat", "POST"),
    ],
)
def test_android_preflight_allows_api_requests(client, path, method):
    response = client.options(
        path,
        headers={
            "Origin": "https://localhost",
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://localhost"


def test_android_can_read_api_responses(client):
    response = client.get("/api/health", headers={"Origin": "https://localhost"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://localhost"


def test_cors_does_not_allow_arbitrary_origins(client):
    response = client.options(
        "/api/profile",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
