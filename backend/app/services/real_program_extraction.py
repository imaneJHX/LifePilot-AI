"""Conservative source adapters. No missing tuition/deadline defaults or fabricated indices."""

import hashlib
import re
from datetime import datetime

from app.schemas.real_programs import Evidence, ProgramFacts, RealProgram, SourceSeed, canonical_url
from app.services.university_retrieval import RetrievedPage


def extract_program(page: RetrievedPage, seed: SourceSeed) -> RealProgram:
    if seed.adapter == "generic":
        from app.services.generic_program_extraction import extract_generic

        return extract_generic(page, seed)
    facts = ProgramFacts()
    provenance: dict[str, list[Evidence]] = {}
    issues = []

    def put(key, value, quote=None, *, registry=False, note=None):
        if value is None:
            return
        setattr(facts, key, value)
        provenance[key] = [
            Evidence(
                source_url=page.url,
                retrieved_at=page.retrieved_at,
                content_sha256=page.sha256,
                quote=quote,
                method="source_registry" if registry else "rule",
                status="unverified" if registry else "source_supported",
                note=note,
            )
        ]

    def match(key, pattern, group=1):
        found = re.search(pattern, page.text)
        if found:
            put(key, found[group].strip(), found[0])

    put("official_program_url", page.url, registry=True, note="Retrieved approved program URL.")
    origin = str(seed.program_url).split("/", 3)[:3]
    put(
        "official_university_url",
        "/".join(origin) + "/",
        registry=True,
        note="Approved institution origin from the discovery registry; not an extracted claim.",
    )
    put(
        "country",
        seed.country,
        registry=True,
        note="Curated discovery country; institutional location still requires evidence review.",
    )
    put("study_area", seed.focus, registry=True, note="Curated discovery category; not a score.")
    if seed.adapter == "tu_darmstadt":
        match("program_name", r"^(.+?)\s+[–—|]\s+TU Darmstadt")
        match("university_name", r"(TU Darmstadt)")
        match("degree_type", r"(Master of Science)")
        match("teaching_language", r"Master of Science; language:\s*(English)")
        found = re.search(r"Semesters\s+(\d+)\s+Language", page.text)
        if found:
            put("duration", f"{found[1]} semesters", found[0], note="Normalized table label/unit.")
        match(
            "admission_requirements",
            r"Admission requirements\s+(.+?)\s+Application\s+"
            r"(?:Online application|Application portal)",
        )
        match("english_language_requirements", r"Language\s+(English C1\s*\.)")
        # A link named 'application deadlines' is not itself a deadline.
    else:
        match("program_name", r"^(M[12]\s+.+?)\s*\|\s*Université Paris-Saclay")
        match("university_name", r"(Université Paris-Saclay)")
        match("degree_type", r"\s(Master)\s+Mention\s")
        match(
            "teaching_language",
            r"Mention Informatique\s+"
            r"(?:(?:Formation initiale|Formation continue)\s+)*(Anglais|Français)",
        )
        match("admission_requirements", r"Public visé et prérequis\s+(.+?)\s+Période\(s\)")
        match(
            "english_language_requirements",
            r"(Preuve d'un niveau d'anglais B2[^.]*\.)",
        )
        if facts.english_language_requirements is None:
            match(
                "english_language_requirements",
                r"(Pour intégrer le M2 DKAI,[^.]*niveau d[’']anglais B2[^.]*\.)",
            )
        if facts.english_language_requirements is None:
            match(
                "english_language_requirements",
                r"(Attestation de niveau d'anglais\s*\([^)]*\)\s*\.)",
            )
        match(
            "application_deadline",
            r"Période\(s\) de candidature\s+(?:Plateforme Inception\s+)?"
            r"(Du \d{2}/\d{2}/\d{4} au \d{2}/\d{2}/\d{4})",
        )
        match("city", r"Lieu\(x\) d'enseignement\s+(.+?)\s+(?:Campus de la formation|Contact\(s\))")
        if facts.program_name and facts.program_name.startswith("M2 "):
            issues.append("M2 is a second-year track; no full-degree duration inferred.")
    match("academic_year", r"(?:Academic year|Année universitaire)\s*:?\s*(20\d{2}[/-]20\d{2})")
    match("tuition_fees", r"Tuition fees\s*:\s*([^|]+?)(?:\s+Semester fee|\s+Admission)")
    if facts.tuition_fees:
        currency_match = re.search(r"\b(EUR|USD|GBP)\b", facts.tuition_fees)
        if currency_match:
            put("currency", currency_match[1], currency_match[0])
    if facts.teaching_language:
        from app.services.program_normalization import teaching_languages

        put(
            "teaching_languages",
            teaching_languages(facts.teaching_language),
            provenance["teaching_language"][0].quote,
            note="Canonical language names; original source wording retained.",
        )
    # Capture a description with the common evidence-checked adapter, retaining the pilot fields.
    if page.html:
        from app.services.program_documents import ProgramDocument

        doc = ProgramDocument(page.html)
        mains = doc.find("main")
        nodes = list(mains[0].find({"p"})) if mains else doc.find("p")
        for node in nodes:
            text = node.text()
            if (
                100 <= len(text) <= 1500
                and text in page.text
                and not re.search(r"cookie|privacy|javascript", text, re.I)
            ):
                put("description", text, text)
                break
    if facts.application_deadline:
        window = re.fullmatch(
            r"Du (\d{2}/\d{2}/\d{4}) au (\d{2}/\d{2}/\d{4})", facts.application_deadline
        )
        if window:
            try:
                opening = datetime.strptime(window[1], "%d/%m/%Y").date()
                closing = datetime.strptime(window[2], "%d/%m/%Y").date()
                if opening <= closing:
                    put(
                        "application_opening_date",
                        opening,
                        facts.application_deadline,
                        note="French-source day/month/year interpretation; no year inferred.",
                    )
                    put(
                        "application_deadline_date",
                        closing,
                        facts.application_deadline,
                        note="French-source day/month/year interpretation; no year inferred.",
                    )
                else:
                    issues.append("Published application date range is reversed; not normalized.")
            except ValueError:
                issues.append("Invalid published calendar dates; not normalized.")
    for key, value in facts.model_dump().items():
        if value is None:
            issues.append(f"{key}: not found in the retrieved program page; left null.")
    if facts.application_deadline:
        issues.append("Application window is copied as published; not advanced to a future intake.")
        end = re.search(r"au (\d{2}/\d{2}/\d{4})", facts.application_deadline)
        if end and datetime.strptime(end[1], "%d/%m/%Y").date() < page.retrieved_at.date():
            issues.append("Published application deadline has passed; next intake is unverified.")
    identifier = hashlib.sha256(
        (canonical_url(page.url) + "|" + (facts.academic_year or "")).encode()
    ).hexdigest()[:24]
    return RealProgram.model_validate(
        {
            **facts.model_dump(mode="json"),
            "id": "real-" + identifier,
            "source_url": page.url,
            "retrieval_date": page.retrieved_at,
            "provenance": provenance,
            "issues": issues,
        }
    )
