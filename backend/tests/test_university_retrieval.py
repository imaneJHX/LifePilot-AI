import hashlib
from datetime import UTC, datetime

import httpx
import pytest

from app.schemas.real_programs import SourcePolicy
from app.services.university_retrieval import (
    USER_AGENT,
    AuthorizedRetriever,
    RetrievalError,
    RobotsRules,
    decode_html,
    html_text,
)

ORIGIN = "https://official.example.edu"
TERMS = b"<html>Reviewed local research terms</html>"


@pytest.fixture
def policy():
    return SourcePolicy(
        origin=ORIGIN,
        terms_url=ORIGIN + "/legal",
        terms_reviewed_at=datetime.now(UTC),
        terms_sha256=hashlib.sha256(TERMS).hexdigest(),
        decision="local_research_only",
        review_note="Mock review.",
    )


def test_html_extraction_and_declared_encoding_are_preserved():
    text = decode_html(b'<meta charset="iso-8859-1"><p>Universit\xe9</p>')
    assert html_text(text) == "Université"
    assert html_text(
        "<p>Real &amp; visible</p><script>fake fees</script><style>hidden</style>"
    ) == ("Real & visible")
    with pytest.raises(RetrievalError, match="no lossy extraction"):
        decode_html(b"\xff", "utf-8")


@pytest.mark.parametrize(
    "url,expected",
    [
        ("/public", True),
        ("/private/data", False),
        ("/private/public", True),
        ("/data?blocked=yes", False),
        ("/document.pdf", False),
        ("/document.pdf/page", True),
        ("/%70rivate/data", False),
    ],
)
def test_robots_wildcards_longest_match_query_and_end_anchor(url, expected):
    rules = RobotsRules(
        "User-agent: *\nDisallow: /private/*\nAllow: /private/public\n"
        "Disallow: /*?blocked=\nDisallow: /*.pdf$"
    )
    assert rules.can_fetch(USER_AGENT, ORIGIN + url) is expected


def test_specific_agent_group_and_allow_tie_override_wildcard():
    rules = RobotsRules(
        "User-agent: *\nDisallow: /\nUser-agent: LifePilotResearch\nDisallow: /same\nAllow: /same\n"
    )
    assert rules.can_fetch(USER_AGENT, ORIGIN + "/public")
    assert rules.can_fetch(USER_AGENT, ORIGIN + "/same")
    assert not rules.can_fetch("OtherBot", ORIGIN + "/public")


@pytest.mark.parametrize("status", [401, 403, 429, 503])
def test_access_and_rate_limits_stop_origin_without_retry(tmp_path, policy, status):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(status, headers={"retry-after": "120"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        retriever = AuthorizedRetriever(client, [policy], tmp_path, interval=0)
        with pytest.raises(RetrievalError, match=f"HTTP {status}"):
            retriever.fetch(ORIGIN + "/program")
        with pytest.raises(RetrievalError, match="Origin stopped"):
            retriever.fetch(ORIGIN + "/program")
    assert len(calls) == 1


def test_robots_denial_prevents_terms_and_page_fetch(tmp_path, policy):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, text="User-agent: *\nDisallow: /program")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        retriever = AuthorizedRetriever(client, [policy], tmp_path, interval=0)
        with pytest.raises(RetrievalError, match="robots.txt disallows"):
            retriever.fetch(ORIGIN + "/program")
    assert calls == ["/robots.txt"]


def test_redirect_is_not_followed_or_used_as_bypass(tmp_path, policy):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(302, headers={"location": "https://unapproved.example/secret"})

    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        retriever = AuthorizedRetriever(client, [policy], tmp_path, interval=0)
        with pytest.raises(RetrievalError, match="Redirect requires"):
            retriever.fetch(ORIGIN + "/program")
    assert calls == ["/robots.txt"]


def test_changed_terms_prevent_program_fetch(tmp_path, policy):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        return httpx.Response(200, text="changed terms")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        retriever = AuthorizedRetriever(client, [policy], tmp_path, interval=0)
        with pytest.raises(RetrievalError, match="Terms page changed"):
            retriever.fetch(ORIGIN + "/program")
    assert calls == ["/robots.txt", "/legal"]


@pytest.mark.parametrize(
    "url",
    [
        "http://official.example.edu/program",
        "https://evil.example/program",
        "https://user:pass@official.example.edu/program",
        "https://official.example.edu:999/program",
        "https://127.0.0.1/program",
    ],
)
def test_unapproved_urls_never_reach_transport(tmp_path, policy, url):
    def handler(request):
        pytest.fail("Unapproved URL reached HTTP transport")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RetrievalError, match="Unapproved"):
            AuthorizedRetriever(client, [policy], tmp_path).fetch(url)


def test_blocked_policy_is_enforced_before_network(tmp_path, policy):
    policy.decision = "blocked"
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("Network called"))
    ) as client:
        with pytest.raises(RetrievalError, match="terms prohibit"):
            AuthorizedRetriever(client, [policy], tmp_path).fetch(ORIGIN + "/program")


def test_crawl_delay_and_request_rate_are_honored_without_real_sleep(tmp_path, policy, monkeypatch):
    waits = []
    monkeypatch.setattr("app.services.university_retrieval.time.monotonic", lambda: 100)
    monkeypatch.setattr("app.services.university_retrieval.time.sleep", waits.append)

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nCrawl-delay: 3\nRequest-rate: 1/4")
        return httpx.Response(200, content=TERMS, headers={"content-type": "text/html"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        AuthorizedRetriever(client, [policy], tmp_path, interval=2).fetch(ORIGIN + "/program")
    assert waits == [4, 4]


def test_unknown_robots_state_fails_closed(tmp_path, policy):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RetrievalError, match="HTTP 404"):
            AuthorizedRetriever(client, [policy], tmp_path).fetch(ORIGIN + "/program")
    assert calls == ["/robots.txt"]
