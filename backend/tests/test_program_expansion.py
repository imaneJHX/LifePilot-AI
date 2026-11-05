import hashlib
from datetime import UTC, date, datetime

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.real_program import RealProgramRecord
from app.repositories.real_programs import import_programs, migrate_staging_payloads
from app.schemas.real_programs import (
    CollectionExport,
    ProgramFacts,
    RealProgram,
    SourceRegistry,
    SourceSeed,
)
from app.services.generic_program_extraction import extract_generic
from app.services.program_documents import ProgramDocument
from app.services.program_normalization import (
    academic_year,
    currency_code,
    duration_months,
    explicit_date,
    teaching_languages,
)
from app.services.program_quality import (
    RagDocument,
    quality_report,
    rag_documents,
    write_quality_artifacts,
)
from app.services.university_collection import collect
from app.services.university_retrieval import (
    AuthorizedRetriever,
    RetrievalError,
    RetrievedPage,
    html_text,
)

ORIGIN = "https://official.example.edu"
TERMS = b"<html>Reviewed local-use notice</html>"


def source_page(html, url=ORIGIN + "/masters/computer-science"):
    return RetrievedPage(
        url,
        datetime(2026, 11, 2, tzinfo=UTC),
        hashlib.sha256(html.encode()).hexdigest(),
        html_text(html),
        "page.html",
        html,
    )


def seed():
    return SourceSeed(
        program_url=ORIGIN + "/masters/computer-science",
        discovery_url=ORIGIN + "/masters",
        country="Canada",
        focus="Computer Science",
        adapter="generic",
        university_name="Example University",
        expected_name="Computer Science [MSc]",
    )


@pytest.fixture
def program():
    return extract_generic(
        source_page("""<html><head><title>Computer Science - Example University</title>
    </head><body><main><h1>Computer Science MSc</h1>
    <p>This master's programme at Example University develops advanced computer science knowledge,
    with research projects in reliable systems and data analysis.</p>
    <dl><dt>Duration</dt><dd>2 years</dd><dt>Language</dt><dd>English</dd>
    <dt>Tuition fees</dt><dd>CAD 24000 per year, international applicants</dd>
    <dt>Academic year</dt><dd>2027/28</dd></dl>
    <h2>Entry requirements</h2><p>A relevant undergraduate degree with sufficient mathematics.</p>
    <h3>Academic preparation</h3><p>Algorithms and programming are required.</p>
    <h2>English language requirements</h2><p>IELTS 7.0 with no component below 6.5.</p>
    <h2>Applications</h2><p>Applications open: 2026-11-02. Application deadline: 2027-01-15.</p>
    </main></body></html>"""),
        seed(),
    )


@pytest.mark.parametrize(
    "text,expected",
    [
        ("€ 1000", "EUR"),
        ("1000 EUR", "EUR"),
        ("£10,000", "GBP"),
        ("C$12000", "CAD"),
        ("CAD 1000", "CAD"),
        ("US$1000", "USD"),
        ("$1000", None),
        ("EUR 100 GBP 90", None),
        ("No fee stated", None),
    ],
)
def test_currency_normalization_never_assumes_dollar_country_or_exchange_rate(text, expected):
    assert currency_code(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("2027-01-15", date(2027, 1, 15)),
        ("15 January 2027", date(2027, 1, 15)),
        ("January 15, 2027", date(2027, 1, 15)),
        ("January 15", None),
        ("01/02/2027", None),
    ],
)
def test_complete_dates_only(text, expected):
    assert explicit_date(text) == expected


@pytest.mark.parametrize("text", ["2027-02-29", "31 April 2027", "32/12/2027"])
def test_invalid_calendar_dates_are_rejected(text):
    with pytest.raises(ValueError):
        explicit_date(text)


@pytest.mark.parametrize(
    "text,expected",
    [("2 Years", 24), ("12 months", 12), ("4 semesters", None), ("12 or 16 months", None)],
)
def test_duration_preserves_ambiguity_and_semester_units(text, expected):
    assert duration_months(text) == expected


@pytest.mark.parametrize(
    "text,expected", [("2026/27", "2026/2027"), ("2026-2027", "2026/2027"), ("2026", None)]
)
def test_explicit_academic_year_normalization(text, expected):
    assert academic_year(text) == expected


def test_nonconsecutive_year_and_reversed_application_window_are_invalid():
    with pytest.raises(ValueError):
        academic_year("2026/2028")
    with pytest.raises(ValidationError):
        ProgramFacts(application_opening_date="2027-02-01", application_deadline_date="2027-01-01")
    with pytest.raises(ValidationError):
        ProgramFacts(currency="ZZZ")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Anglais", ["English"]),
        ("Inglese", ["English"]),
        ("ITA-ENG", ["English", "Italian"]),
        ("Nederlands", ["Dutch"]),
        ("Not stated", None),
    ],
)
def test_language_normalization_does_not_infer_language_from_country(raw, expected):
    assert teaching_languages(raw) == expected


