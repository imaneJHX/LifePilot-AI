import copy
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.real_program import RealProgramRecord
from app.repositories.real_catalog import deadline_status
from app.repositories.real_programs import import_programs, read_export

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def staged(client):
    path = ROOT / "data/processed/real_university_programs.json"
    if not path.is_file():
        pytest.skip("Optional private university export is not included in the public repository.")
    with contextmanager(client.app.dependency_overrides[get_db])() as session:
        engine = session.get_bind()
        export = read_export(path)
        import_programs(export, engine)
    return client, engine, export


def test_empty_database_does_not_fall_back_to_export(client):
    response = client.get("/api/real-programs")
    assert response.status_code == 200
    assert response.json()["programs"] == []
    assert response.json()["total"] == response.json()["count"] == 0
    assert response.headers["cache-control"] == "no-store"


def test_catalog_reads_database_without_promoting_or_changing_records(staged):
    client, engine, export = staged
    with Session(engine) as session:
        before = {
            row.id: copy.deepcopy(row.data) for row in session.scalars(select(RealProgramRecord))
        }
    response = client.get("/api/real-programs")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == body["count"] == 78
    assert body["recommendation_eligible"] is False
    assert len(body["countries"]) == len(body["universities"]) == len(body["study_areas"]) == 7
    for row in body["programs"]:
        assert row["verification_status"] == "needs_review"
        assert row["synthetic"] is False
        assert row["recommendation_eligible"] is False
        assert "provenance" not in row and "review" not in row
        for field in ("tuition_fees", "admission_requirements", "english_language_requirements"):
            assert row[field] == before[row["id"]][field]
    assert sum(row["tuition_fees"] is None for row in body["programs"]) == 57
    assert sum(row["deadline_status"] == "expired" for row in body["programs"]) == 10
    assert sum(row["deadline_status"] == "unknown" for row in body["programs"]) == 68
    with Session(engine) as session:
        after = {row.id: row.data for row in session.scalars(select(RealProgramRecord))}
        assert all(
            not row.recommendation_eligible for row in session.scalars(select(RealProgramRecord))
        )
    assert before == after == {p.id: p.model_dump(mode="json") for p in export.programs}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "country,count",
    [
        ("Belgium", 2),
        ("Canada", 3),
        ("France", 10),
        ("Germany", 10),
        ("Italy", 24),
        ("Netherlands", 4),
        ("United Kingdom", 25),
    ],
)
def test_all_seven_country_filters(staged, country, count):
    client, _, _ = staged
    body = client.get("/api/real-programs", params={"country": country}).json()
    assert body["count"] == len(body["programs"]) == count
    assert body["total"] == 78
    assert all(row["country"] == country for row in body["programs"])
    assert len(body["countries"]) == 7  # Facets remain available after filtering.


def test_combined_filters_are_case_and_accent_insensitive(staged):
    client, _, _ = staged
    body = client.get(
        "/api/real-programs",
        params={
            "country": " france ",
            "university": "universite paris-saclay",
            "study_area": "artificial intelligence",
            "search": "M2 Artificial Intelligence",
        },
    ).json()
    assert body["count"] == 1
    assert body["programs"][0]["program_name"] == "M2 Artificial Intelligence"
    assert (
        client.get("/api/real-programs", params={"search": "no such program xyz"}).json()["count"]
        == 0
    )


def test_a_database_row_removal_changes_results_not_the_export(staged):
    client, engine, export = staged
    with Session(engine) as session, session.begin():
        session.execute(
            delete(RealProgramRecord).where(RealProgramRecord.id == export.programs[0].id)
        )
    body = client.get("/api/real-programs").json()
    assert body["total"] == 77
    assert export.programs[0].id not in {p["id"] for p in body["programs"]}


@pytest.mark.parametrize("tampering", ["unreviewed_verified_label", "ranking_enabled"])
def test_invalid_staging_data_is_not_silently_published(staged, tampering):
    client, engine, export = staged
    with Session(engine) as session, session.begin():
        row = session.get(RealProgramRecord, export.programs[0].id)
        data = copy.deepcopy(row.data)
        if tampering == "unreviewed_verified_label":
            data["verification_status"] = "verified"
        else:
            data["recommendation_eligible"] = True
        row.data = data
    response = client.get("/api/real-programs")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "real_catalog_invalid"


def test_demo_profiles_and_rankings_stay_separate(staged, profile_data):
    client, _, _ = staged
    profile_id = client.post("/api/profile", json=profile_data).json()["id"]
    before = client.post("/api/recommendations", json={"profile_id": profile_id}).json()
    client.get("/api/real-programs")
    after = client.post("/api/recommendations", json={"profile_id": profile_id}).json()
    assert before == after
    assert all(row["program"]["synthetic"] for row in after["results"])
    assert all(not row["program"]["id"].startswith("real-") for row in after["results"])
    assert len(client.get("/api/universities").json()) == 24
    assert client.get(f"/api/profile/{profile_id}").status_code == 200


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, "unknown"),
        (date(2026, 11, 4), "expired"),
        (date(2026, 11, 5), "today"),
        (date(2026, 11, 6), "upcoming"),
    ],
)
def test_deadline_status_uses_date_only_without_inventing_intakes(value, expected):
    assert deadline_status(value, date(2026, 11, 5)) == expected


def test_raw_undated_window_is_not_invented_as_a_future_date(staged):
    client, _, _ = staged
    rows = client.get("/api/real-programs", params={"university": "McGill University"}).json()[
        "programs"
    ]
    row = next(p for p in rows if p["application_deadline"])
    assert row["application_deadline_date"] is None
    assert row["deadline_status"] == "unknown"


def test_filter_length_validation(client):
    assert client.get("/api/real-programs", params={"search": "x" * 101}).status_code == 422
