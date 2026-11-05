import hashlib
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import HttpUrl, ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.real_program import RealProgramRecord
from app.repositories.catalog import get_catalog
from app.repositories.real_programs import deduplicate, export_json, import_programs, read_export
from app.schemas.real_programs import CollectionExport, ProgramFacts, RealProgram, SourceRegistry
from app.services.real_program_extraction import extract_program
from app.services.university_collection import collect, discover_sources
from app.services.university_retrieval import RetrievedPage, html_text

ORIGIN = "https://official.example.edu"
TERMS = b"<html><body>Local factual research; no republication.</body></html>"
PROGRAM_HTML = """<html><head><meta charset="utf-8">
<title>Computer Science – TU Darmstadt</title></head><body>
Master of Science; language: English
General Information &amp; Application Semesters 4 Language English C1 .
Admission requirements A relevant degree. Admission procedure Entrance exam may be required.
Application Online application
<script>Tuition fees: 999 EUR Admission</script></body></html>"""


@pytest.fixture
def registry():
    return SourceRegistry.model_validate(
        {
            "policies": [
                {
                    "origin": ORIGIN,
                    "terms_url": ORIGIN + "/legal",
                    "terms_reviewed_at": datetime.now(UTC),
                    "terms_sha256": hashlib.sha256(TERMS).hexdigest(),
                    "decision": "local_research_only",
                    "review_note": "Mock policy reviewed for this test only.",
                }
            ],
            "programs": [
                {
                    "program_url": ORIGIN + "/program",
                    "discovery_url": ORIGIN + "/masters",
                    "country": "Germany",
                    "focus": "Computer Science",
                    "adapter": "tu_darmstadt",
                }
            ],
        }
    )


@pytest.fixture
def program(registry):
    page = RetrievedPage(
        ORIGIN + "/program",
        datetime.now(UTC),
        hashlib.sha256(PROGRAM_HTML.encode()).hexdigest(),
        html_text(PROGRAM_HTML),
        "page.html",
    )
    return extract_program(page, registry.programs[0])


def make_export(program):
    return CollectionExport(generated_at=datetime.now(UTC), programs=[program])


def test_missing_values_are_null_and_hidden_script_is_not_fee_evidence(program):
    assert program.program_name == "Computer Science"
    assert program.duration == "4 semesters"
    assert program.tuition_fees is program.currency is program.academic_year is None
    assert program.city is program.application_deadline is None
    assert "Entrance exam may be required" in program.admission_requirements
    assert program.verification_status == "needs_review"
    assert program.recommendation_eligible is False
    assert program.provenance["country"][0].status == "unverified"
    assert "tuition_fees" not in program.provenance


@pytest.mark.parametrize(
    "field,value",
    [
        ("country", "Atlantis"),
        ("currency", "euros"),
        ("duration", 4),
        ("official_program_url", "javascript:alert(1)"),
        ("tuition_fees", float("nan")),
        ("university_name", " "),
    ],
)
def test_fact_validation_rejects_invalid_values(field, value):
    with pytest.raises(ValidationError):
        ProgramFacts.model_validate({field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("synthetic", True),
        ("recommendation_eligible", True),
        ("verification_status", "verified"),
    ],
)
def test_real_staging_contract_prevents_synthetic_and_automatic_promotion(program, field, value):
    data = program.model_dump(mode="json")
    data[field] = value
    with pytest.raises(ValidationError):
        RealProgram.model_validate(data)


def test_every_populated_field_retains_provenance(program):
    for field in ProgramFacts.model_fields:
        if getattr(program, field) is not None:
            evidence = program.provenance[field][0]
            assert str(evidence.source_url) == ORIGIN + "/program"
            assert evidence.retrieved_at == program.retrieval_date
            assert len(evidence.content_sha256) == 64
            assert evidence.quote or evidence.method == "source_registry"
    data = program.model_dump(mode="json")
    del data["provenance"]["program_name"]
    with pytest.raises(ValidationError, match="Missing provenance"):
        RealProgram.model_validate(data)


def test_evidence_for_null_or_unknown_fields_is_rejected(program):
    data = program.model_dump(mode="json")
    data["provenance"]["city"] = data["provenance"]["program_name"]
    with pytest.raises(ValidationError, match="Null field"):
        RealProgram.model_validate(data)
    data["provenance"].pop("city")
    data["provenance"]["unknown"] = data["provenance"]["program_name"]
    with pytest.raises(ValidationError, match="Unknown provenance"):
        RealProgram.model_validate(data)


