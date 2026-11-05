"""Reproducible quality metrics and local RAG preparation; no retrieval index or ranking."""

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime

from app.schemas.real_programs import (
    CollectionExport,
    Evidence,
    ProgramFacts,
    StrictModel,
    Text,
    canonical_url,
)


class RagDocument(StrictModel):
    id: str
    program_id: str
    program_name: str
    university_name: str | None
    country: str | None
    section: Literal["description", "admission_requirements", "english_language_requirements"]
    content: Text
    content_sha256: str
    official_program_url: str
    retrieved_at: AwareDatetime
    source_references: list[Evidence]
    program_verification_status: Literal["unverified", "needs_review", "verified"]
    recommendation_eligible: Literal[False] = False
    usage_scope: Literal["local_research_only"] = "local_research_only"


def quality_report(export: CollectionExport) -> dict:
    export = CollectionExport.model_validate(export.model_dump(mode="json"))
    programs = export.programs
    total = len(programs)
    missing = {
        name: {
            "missing": sum(getattr(program, name) is None for program in programs),
            "present": sum(getattr(program, name) is not None for program in programs),
            "missing_percent": round(
                100 * sum(getattr(p, name) is None for p in programs) / total, 2
            )
            if total
            else None,
        }
        for name in ProgramFacts.model_fields
    }
    return {
        "schema_version": 1,
        "generated_at": export.generated_at.isoformat(),
        "total_programs": total,
        "unique_program_urls": len({canonical_url(str(p.official_program_url)) for p in programs}),
        "countries": dict(sorted(Counter(p.country or "Unknown" for p in programs).items())),
        "universities": dict(
            sorted(Counter(p.university_name or "Unknown" for p in programs).items())
        ),
        "study_areas": dict(sorted(Counter(p.study_area or "Unknown" for p in programs).items())),
        "verification_status": dict(Counter(p.verification_status for p in programs)),
        "verified_programs": sum(p.verification_status == "verified" for p in programs),
        "recommendation_eligible_programs": sum(p.recommendation_eligible for p in programs),
        "synthetic_programs": sum(p.synthetic for p in programs),
        "missing_information": missing,
        "expired_deadlines": [
            p.id
            for p in programs
            if p.application_deadline_date and p.application_deadline_date < p.retrieval_date.date()
        ],
        "date_issues": [
            {"program_id": p.id, "issue": issue}
            for p in programs
            for issue in p.issues
            if "date" in issue.lower() or "deadline" in issue.lower()
        ],
        "failed_sources": export.failures,
        "failed_source_count": len({item["url"] for item in export.failures}),
        "duplicates": export.duplicates,
        "duplicate_count": len(export.duplicates),
        "provenance_methods": dict(
            Counter(e.method for p in programs for values in p.provenance.values() for e in values)
        ),
        "notes": [
            "Source-supported quotations are not human verification.",
            "Country and category discovery metadata remain unverified unless explicitly reviewed.",
            "Missing values are null; no exchange rates, living costs or synthetic indices added.",
            "Expired dates describe the published intake, never a presumed future year.",
        ],
    }


def rag_documents(export: CollectionExport) -> list[RagDocument]:
    export = CollectionExport.model_validate(export.model_dump(mode="json"))
    documents = []
    for program in export.programs:
        for section in ("description", "admission_requirements", "english_language_requirements"):
            value = getattr(program, section)
            if value is None:
                continue
            digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
            documents.append(
                RagDocument(
                    id=f"{program.id}:{section}:{digest[:12]}",
                    program_id=program.id,
                    program_name=program.program_name,
                    university_name=program.university_name,
                    country=program.country,
                    section=section,
                    content=value,
                    content_sha256=digest,
                    official_program_url=str(program.official_program_url),
                    retrieved_at=program.retrieval_date,
                    source_references=program.provenance[section],
                    program_verification_status=program.verification_status,
                )
            )
    return documents


def write_quality_artifacts(export: CollectionExport, directory: Path) -> dict:
    directory = directory.resolve()
    if "sample" in directory.parts:
        raise ValueError("Real quality artifacts cannot overwrite the synthetic sample directory.")
    directory.mkdir(parents=True, exist_ok=True)
    report = quality_report(export)
    documents = rag_documents(export)
    report["rag_documents"] = len(documents)
    (directory / "data_quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (directory / "rag_program_documents.jsonl").write_text(
        "".join(document.model_dump_json() + "\n" for document in documents), encoding="utf-8"
    )
    lines = [
        "# Real program data quality",
        "",
        f"Generated: {report['generated_at']}",
        "",
        f"Collected records: **{report['total_programs']}**; "
        f"unique URLs: **{report['unique_program_urls']}**.",
        f"Verified: **{report['verified_programs']}**; "
        f"recommendation eligible: **{report['recommendation_eligible_programs']}**.",
        f"RAG preparation documents: **{len(documents)}**. "
        "No embeddings, index or RAG service created.",
        "",
        "## Countries",
        "",
        "| Country | Programs |",
        "| --- | ---: |",
        *[f"| {country} | {count} |" for country, count in report["countries"].items()],
        "",
        "## Universities",
        "",
        "| University | Programs |",
        "| --- | ---: |",
        *[f"| {name} | {count} |" for name, count in report["universities"].items()],
        "",
        "## Missing information",
        "",
        "| Field | Missing | Missing % |",
        "| --- | ---: | ---: |",
        *[
            f"| {name} | {value['missing']} | {value['missing_percent']} |"
            for name, value in report["missing_information"].items()
        ],
        "",
        "## Failed or excluded sources",
        "",
        *[f"- {failure['url']}: {failure['reason']}" for failure in export.failures],
        "",
        "## Duplicates",
        "",
        f"{len(export.duplicates)} duplicate occurrences excluded; "
        "details in data_quality_report.json.",
        "",
        "## Limits",
        "",
        *[f"- {note}" for note in report["notes"]],
    ]
    (directory / "DATA_QUALITY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
