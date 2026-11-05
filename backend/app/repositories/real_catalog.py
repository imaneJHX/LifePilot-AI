"""Read validated records from staging without importing, updating or ranking them."""

import unicodedata
from datetime import UTC, date, datetime

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.real_program import RealProgramRecord
from app.schemas.real_catalog import RealProgramCatalog, RealProgramSummary
from app.schemas.real_programs import ProgramFacts, RealProgram


def deadline_status(deadline: date | None, today: date) -> str:
    if deadline is None:
        return "unknown"
    if deadline < today:
        return "expired"
    return "today" if deadline == today else "upcoming"


def folded(value: str) -> str:
    return " ".join(
        "".join(
            char for char in unicodedata.normalize("NFKD", value) if not unicodedata.combining(char)
        )
        .casefold()
        .split()
    )


def list_real_programs(
    session: Session,
    *,
    country: str | None = None,
    university: str | None = None,
    study_area: str | None = None,
    search: str = "",
) -> RealProgramCatalog:
    today = datetime.now(UTC).date()
    programs = []
    fields = set(ProgramFacts.model_fields) | {"id", "retrieval_date", "verification_status"}
    for row in session.scalars(select(RealProgramRecord).order_by(RealProgramRecord.id)):
        try:
            program = RealProgram.model_validate(row.data)
            if program.id != row.id:
                raise ValueError("Staging ID mismatch.")
            programs.append(
                RealProgramSummary.model_validate(
                    {
                        **program.model_dump(include=fields),
                        "deadline_status": deadline_status(
                            program.application_deadline_date, today
                        ),
                    }
                )
            )
        except (ValidationError, ValueError) as exc:
            raise AppError(
                "real_catalog_invalid",
                "The real-program records need a data review before they can be displayed.",
                503,
            ) from exc
    programs.sort(
        key=lambda p: (folded(p.university_name or ""), folded(p.program_name or ""), p.id)
    )
    query = folded(search)
    matches = [
        p
        for p in programs
        if (not country or folded(p.country or "") == folded(country))
        and (not university or folded(p.university_name or "") == folded(university))
        and (not study_area or folded(p.study_area or "") == folded(study_area))
        and (
            not query
            or query
            in folded(
                " ".join(
                    value or ""
                    for value in (
                        p.program_name,
                        p.university_name,
                        p.country,
                        p.city,
                        p.study_area,
                        p.degree_type,
                    )
                )
            )
        )
    ]
    return RealProgramCatalog(
        programs=matches,
        total=len(programs),
        count=len(matches),
        countries=sorted({p.country for p in programs if p.country}),
        universities=sorted({p.university_name for p in programs if p.university_name}),
        study_areas=sorted({p.study_area for p in programs if p.study_area}),
        as_of_date=today,
    )
