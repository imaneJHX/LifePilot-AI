import hashlib
import json
from datetime import UTC, datetime

import httpx
import pytest

from app.core.config import Settings
from app.schemas.real_programs import SourceSeed
from app.services.llama_extraction import LlamaExtractor
from app.services.ollama_diagnostics import diagnose_ollama
from app.services.real_program_extraction import extract_program
from app.services.university_retrieval import RetrievedPage


def mock_settings():
    # Unit tests must not inherit a developer's model tag or server URL.
    return Settings(
        _env_file=None,
        ollama_model="llama3.2:3b",
        ollama_base_url="http://ollama.test",
    )


@pytest.fixture
def page():
    text = (
        "Computer Science – TU Darmstadt Master of Science; language: English "
        "General Information & Application Semesters 4 Language English C1 . "
        "Admission requirements A degree. Admission procedure Entrance exam may be needed. "
        "Application Online application Tuition for this programme: 500 EUR per semester."
    )
    return RetrievedPage(
        "https://official.example.edu/program",
        datetime.now(UTC),
        hashlib.sha256(text.encode()).hexdigest(),
        text,
        "page.html",
    )


@pytest.fixture
def program(page):
    return extract_program(
        page,
        SourceSeed(
            program_url=page.url,
            discovery_url="https://official.example.edu/masters",
            country="Germany",
            focus="Computer Science",
            adapter="tu_darmstadt",
        ),
    )


def test_diagnostic_lists_models_sends_prompt_and_measures_response():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "llama3.2:3b"}]})
        payload = json.loads(request.content)
        assert payload["model"] == "llama3.2:3b"
        assert payload["stream"] is False
        return httpx.Response(200, json={"message": {"content": "LifePilot diagnostic OK"}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = diagnose_ollama(mock_settings(), client)
    assert calls == ["/api/tags", "/api/chat"]
    assert report.reachable and report.model_available
    assert report.response == "LifePilot diagnostic OK"
    assert report.response_seconds >= 0
    assert report.total_seconds >= report.response_seconds
    assert report.error is None


def test_missing_model_prints_manual_install_instructions_without_download():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json={"models": [{"name": "other:latest"}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = diagnose_ollama(mock_settings(), client)
    assert calls == ["/api/tags"]
    assert report.reachable and not report.model_available
    assert report.response is None
    assert "ollama pull llama3.2:3b" in " ".join(report.instructions)


@pytest.mark.parametrize("error", [httpx.ConnectError, httpx.ReadTimeout])
def test_diagnostic_connection_and_timeout_errors_are_useful(error):
    def handler(request):
        raise error("offline", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = diagnose_ollama(mock_settings(), client)
    assert report.error
    assert report.response is None
    assert report.total_seconds >= 0


@pytest.mark.parametrize(
    "status,body",
    [
        (500, {}),
        (404, {}),
        (200, {}),
        (200, {"models": "not a list"}),
        (200, {"models": [{"name": 10}]}),
    ],
)
def test_diagnostic_rejects_upstream_errors_and_malformed_tags(status, body):
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(status, json=body))
    ) as c:
        report = diagnose_ollama(mock_settings(), c)
    assert report.error
    assert report.response is None


def test_diagnostic_bad_inference_payload_keeps_installed_model_information():
    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "llama3.2:3b"}]})
        return httpx.Response(200, json={"message": {"content": ""}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        report = diagnose_ollama(mock_settings(), c)
    assert report.reachable and report.model_available
    assert "invalid JSON" in report.error
    assert report.response_seconds >= 0


def test_llama_schema_json_validation_and_provenance(page, program):
    def handler(request):
        payload = json.loads(request.content)
        assert payload["format"]["type"] == "object"
        assert payload["options"]["temperature"] == 0
        assert "untrusted" in payload["messages"][0]["content"]
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": json.dumps(
                        {
                            "claims": [
                                {
                                    "field": "tuition_fees",
                                    "value": "500 EUR per semester",
                                    "quote": "Tuition for this programme: 500 EUR per semester.",
                                }
                            ],
                            "uncertainties": [
                                "Fee applicability and academic year require review."
                            ],
                        }
                    )
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        result = LlamaExtractor(mock_settings(), c).augment(program, page)
    assert result.tuition_fees == "500 EUR per semester"
    assert result.currency is None  # Never inferred from an unrequested model field.
    assert result.provenance["tuition_fees"][0].method == "llama"
    assert result.provenance["tuition_fees"][0].status == "needs_review"
    assert result.verification_status == "needs_review"
    assert not result.recommendation_eligible
    assert result.provenance["tuition_fees"][0].source_url == result.source_url


@pytest.mark.parametrize(
    "draft",
    [
        {"claims": [{"field": "tuition_fees", "value": "0", "quote": "Free tuition"}]},
        {"claims": [{"field": "tuition_fees", "value": "0", "quote": "500 EUR per semester"}]},
        {"claims": [{"field": "verification_status", "value": "verified", "quote": "verified"}]},
        {"claims": [], "verification_status": "verified"},
        {
            "claims": [
                {"field": "currency", "value": "EUR", "quote": "500 EUR per semester"},
                {"field": "currency", "value": "EUR", "quote": "500 EUR per semester"},
            ]
        },
    ],
)
def test_unsupported_or_promoting_llama_output_is_rejected(page, program, draft):
    def handler(request):
        return httpx.Response(200, json={"message": {"content": json.dumps(draft)}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        result = LlamaExtractor(mock_settings(), c).augment(program, page)
    assert result.tuition_fees is None
    assert result.currency is None
    assert any("unavailable/rejected" in issue for issue in result.issues)


@pytest.mark.parametrize("error", [httpx.ConnectError, httpx.ReadTimeout])
def test_offline_llama_does_not_break_deterministic_collection(page, program, error):
    def handler(request):
        raise error("offline", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        result = LlamaExtractor(mock_settings(), c).augment(program, page)
    assert result.program_name == program.program_name
    assert result.provenance == program.provenance
    assert result.recommendation_eligible is False
    assert any("unavailable/rejected" in issue for issue in result.issues)