def test_identical_duplicates_and_fragment_aliases_are_detected(program):
    alias = program.model_copy(
        update={"official_program_url": HttpUrl(ORIGIN + "/program/#overview")}
    )
    unique, duplicates = deduplicate([program, program, alias])
    assert unique == [program]
    assert len(duplicates) == 2


def test_identity_alias_is_detected_but_conflicting_duplicates_fail(program):
    alias = program.model_copy(update={"official_program_url": HttpUrl(ORIGIN + "/program-alias")})
    assert len(deduplicate([program, alias])[0]) == 1
    conflict = program.model_copy(update={"duration": "8 semesters"})
    with pytest.raises(ValueError, match="Conflicting duplicate"):
        deduplicate([program, conflict])


def test_different_academic_years_remain_separate(program):
    data = program.model_dump(mode="json")
    data["academic_year"] = "2027/2028"
    data["provenance"]["academic_year"] = data["provenance"]["program_name"]
    data["id"] = "real-" + "b" * 24
    other = RealProgram.model_validate(data)
    assert len(deduplicate([program, other])[0]) == 2


def test_json_export_roundtrip_preserves_unicode_nulls_and_provenance(tmp_path, program):
    output = tmp_path / "processed" / "programs.json"
    export_json(make_export(program), output)
    restored = read_export(output)
    assert restored.programs == [program]
    assert json.loads(output.read_text())["programs"][0]["tuition_fees"] is None
    assert not list(output.parent.glob("*.tmp"))


def test_empty_collection_stays_an_honest_empty_export(tmp_path):
    output = tmp_path / "empty.json"
    export_json(CollectionExport(generated_at=datetime.now(UTC), programs=[]), output)
    assert read_export(output).programs == []


def test_export_refuses_fictional_sample_path(tmp_path, program):
    with pytest.raises(ValueError, match="fictional"):
        export_json(make_export(program), tmp_path / "sample" / "universities.json")


def test_database_import_is_idempotent_and_preserves_demo_catalog(program):
    before = get_catalog()
    engine = create_engine("sqlite://")
    try:
        assert import_programs(make_export(program), engine) == {
            "inserted": 1,
            "updated": 0,
            "duplicates": 0,
        }
        assert import_programs(make_export(program), engine)["updated"] == 1
        with Session(engine) as session:
            rows = list(session.scalars(select(RealProgramRecord)))
            assert len(rows) == 1
            assert RealProgram.model_validate(rows[0].data) == program
            assert rows[0].recommendation_eligible is False
        assert get_catalog() == before
        assert all(item.synthetic for item in get_catalog())
    finally:
        engine.dispose()


def test_database_import_rejects_invalid_external_payload_and_stale_snapshots(program):
    engine = create_engine("sqlite://")
    try:
        import_programs(make_export(program), engine)
        older = program.model_copy(
            update={"retrieval_date": program.retrieval_date - timedelta(days=1)}
        )
        with pytest.raises(ValueError, match="older retrieval"):
            import_programs(make_export(older), engine)
        invalid = program.model_copy(update={"recommendation_eligible": True})
        with pytest.raises(ValidationError):
            import_programs(make_export(invalid), engine)
    finally:
        engine.dispose()


def test_duplicate_database_identity_under_different_id_is_not_inserted(program):
    engine = create_engine("sqlite://")
    try:
        import_programs(make_export(program), engine)
        alternate_id = program.model_copy(update={"id": "real-" + "c" * 24})
        with pytest.raises(ValueError, match="Duplicate identity"):
            import_programs(make_export(alternate_id), engine)
        with Session(engine) as session:
            assert len(list(session.scalars(select(RealProgramRecord)))) == 1
    finally:
        engine.dispose()


def test_curated_discovery_deduplicates_urls_and_requires_policy(registry):
    registry.programs.append(registry.programs[0])
    assert len(list(discover_sources(registry))) == 1
    registry.policies.clear()
    with pytest.raises(ValueError, match="approved source policy"):
        list(discover_sources(registry))


