"""Staging contracts: real records cannot enter the synthetic ranking catalog."""

from datetime import date, datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    model_validator,
)

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=6000)]
Country = Literal[
    "Germany", "France", "Belgium", "Netherlands", "Italy", "United Kingdom", "Canada"
]
Focus = Literal[
    "Artificial Intelligence",
    "Data Science",
    "Computer Science",
    "Business Analytics",
    "Finance",
    "Management",
    "Engineering",
]


def canonical_url(value: str) -> str:
    parsed = urlsplit(value)
    return urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), parsed.query, "")
    )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_assignment=True)


class ProgramFacts(StrictModel):
    university_name: Text | None = None
    country: Country | None = None
    city: Text | None = None
    official_university_url: HttpUrl | None = None
    program_name: Text | None = None
    degree_type: Text | None = None
    teaching_language: Text | None = None
    teaching_languages: list[Literal["English", "French", "German", "Italian", "Dutch"]] | None = (
        Field(default=None, min_length=1, max_length=5)
    )
    duration: Text | None = None
    duration_months: int | None = Field(default=None, gt=0, le=120)
    description: Text | None = None
    study_area: Focus | None = None
    # Preserve original period, applicant cohort, and exceptions; never assume annual fees.
    tuition_fees: Text | None = None
    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")] | None = None
    academic_year: Text | None = None
    admission_requirements: Text | None = None
    english_language_requirements: Text | None = None
    application_deadline: Text | None = None
    application_opening_date: date | None = None
    application_deadline_date: date | None = None
    official_program_url: HttpUrl | None = None

    @model_validator(mode="after")
    def valid_normalized_values(self):
        if self.currency not in (None, "EUR", "GBP", "CAD", "USD", "CHF"):
            raise ValueError("Unsupported currency code; no country-based inference is allowed.")
        if self.academic_year:
            import re

            match = re.fullmatch(r"(20\d{2})/(20\d{2})", self.academic_year)
            if not match or int(match[2]) != int(match[1]) + 1:
                raise ValueError("Academic year must be an explicit consecutive YYYY/YYYY pair.")
        if (
            self.application_opening_date
            and self.application_deadline_date
            and self.application_opening_date > self.application_deadline_date
        ):
            raise ValueError("Application opening date cannot follow its deadline.")
        return self


class Evidence(StrictModel):
    source_url: HttpUrl
    retrieved_at: AwareDatetime
    content_sha256: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
    quote: Text | None = None
    method: Literal["rule", "llama", "source_registry"]
    status: Literal["source_supported", "needs_review", "unverified"]
    note: Text | None = None


class HumanReview(StrictModel):
    reviewer: Text
    reviewed_at: AwareDatetime
    reviewed_fields: list[str] = Field(min_length=1)
    source_versions: dict[str, str] = Field(min_length=1)
    note: Text


class RealProgram(ProgramFacts):
    id: Annotated[str, StringConstraints(pattern=r"^real-[a-f0-9]{24}$")]
    source_url: HttpUrl
    retrieval_date: AwareDatetime
    verification_status: Literal["unverified", "needs_review", "verified"] = "needs_review"
    review: HumanReview | None = None
    synthetic: Literal[False] = False
    recommendation_eligible: Literal[False] = False
    provenance: dict[str, list[Evidence]]
    issues: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def every_fact_has_evidence(self):
        if self.program_name is None or self.official_program_url is None:
            raise ValueError("A collected program needs an evidenced name and official URL.")
        for key in ProgramFacts.model_fields:
            value = getattr(self, key)
            evidence = self.provenance.get(key, [])
            if value is not None and not evidence:
                raise ValueError(f"Missing provenance for {key}.")
            if value is None and evidence:
                raise ValueError(f"Null field {key} cannot have accepted evidence.")
            for item in evidence:
                if item.method != "source_registry" and not item.quote:
                    raise ValueError("Extracted facts require an exact source quotation.")
                if (
                    item.method in ("llama", "source_registry")
                    and item.status == "source_supported"
                ):
                    raise ValueError("Model output and source metadata require review.")
        if set(self.provenance) - set(ProgramFacts.model_fields):
            raise ValueError("Unknown provenance fields.")
        if self.verification_status == "verified":
            populated = {key for key in ProgramFacts.model_fields if getattr(self, key) is not None}
            if not self.review or not populated.issubset(self.review.reviewed_fields):
                raise ValueError("Verified records require a human review of every populated fact.")
            for items in self.provenance.values():
                for item in items:
                    if self.review.source_versions.get(str(item.source_url)) != item.content_sha256:
                        raise ValueError("Human review must reference each exact source version.")
        return self


class SourcePolicy(StrictModel):
    origin: HttpUrl
    terms_url: HttpUrl
    terms_reviewed_at: AwareDatetime
    terms_sha256: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
    decision: Literal["local_research_only", "blocked"]
    review_note: Text
    allow_same_origin_redirects: bool = False


class SourceSeed(StrictModel):
    program_url: HttpUrl
    discovery_url: HttpUrl
    country: Country
    focus: Focus
    adapter: Literal["tu_darmstadt", "paris_saclay", "generic"]
    university_name: Text | None = None
    expected_name: Text | None = None


class DiscoveryPage(StrictModel):
    url: HttpUrl
    country: Country
    university_name: Text
    adapter: Literal["tu_darmstadt", "paris_saclay", "generic"] = "generic"
    program_path_pattern: Text
    name_pattern: Text = (
        r"(?i)artificial intelligence|data science|computer science|"
        r"business analytics|finance|management|engineering"
    )
    max_programs: int = Field(default=12, ge=1, le=50)


class SourceRegistry(StrictModel):
    version: Literal[1] = 1
    policies: list[SourcePolicy]
    programs: list[SourceSeed] = Field(default_factory=list, max_length=100)
    discovery_pages: list[DiscoveryPage] = Field(default_factory=list, max_length=30)
    max_programs: int = Field(default=100, ge=1, le=100)
    excluded_sources: list[dict[str, str]] = Field(default_factory=list)


class CollectionExport(StrictModel):
    schema_version: Literal[1] = 1
    generated_at: datetime
    dataset_kind: Literal["real_staging"] = "real_staging"
    recommendation_eligible: Literal[False] = False
    programs: list[RealProgram]
    failures: list[dict[str, str]] = Field(default_factory=list)
    duplicates: list[dict[str, str]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
