"""Idempotent, validated staging import; no synthetic table or JSON catalog writes."""

import json
import unicodedata
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.models.real_program import RealProgramRecord
from app.schemas.real_programs import CollectionExport, ProgramFacts, RealProgram, canonical_url


def _identity(program: RealProgram) -> tuple:
    def normalized(value):
        return " ".join(unicodedata.normalize("NFKC", value or "").casefold().split())

    return tuple(
        normalized(value)
        for value in (
            program.university_name,
            program.program_name,
            program.degree_type,
            program.country,
            program.academic_year,
        )
    )


def deduplicate(programs: list[RealProgram]) -> tuple[list[RealProgram], list[dict[str, str]]]:
    unique: list[RealProgram] = []
    duplicates = []
    urls, identities = {}, {}
    for item in programs:
        program = RealProgram.model_validate(item.model_dump(mode="json"))
        url_key = (canonical_url(str(program.official_program_url)), program.academic_year)
        identity = _identity(program)
        prior = urls.get(url_key) or identities.get(identity)
        if prior:
            # Never choose arbitrarily between contradictory facts for the same intake.
            a = prior.model_dump(include=set(ProgramFacts.model_fields), mode="json")
            b = program.model_dump(include=set(ProgramFacts.model_fields), mode="json")
            a.pop("official_program_url", None)
            b.pop("official_program_url", None)
            if a != b:
                raise ValueError(f"Conflicting duplicate: {program.official_program_url}")
            duplicates.append({"id": program.id, "duplicate_of": prior.id})
            continue
        unique.append(program)
        urls[url_key] = program
        identities[identity] = program
    return unique, duplicates


def export_json(export: CollectionExport, output: Path) -> None:
    checked = CollectionExport.model_validate(export.model_dump(mode="json"))
    output = output.resolve()
    if "sample" in output.parts:
        raise ValueError("Cannot export real records into the fictional sample directory.")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + "." + uuid4().hex + ".tmp")
    try:
        temporary.write_text(checked.model_dump_json(indent=2) + "\n", encoding="utf-8")
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()


def import_programs(export: CollectionExport, engine: Engine) -> dict[str, int]:
    # Revalidate external JSON and reject conflicting duplicates before creating/writing tables.
    checked = CollectionExport.model_validate(export.model_dump(mode="json"))
    programs, duplicates = deduplicate(checked.programs)
    RealProgramRecord.__table__.create(engine, checkfirst=True)
    counts = {"inserted": 0, "updated": 0, "duplicates": len(duplicates)}
    with Session(engine) as session, session.begin():
        for program in programs:
            row = session.get(RealProgramRecord, program.id)
            if row is None:
                # Also reject alternate IDs pointing to the same URL/intake in existing storage.
                for candidate in session.scalars(select(RealProgramRecord)):
                    existing = RealProgram.model_validate(candidate.data)
                    if (
                        canonical_url(str(existing.official_program_url))
                        == canonical_url(str(program.official_program_url))
                        and existing.academic_year == program.academic_year
                    ) or _identity(existing) == _identity(program):
                        raise ValueError("Duplicate identity under a different database ID.")
                row = RealProgramRecord(id=program.id)
                session.add(row)
                counts["inserted"] += 1
            else:
                existing = RealProgram.model_validate(row.data)
                if (
                    canonical_url(str(existing.official_program_url))
                    != canonical_url(str(program.official_program_url))
                    or existing.academic_year != program.academic_year
                ):
                    raise ValueError("Existing ID belongs to a different program/intake.")
                if existing.retrieval_date > program.retrieval_date:
                    raise ValueError(
                        "Refusing to replace a newer snapshot with an older retrieval."
                    )
                counts["updated"] += 1
            row.source_url = str(program.source_url)
            row.data = program.model_dump(mode="json")
            row.retrieved_at = program.retrieval_date
            row.recommendation_eligible = False
    return counts


def read_export(path: Path) -> CollectionExport:
    return CollectionExport.model_validate(json.loads(path.read_text(encoding="utf-8")))


def migrate_staging_payloads(engine: Engine) -> int:
    """Idempotent additive JSON migration using the existing checkfirst table approach."""
    RealProgramRecord.__table__.create(engine, checkfirst=True)
    changed = 0
    with Session(engine) as session, session.begin():
        for row in session.scalars(select(RealProgramRecord)):
            program = RealProgram.model_validate(row.data)
            if program.id != row.id:
                raise ValueError("Staging row ID does not match its payload.")
            normalized = program.model_dump(mode="json")
            if row.data != normalized or row.recommendation_eligible:
                row.data = normalized
                row.recommendation_eligible = False
                changed += 1
    return changed
