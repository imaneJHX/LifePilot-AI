import asyncio

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.schemas.contracts import ChatMessage
from app.services.ollama import OllamaService, get_ollama_service


def run_chat(handler):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await OllamaService(Settings(), client).chat(
                [ChatMessage(role="user", content="Help me compare")], None, []
            )

    return asyncio.run(run())


def test_chat_success_and_payload():
    def handler(request):
        import json

        body = json.loads(request.content)
        assert body["stream"] is False
        assert "SYNTHETIC" in body["messages"][0]["content"]
        assert body["messages"][-1]["role"] == "user"
        return httpx.Response(200, json={"message": {"content": "Compare annual costs."}})

    assert run_chat(handler) == "Compare annual costs."


@pytest.mark.parametrize(
    "status,body,code",
    [
        (404, {"error": "missing model"}, "ollama_model_missing"),
        (500, {"error": "crash"}, "ollama_error"),
        (200, {"message": {}}, "ollama_invalid_response"),
        (200, {"message": {"content": ""}}, "ollama_invalid_response"),
        (200, {"message": {"content": 123}}, "ollama_invalid_response"),
    ],
)
def test_model_and_upstream_errors(status, body, code):
    with pytest.raises(AppError) as error:
        run_chat(lambda request: httpx.Response(status, json=body))
    assert error.value.code == code


@pytest.mark.parametrize(
    "exception,code",
    [
        (httpx.ConnectError, "ollama_unavailable"),
        (httpx.ReadTimeout, "ollama_timeout"),
    ],
)
def test_network_errors(exception, code):
    def handler(request):
        raise exception("unavailable", request=request)

    with pytest.raises(AppError) as error:
        run_chat(handler)
    assert error.value.code == code


def test_chat_endpoint_failure_does_not_break_ranking(client, profile_data):
    class OfflineService:
        async def chat(self, *args):
            raise AppError("ollama_unavailable", "Ollama is offline", 503)

    client.app.dependency_overrides[get_ollama_service] = lambda: OfflineService()
    response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Hi"}]})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ollama_unavailable"
    profile_id = client.post("/api/profile", json=profile_data).json()["id"]
    assert client.post("/api/recommendations", json={"profile_id": profile_id}).status_code == 200
    assert client.get("/api/health").status_code == 200
