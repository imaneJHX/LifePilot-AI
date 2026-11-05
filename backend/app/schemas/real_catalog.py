"""Read-only explorer contracts; real staging data is never a ranking input."""

from datetime import date
from typing import Literal

from pydantic import AwareDatetime

from app.schemas.real_programs import ProgramFacts, StrictModel


class RealProgramSummary(ProgramFacts):
    id: str
    retrieval_date: AwareDatetime
    verification_status: Literal["unverified", "needs_review", "verified"]
    deadline_status: Literal["expired", "upcoming", "today", "unknown"]
    synthetic: Literal[False] = False
    recommendation_eligible: Literal[False] = False


class RealProgramCatalog(StrictModel):
    programs: list[RealProgramSummary]
    total: int
    count: int
    countries: list[str]
    universities: list[str]
    study_areas: list[str]
    as_of_date: date
    recommendation_eligible: Literal[False] = False
