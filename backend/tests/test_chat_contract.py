from app.core.config import Settings
from app.services.ollama import get_ollama_service


def test_chat_rejects_oversized_user_messages(client):
    response = client.post(
        "/api/chat",
        json={
            "messages": [{"role": "user", "content": "x" * 4001}],
        },
    )
    assert response.status_code == 422


def test_chat_response_and_profile_context(client, profile_data):
    class WorkingService:
        settings = Settings()

        async def chat(self, messages, profile, catalog):
            assert profile.name == "Sam"
            assert messages[-1].content == "Help me compare"
            assert len(catalog) == 6
            assert all(p["synthetic"] for p in catalog)
            return "A" * 5000

    client.app.dependency_overrides[get_ollama_service] = lambda: WorkingService()
    profile_id = client.post("/api/profile", json=profile_data).json()["id"]
    response = client.post(
        "/api/chat",
        json={
            "messages": [{"role": "user", "content": "Help me compare"}],
            "profile_id": profile_id,
        },
    )
    assert response.status_code == 200
    assert len(response.json()["message"]["content"]) == 5000
    assert response.json()["synthetic_context"] is True