def test_generic_structured_extraction_is_source_grounded_and_normalized(program):
    assert program.program_name == "Computer Science"
    assert program.degree_type == "MSc"
    assert program.duration_months == 24
    assert program.currency == "CAD"
    assert program.teaching_languages == ["English"]
    assert program.academic_year == "2027/2028"
    assert program.application_opening_date == date(2026, 11, 2)
    assert program.application_deadline_date == date(2027, 1, 15)
    assert "Algorithms and programming" in program.admission_requirements
    assert program.english_language_requirements.startswith("IELTS")
    assert program.city is None
    assert not program.recommendation_eligible


def test_html_section_spans_preserve_nested_requirements_and_skip_scripts():
    html = (
        "<h2>Entry requirements</h2><p>A degree.</p><h3>Maths</h3><p>Calculus.</p>"
        "<h2>Fees</h2><p>£10.</p><script>Fabricated fees</script>"
    )
    doc = ProgramDocument(html)
    sections = dict(doc.source_sections())
    assert sections["Entry requirements"] == "A degree. Maths Calculus."
    assert "Fabricated" not in doc.root.text()


def test_category_h1_is_not_used_as_a_program_name():
    html = (
        "<title>University of Glasgow - Postgraduate study - Taught degree programmes A‑Z - "
        "Data Science for Ecology</title><h1>Postgraduate study</h1>"
        "<h2>Data Science for Ecology MSc</h2>"
    )
    item = extract_generic(source_page(html), seed().model_copy(update={"expected_name": None}))
    assert item.program_name == "Data Science for Ecology"
    assert item.degree_type == "MSc"


def test_deposit_is_not_treated_as_tuition():
    html = (
        "<h1>Computer Science MSc</h1><h2>Fees &amp; funding</h2>"
        "<p>Tuition fees for 2027-28</p><h3>Deposits</h3><p>A deposit of £2000 is required.</p>"
    )
    item = extract_generic(source_page(html), seed())
    assert item.tuition_fees is item.currency is None
    assert item.academic_year == "2027/2028"


def test_international_master_qualification_is_not_replaced_by_related_msc():
    html = (
        "<h1>Postgraduate study</h1><h2>Computer Science IntM</h2>"
        "<p>Related programme: Engineering MSc.</p>"
    )
    item = extract_generic(
        source_page(html), seed().model_copy(update={"expected_name": "Computer Science [IntM]"})
    )
    assert item.program_name == "Computer Science"
    assert item.degree_type == "IntM"


def test_recurring_cohort_dates_remain_raw_without_an_invented_year():
    html = """<h1>Computer Science MSc</h1><table><tr><th>Intake</th><th>Applications Open</th>
    <th>Application Deadline International</th><th>Application Deadline Domestic</th></tr>
    <tr><td>Fall</td><td>September 15</td><td>December 15</td><td>February 15</td></tr></table>"""
    item = extract_generic(source_page(html), seed())
    assert "Domestic" in item.application_deadline
    assert item.application_opening_date is item.application_deadline_date is None


def test_program_verification_requires_explicit_review_and_matching_versions(program):
    data = program.model_dump(mode="json")
    data["verification_status"] = "verified"
    with pytest.raises(ValidationError, match="human review"):
        RealProgram.model_validate(data)
    data["review"] = {
        "reviewer": "Fixture reviewer",
        "reviewed_at": datetime.now(UTC).isoformat(),
        "reviewed_fields": [key for key in ProgramFacts.model_fields if data[key] is not None],
        "source_versions": {
            str(program.source_url): program.provenance["program_name"][0].content_sha256
        },
        "note": "Explicit review fixture, not production university verification.",
    }
    reviewed = RealProgram.model_validate(data)
    assert reviewed.verification_status == "verified"
    assert reviewed.recommendation_eligible is False
    data["review"]["source_versions"][str(program.source_url)] = "0" * 64
    with pytest.raises(ValidationError, match="exact source version"):
        RealProgram.model_validate(data)


def test_quality_and_rag_exports_preserve_missing_values_and_field_provenance(tmp_path, program):
    export = CollectionExport(
        generated_at=datetime.now(UTC),
        programs=[program],
        failures=[{"url": ORIGIN + "/blocked", "reason": "HTTP 403"}],
        duplicates=[{"id": program.id, "duplicate_of": program.id}],
    )
    metrics = quality_report(export)
    assert metrics["total_programs"] == metrics["unique_program_urls"] == 1
    assert metrics["verified_programs"] == metrics["synthetic_programs"] == 0
    assert metrics["missing_information"]["city"]["missing"] == 1
    assert metrics["duplicate_count"] == metrics["failed_source_count"] == 1
    documents = rag_documents(export)
    assert len(documents) == 3
    assert all(
        doc.source_references and doc.retrieved_at == program.retrieval_date for doc in documents
    )
    assert all(doc.program_verification_status == "needs_review" for doc in documents)
    write_quality_artifacts(export, tmp_path)
    restored = [
        RagDocument.model_validate_json(line)
        for line in (tmp_path / "rag_program_documents.jsonl").read_text().splitlines()
    ]
    assert restored == documents
    assert (tmp_path / "DATA_QUALITY_REPORT.md").exists()