def test_mocked_full_pipeline_and_offline_replay(tmp_path, registry):
    requests = []

    def handler(request):
        requests.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200, text="User-agent: *\nAllow: /", headers={"content-type": "text/plain"}
            )
        if request.url.path == "/legal":
            return httpx.Response(200, content=TERMS, headers={"content-type": "text/html"})
        return httpx.Response(200, text=PROGRAM_HTML, headers={"content-type": "text/html"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = collect(registry, client, tmp_path / "raw", tmp_path / "out.json", interval=0)
    assert len(result.programs) == 1
    assert requests == ["/robots.txt", "/legal", "/program"]

    def offline(request):
        pytest.fail("Replay must not make any HTTP request")

    with httpx.Client(transport=httpx.MockTransport(offline)) as client:
        replay = collect(
            registry,
            client,
            tmp_path / "replay-run",
            tmp_path / "replay.json",
            replay_dir=tmp_path / "raw",
        )
    assert replay.programs == result.programs
    archive = json.loads((tmp_path / "raw/manifest.json").read_text())
    (tmp_path / "raw" / archive["pages"][0]["raw_file"]).write_text("tampered")
    with httpx.Client(transport=httpx.MockTransport(offline)) as client:
        tampered = collect(
            registry,
            client,
            tmp_path / "tampered-run",
            tmp_path / "tampered.json",
            replay_dir=tmp_path / "raw",
        )
    assert tampered.programs == []
    assert "hash mismatch" in tampered.failures[0]["reason"]


def test_live_network_failure_exports_no_invented_programs(tmp_path, registry):
    def offline(request):
        raise httpx.ConnectError("offline", request=request)

    with httpx.Client(transport=httpx.MockTransport(offline)) as client:
        result = collect(registry, client, tmp_path / "raw", tmp_path / "out.json", interval=0)
    assert result.programs == []
    assert "Network unavailable" in result.failures[0]["reason"]
    assert read_export(tmp_path / "out.json").programs == []


def test_french_m2_preserves_published_language_location_and_past_deadline(registry):
    text = (
        "M2 Artificial Intelligence | Université Paris-Saclay Master Mention Informatique "
        "Formation initiale Formation continue Anglais "
        "Public visé et prérequis Des acquis de M1. "
        "Période(s) de candidature Plateforme Inception Du 01/03/2026 au 01/04/2026 "
        "Preuve d'un niveau d'anglais B2 ou document officiel de votre université. "
        "Lieu(x) d'enseignement ORSAY Campus de la formation"
    )
    page = RetrievedPage(
        ORIGIN + "/program",
        datetime(2026, 11, 2, tzinfo=UTC),
        hashlib.sha256(text.encode()).hexdigest(),
        text,
        "french.html",
    )
    seed = registry.programs[0].model_copy(update={"adapter": "paris_saclay", "country": "France"})
    result = extract_program(page, seed)
    assert result.program_name == "M2 Artificial Intelligence"
    assert result.city == "ORSAY"
    assert result.teaching_language == "Anglais"
    assert result.duration is result.academic_year is None
    assert result.application_deadline == "Du 01/03/2026 au 01/04/2026"
    assert "B2" in result.english_language_requirements
    assert any("deadline has passed" in issue for issue in result.issues)


def test_explicit_zero_tuition_and_period_are_retained_without_total_cost_assumptions(registry):
    html = PROGRAM_HTML + "Tuition fees: 0 EUR per semester Semester fee additional."
    page = RetrievedPage(
        ORIGIN + "/program",
        datetime.now(UTC),
        hashlib.sha256(html.encode()).hexdigest(),
        html_text(html),
        "zero-tuition.html",
    )
    result = extract_program(page, registry.programs[0])
    assert result.tuition_fees == "0 EUR per semester"
    assert result.currency == "EUR"
    assert result.provenance["currency"][0].quote == "EUR"
    assert result.academic_year is None


def test_database_transaction_rolls_back_earlier_insert_on_identity_conflict(program):
    engine = create_engine("sqlite://")
    try:
        import_programs(make_export(program), engine)
        data = program.model_dump(mode="json")
        data.update(id="real-" + "d" * 24, program_name="A different program")
        data["official_program_url"] = ORIGIN + "/other-program"
        new_program = RealProgram.model_validate(data)
        conflict = program.model_copy(update={"id": "real-" + "e" * 24})
        export = CollectionExport(generated_at=datetime.now(UTC), programs=[new_program, conflict])
        with pytest.raises(ValueError, match="Duplicate identity"):
            import_programs(export, engine)
        with Session(engine) as session:
            assert [row.id for row in session.scalars(select(RealProgramRecord))] == [program.id]
    finally:
        engine.dispose()
