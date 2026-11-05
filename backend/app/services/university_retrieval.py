"""Small, bounded official-source retrieval with fail-closed access checks."""

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.schemas.real_programs import SourcePolicy

USER_AGENT = "LifePilotResearch/0.1 (+local academic programme data collection)"
MAX_BYTES = 3_000_000


class RetrievalError(Exception):
    pass


class SourceRedirect(RetrievalError):
    def __init__(self, url, location):
        super().__init__(f"Redirect requires source-registry review: {url}")
        self.location = location


class RobotsRules:
    """Longest-match robots rules, including * and $ unsupported by robotparser."""

    def __init__(self, text: str):
        self.timing = RobotFileParser()
        self.timing.parse(text.splitlines())
        self.groups: list[tuple[list[str], list[tuple[str, str]]]] = []
        agents: list[str] = []
        rules: list[tuple[str, str]] = []
        for line in text.splitlines():
            key, separator, value = line.split("#", 1)[0].partition(":")
            if not separator:
                continue
            key, value = key.strip().lower(), value.strip()
            if key == "user-agent":
                if rules:
                    self.groups.append((agents, rules))
                    agents, rules = [], []
                agents.append(value.lower())
            elif agents and key in ("allow", "disallow") and value:
                rules.append((key, value))
        if agents:
            self.groups.append((agents, rules))

    def can_fetch(self, agent: str, url: str) -> bool:
        matches = []
        for agents, rules in self.groups:
            specificity = max(
                (
                    0 if item == "*" else len(item)
                    for item in agents
                    if item == "*" or item in agent.lower()
                ),
                default=-1,
            )
            if specificity >= 0:
                matches.append((specificity, rules))
        if not matches:
            return True
        strongest = max(item[0] for item in matches)
        parsed = urlsplit(url)
        path = unquote(parsed.path or "/") + ("?" + parsed.query if parsed.query else "")
        matching_rules = []
        for specificity, rules in matches:
            if specificity != strongest:
                continue
            for action, pattern in rules:
                pattern = unquote(pattern)
                end = pattern.endswith("$")
                body = pattern[:-1] if end else pattern
                regex = re.escape(body).replace(r"\*", ".*") + ("$" if end else "")
                if re.match(regex, path):
                    matching_rules.append((len(body.replace("*", "")), action == "allow"))
        return max(matching_rules)[1] if matching_rules else True


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "template", "noscript"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "template", "noscript") and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def html_text(html: str) -> str:
    parser = VisibleText()
    parser.feed(html)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def decode_html(content: bytes, header_encoding: str | None = None) -> str:
    meta = re.search(rb"charset\s*=\s*[\"']?([\w.-]+)", content[:10000], re.I)
    encoding = meta[1].decode("ascii") if meta else header_encoding or "utf-8"
    try:
        return content.decode(encoding, errors="strict")
    except (LookupError, UnicodeError) as exc:
        raise RetrievalError(
            f"Cannot decode source using {encoding}; no lossy extraction."
        ) from exc


@dataclass(frozen=True)
class RetrievedPage:
    url: str
    retrieved_at: datetime
    sha256: str
    text: str
    raw_file: str
    html: str | None = None