def test_additive_json_migration_is_idempotent_and_never_promotes(program):
    engine = create_engine("sqlite://")
    try:
        import_programs(
            CollectionExport(generated_at=datetime.now(UTC), programs=[program]), engine
        )
        with Session(engine) as session, session.begin():
            row = session.get(RealProgramRecord, program.id)
            old = dict(row.data)
            old.pop("review")
            row.data = old
        assert migrate_staging_payloads(engine) == 1
        assert migrate_staging_payloads(engine) == 0
        with Session(engine) as session:
            row = session.get(RealProgramRecord, program.id)
            assert row.data["review"] is None
            assert row.recommendation_eligible is False
    finally:
        engine.dispose()


def test_discovery_conflicts_are_reported_without_losing_other_records(tmp_path):
    registry = SourceRegistry.model_validate(
        {
            "policies": [
                {
                    "origin": ORIGIN,
                    "terms_url": ORIGIN + "/terms",
                    "terms_reviewed_at": datetime.now(UTC),
                    "terms_sha256": hashlib.sha256(TERMS).hexdigest(),
                    "decision": "local_research_only",
                    "review_note": "Mock notice.",
                }
            ],
            "programs": [],
            "discovery_pages": [
                {
                    "url": ORIGIN + "/masters",
                    "country": "Canada",
                    "university_name": "Example University",
                    "program_path_pattern": r"^/masters/[^/]+$",
                    "max_programs": 10,
                }
            ],
        }
    )
    html = "<h1>Computer Science MSc</h1><p>Example University</p>"
    listing = (
        '<a href="/masters/cs">Computer Science</a>'
        '<a href="/masters/alias">Computer Science</a><a href="/masters/eng">Engineering</a>'
        '<a href="https://evil.test/masters/x">Finance</a>'
    )

    def handler(request):
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if path == "/terms":
            return httpx.Response(200, content=TERMS)
        body = listing if path == "/masters" else html
        if path == "/masters/alias":
            body += "<h2>Duration</h2><p>2 years</p>"
        if path == "/masters/eng":
            body = body.replace("Computer Science", "Engineering")
        return httpx.Response(200, text=body, headers={"content-type": "text/html"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        export = collect(registry, client, tmp_path / "raw", tmp_path / "out.json", interval=0)
    assert len(export.programs) == 2
    assert any("Conflicting duplicate" in f["reason"] for f in export.failures)
    assert any(d.get("stage") == "conflict" for d in export.duplicates)
    assert (tmp_path / "raw/manifest.json").exists()


def test_reviewed_same_origin_redirect_rechecks_robots_and_replays_without_network(tmp_path):
    registry = SourceRegistry.model_validate(
        {
            "policies": [
                {
                    "origin": ORIGIN,
                    "terms_url": ORIGIN + "/terms",
                    "allow_same_origin_redirects": True,
                    "terms_reviewed_at": datetime.now(UTC),
                    "terms_sha256": hashlib.sha256(TERMS).hexdigest(),
                    "decision": "local_research_only",
                    "review_note": "Mock reviewed redirects.",
                }
            ],
            "programs": [seed().model_dump(mode="json")],
        }
    )
    paths = []

    def handler(request):
        path = request.url.path
        paths.append(path)
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private")
        if path == "/terms":
            return httpx.Response(200, content=TERMS)
        if path == "/masters/computer-science":
            return httpx.Response(301, headers={"location": ORIGIN + "/canonical"})
        return httpx.Response(
            200, text="<h1>Computer Science MSc</h1>", headers={"content-type": "text/html"}
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        exported = collect(registry, client, tmp_path / "raw", tmp_path / "out.json", interval=0)
    assert str(exported.programs[0].source_url) == ORIGIN + "/canonical"
    assert paths == ["/robots.txt", "/terms", "/masters/computer-science", "/canonical"]

    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("Replay performed HTTP"))
    ) as client:
        replay = collect(
            registry,
            client,
            tmp_path / "replay",
            tmp_path / "replay.json",
            replay_dir=tmp_path / "raw",
        )
    assert replay.programs == exported.programs


@pytest.mark.parametrize("target", [ORIGIN + "/private/program", "https://evil.example/program"])
def test_redirect_cannot_cross_robots_or_origin_boundary(tmp_path, target):
    registry = SourceRegistry.model_validate(
        {
            "policies": [
                {
                    "origin": ORIGIN,
                    "terms_url": ORIGIN + "/terms",
                    "allow_same_origin_redirects": True,
                    "terms_reviewed_at": datetime.now(UTC),
                    "terms_sha256": hashlib.sha256(TERMS).hexdigest(),
                    "decision": "local_research_only",
                    "review_note": "Mock.",
                }
            ]
        }
    )

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private")
        if request.url.path == "/terms":
            return httpx.Response(200, content=TERMS)
        if request.url.path == "/program":
            return httpx.Response(302, headers={"location": target})
        pytest.fail("Unauthorized redirect fetched")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RetrievalError):
            AuthorizedRetriever(client, registry.policies, tmp_path, interval=0).fetch(
                ORIGIN + "/program"
            )