class AuthorizedRetriever:
    def __init__(
        self, client: httpx.Client, policies: list[SourcePolicy], raw_dir: Path, *, interval=2.0
    ):
        self.client = client
        self.policies = {str(policy.origin).rstrip("/"): policy for policy in policies}
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.interval = max(0.0, interval)
        self.last_request: dict[str, float] = {}
        self.robots: dict[str, RobotsRules] = {}
        self.authorized: set[str] = set()
        self.stopped: set[str] = set()
        self.pages: dict[str, RetrievedPage] = {}

    def _origin(self, url: str) -> str:
        parsed = urlsplit(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if (
            parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
            or origin not in self.policies
        ):
            raise RetrievalError(f"Unapproved URL/origin: {url}")
        if self.policies[origin].decision == "blocked":
            raise RetrievalError(f"Source terms prohibit collection: {origin}")
        if origin in self.stopped:
            raise RetrievalError(f"Origin stopped after an access/rate-limit failure: {origin}")
        return origin

    def _get(self, url: str, delay: float) -> tuple[bytes, str | None, str]:
        origin = self._origin(url)
        remaining = delay - (time.monotonic() - self.last_request.get(origin, -1e10))
        if remaining > 0:
            time.sleep(remaining)
        try:
            with self.client.stream(
                "GET", url, headers={"User-Agent": USER_AGENT}, follow_redirects=False
            ) as response:
                self.last_request[origin] = time.monotonic()
                log = {
                    "url": url,
                    "status_code": response.status_code,
                    "retrieved_at": datetime.now(UTC).isoformat(),
                    "location": response.headers.get("location"),
                    "retry_after": response.headers.get("retry-after"),
                }
                with (self.raw_dir / "requests.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(log) + "\n")
                if response.status_code in (401, 403, 429, 503):
                    self.stopped.add(origin)
                if response.is_redirect:
                    raise SourceRedirect(url, response.headers.get("location", ""))
                if response.status_code != 200:
                    raise RetrievalError(f"HTTP {response.status_code}: {url}; no bypass or retry.")
                content = bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_BYTES:
                        raise RetrievalError(f"Response exceeds {MAX_BYTES} bytes: {url}")
                return (
                    bytes(content),
                    response.charset_encoding,
                    response.headers.get("content-type", "").lower(),
                )
        except httpx.RequestError as exc:
            self.stopped.add(origin)
            raise RetrievalError(
                f"Network unavailable for {url}: {type(exc).__name__}: {exc}"
            ) from exc

    def _snapshot(self, url: str, content: bytes, suffix: str) -> str:
        name = hashlib.sha256(url.encode()).hexdigest()[:24] + suffix
        (self.raw_dir / name).write_bytes(content)
        return name

    def _robots(self, origin: str) -> RobotsRules:
        if origin not in self.robots:
            content, _, content_type = self._get(origin + "/robots.txt", self.interval)
            if "text/plain" not in content_type:
                raise RetrievalError("robots.txt is not plain text; cannot establish access.")
            parser = RobotsRules(content.decode("utf-8-sig", errors="strict"))
            self.robots[origin] = parser
            self._snapshot(origin + "/robots.txt", content, ".robots.txt")
        return self.robots[origin]

    def fetch(self, url: str, *, _redirects: int = 0) -> RetrievedPage:
        if url in self.pages:
            return self.pages[url]
        origin = self._origin(url)
        robots = self._robots(origin)
        if not robots.can_fetch(USER_AGENT, url):
            raise RetrievalError(f"robots.txt disallows {url}")
        delay = max(self.interval, robots.timing.crawl_delay(USER_AGENT) or 0)
        rate = robots.timing.request_rate(USER_AGENT)
        if rate and rate.requests:
            delay = max(delay, rate.seconds / rate.requests)
        if delay > 60:
            raise RetrievalError(
                "Source requires a delay above the pilot's 60-second request budget."
            )
        if origin not in self.authorized:
            policy = self.policies[origin]
            terms_url = str(policy.terms_url)
            if self._origin(terms_url) != origin or not robots.can_fetch(USER_AGENT, terms_url):
                raise RetrievalError("Terms page cannot be reviewed under current access rules.")
            terms, _, _ = self._get(terms_url, delay)
            self._snapshot(terms_url, terms, ".terms.html")
            if hashlib.sha256(terms).hexdigest() != policy.terms_sha256:
                raise RetrievalError("Terms page changed since review; update policy after review.")
            self.authorized.add(origin)
        try:
            content, encoding, content_type = self._get(url, delay)
        except SourceRedirect as exc:
            target = urljoin(url, exc.location)
            if (
                not self.policies[origin].allow_same_origin_redirects
                or _redirects >= 3
                or not exc.location
                or self._origin(target) != origin
                or not robots.can_fetch(USER_AGENT, target)
            ):
                raise RetrievalError(
                    "Redirect target is not authorized by source policy/robots."
                ) from exc
            page = self.fetch(target, _redirects=_redirects + 1)
            self.pages[url] = page
            return page
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            raise RetrievalError(f"Only HTML sources are supported: {url}")
        raw_file = self._snapshot(url, content, ".html")
        html = decode_html(content, encoding)
        page = RetrievedPage(
            url,
            datetime.now(UTC),
            hashlib.sha256(content).hexdigest(),
            html_text(html),
            raw_file,
            html,
        )
        (self.raw_dir / (raw_file + ".text.txt")).write_text(page.text, encoding="utf-8")
        self.pages[url] = page
        return page
