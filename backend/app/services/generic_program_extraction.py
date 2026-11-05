"""Conservative DOM/section extraction for reviewed university sources."""

import hashlib
import re

from app.schemas.real_programs import Evidence, ProgramFacts, RealProgram, SourceSeed, canonical_url
from app.services.program_documents import ProgramDocument
from app.services.program_normalization import (
    academic_year,
    currency_code,
    duration_months,
    explicit_date,
    teaching_languages,
)
from app.services.university_retrieval import RetrievedPage


def extract_generic(page: RetrievedPage, seed: SourceSeed) -> RealProgram:
    document = ProgramDocument(page.html or "")
    facts, provenance, issues = {}, {}, []

    def put(key, value, quote=None, *, metadata=False, note=None):
        if value is None or key in facts:
            return
        if not metadata and (not quote or quote not in page.text):
            return
        ProgramFacts.model_validate({key: value})
        facts[key] = value
        provenance[key] = [
            Evidence(
                source_url=page.url,
                retrieved_at=page.retrieved_at,
                content_sha256=page.sha256,
                quote=quote,
                method="source_registry" if metadata else "rule",
                status="unverified" if metadata else "source_supported",
                note=note,
            )
        ]

    put(
        "country",
        seed.country,
        metadata=True,
        note="Reviewed discovery metadata; not text verification.",
    )
    put(
        "study_area", seed.focus, metadata=True, note="Discovery category; not a predictive rating."
    )
    put("official_program_url", page.url, metadata=True, note="Retrieved approved official URL.")
    put(
        "official_university_url",
        "/".join(page.url.split("/", 3)[:3]) + "/",
        metadata=True,
        note="Approved university origin; no independent verification claimed.",
    )
    if seed.university_name:
        if seed.university_name in page.text:
            put("university_name", seed.university_name, seed.university_name)
        else:
            put(
                "university_name",
                seed.university_name,
                metadata=True,
                note="Curated institution identity from the reviewed official discovery registry.",
            )
    headings = [n.text() for n in document.find("h1") if n.text()]
    titles = [n.text() for n in document.find("title") if n.text()]
    name = None
    if seed.expected_name:
        expected = re.sub(r"\s*\[[^\[\]]+\]\s*$", "", seed.expected_name).strip()
        for candidate in (seed.expected_name, expected):
            if (
                candidate in page.text
                and len(candidate) > 3
                and any(
                    candidate in h
                    for h in headings + titles + [n.text() for n in document.find("h2")]
                )
            ):
                name = candidate
                break
    if name is None and titles and " - Taught degree programmes" in titles[0]:
        name = titles[0].rsplit(" - ", 1)[-1].strip()
    if name is None:
        name = next(
            (
                n.text()
                for n in document.find("h1", "h2")
                if n.text().startswith(("Master of ", "Master in "))
            ),
            None,
        )
    if name is None and headings:
        name = next(
            (
                h
                for h in headings
                if len(h) > 5
                and h.lower()
                not in (
                    "study",
                    "search",
                    "postgraduate study",
                    "master programmes",
                    "master's programmes",
                )
            ),
            None,
        )
    if name:
        original_name = name
        name = re.sub(r"\s*\[[^\[\]]+\]\s*$", "", name).strip()
        # Reject topic/category/index pages and undergraduate programmes even if linked from a list.
        if re.search(r"\b(bachelor|BSc|BEng|PhD|PGCert|micro.?credential)\b", name, re.I):
            raise ValueError("Discovered page is not a master's program.")
        put("program_name", name, original_name)
        for heading in document.find("h1", "h2"):
            text = heading.text()
            if name in text:
                degree = re.search(r"\b(MSc|MEng|MBA|MAcc|MFin|IntM)\b", text)
                if degree:
                    put("degree_type", degree[1], text)
                    break
    if not re.search(
        r"\b(master|masters|MSc|MEng|MBA|M\.Sc\.|laurea magistrale|M2)\b", page.text, re.I
    ):
        raise ValueError("No master's-level evidence in the retrieved program page.")
    for label, value, quote in document.labeled_values():
        if len(value) > 2500:
            continue
        key = label.casefold().strip(" :")
        if re.fullmatch(r"duration|durata|length|programme duration|standard period of study", key):
            put("duration", value, quote)
        elif re.fullmatch(
            r"language|languages|lingua|teaching language|language of instruction", key
        ):
            put("teaching_language", value, quote)
        elif re.fullmatch(r"city|location|place of teaching|study location", key):
            put("city", value, quote)
        elif re.fullmatch(r"degree|degree type|qualification|level|livello", key):
            if re.search(r"master|MSc|MEng|MBA|magistrale", value, re.I):
                put("degree_type", value, quote)
        elif re.fullmatch(r"tuition fees?|fees?|tuition", key):
            if re.search(r"\d", value) and currency_code(value):
                put("tuition_fees", value, quote)
        elif re.fullmatch(r"academic year|anno accademico", key):
            try:
                put("academic_year", academic_year(value), quote)
            except ValueError:
                issues.append("Invalid academic year published; not normalized.")
    sections = list(document.source_sections())
    for heading, body in sections:
        if len(body) > 5000:
            body = body[:5000].rsplit(" ", 1)[0]
        if re.fullmatch(r"duration|durata|programme length", heading, re.I) and len(body) < 200:
            put("duration", body, body)
        if re.fullmatch(r"language|lingua|teaching language", heading, re.I) and len(body) < 100:
            put("teaching_language", body, body)
        if re.fullmatch(r"level|qualification|livello", heading, re.I) and len(body) < 100:
            if re.search(r"master|MSc|MEng|magistrale", body, re.I):
                put("degree_type", body, body)
        if re.search(
            r"^(about (the |this )?(programme|program|course)|overview|programme overview|"
            r"description|the course in brief|il corso in breve)$",
            heading,
            re.I,
        ):
            put("description", body, body)
        if re.fullmatch(
            r"entry requirements|admission requirements|admissions requirements|"
            r"admission|requirements|admission and application",
            heading,
            re.I,
        ):
            if len(body) > 40:
                put("admission_requirements", body, body)
        if re.fullmatch(
            r"english language requirements|language requirements|english language", heading, re.I
        ):
            if re.search(r"IELTS|TOEFL|B2|C1|English|anglais", body):
                put("english_language_requirements", body, body)
        if re.fullmatch(
            r"tuition fees|tuition and fees|fees|annual fees|fees (?:and|&) funding", heading, re.I
        ):
            fee_amount = re.search(
                r"(?:tuition(?:\s+fees?)?|(?:full|part)[ -]time fees?|annual fees?)"
                r"[^\d£€$]{0,60}(?:£|€|(?:CAD|USD|EUR|GBP)\s*)\s*\d",
                body,
                re.I,
            )
            if fee_amount and currency_code(body):
                put(
                    "tuition_fees",
                    body,
                    body,
                    note="Published fee context retained; cohort and period require review.",
                )
    if "degree_type" not in facts:
        match = re.search(
            r"\b(Master of Science|Master of Engineering|Master of Business Administration|"
            r"Master of Management|MSc|MEng|MBA|Laurea magistrale)\b",
            page.text,
        )
        if match:
            put("degree_type", match[1], match[0])
    # Explicit labeled inline units, never course-credit quantities or degree-level assumptions.
    if "duration" not in facts:
        match = re.search(
            r"(?:Duration|Durata|Programme length)\s*:?\s*(\d+\s*(?:years?|months?|Anni|anni))\b",
            page.text,
        )
        if match:
            put("duration", match[1], match[0])
    if "teaching_language" not in facts:
        match = re.search(
            r"(?:Teaching language|Language of instruction|Language|Lingua)\s*:?\s*"
            r"(English|French|Italian|Dutch|German|Inglese|Italiano)(?:\b)",
            page.text,
        )
        if match:
            put("teaching_language", match[1], match[0])
    if "description" not in facts:
        mains = document.find("main")
        nodes = list(mains[0].find({"p"})) if mains else document.find("p")
        for node in nodes:
            text = node.text()
            if (
                100 <= len(text) <= 1500
                and re.search(r"master|programme|program|degree|course|engineering", text, re.I)
                and not re.search(r"cookies|privacy|javascript|we use|sign up", text, re.I)
            ):
                put("description", text, text)
                break
    published_year = re.search(
        r"(?:Academic year|Tuition fees for)\s*:?\s*(20\d{2}[-/](?:20\d{2}|\d{2}))", page.text, re.I
    )
    if published_year:
        try:
            put(
                "academic_year",
                academic_year(published_year[1]),
                published_year[0],
                note="Explicit published academic/fee year; no year inferred from retrieval.",
            )
        except ValueError:
            issues.append("Invalid published academic year; left for review.")
    if facts.get("tuition_fees"):
        code = currency_code(facts["tuition_fees"])
        put(
            "currency",
            code,
            facts["tuition_fees"],
            note="Explicit symbol/code normalized; no conversion.",
        )
    if facts.get("teaching_language"):
        put(
            "teaching_languages",
            teaching_languages(facts["teaching_language"]),
            provenance["teaching_language"][0].quote,
            note="Explicit language names/codes normalized; original teaching_language retained.",
        )
    if facts.get("duration"):
        put(
            "duration_months",
            duration_months(facts["duration"]),
            provenance["duration"][0].quote,
            note="Explicit years/months converted; semesters and mixed modes not assumed.",
        )
    # Preserve recurring/cohort-specific application tables without inventing their year.
    for table in document.find("table"):
        text = table.text()
        if (
            len(text) <= 3000
            and re.search(r"Applications? Open", text, re.I)
            and re.search(r"Application Deadline", text, re.I)
        ):
            put(
                "application_deadline",
                text,
                text,
                note="Full intake/cohort table preserved; missing years are not inferred.",
            )
    date_token = (
        r"(?:20\d{2}-\d{2}-\d{2}|\d{1,2}\s+[A-Z][a-z]+\s+20\d{2}|[A-Z][a-z]+\s+\d{1,2},?\s+20\d{2})"
    )
    for key, label in [
        ("application_opening_date", r"Applications? open(?:s|ing)?(?: date)?"),
        ("application_deadline_date", r"Application deadline|Applications? close(?:s| date)?"),
    ]:
        match = re.search(r"(?:" + label + r")\s*:?\s*(" + date_token + ")", page.text)
        if match:
            try:
                put(key, explicit_date(match[1]), match[0])
                if key == "application_deadline_date":
                    put("application_deadline", match[1], match[0])
            except ValueError:
                issues.append(f"{key}: invalid calendar date published; not normalized.")
    if (
        facts.get("application_deadline_date")
        and facts["application_deadline_date"] < page.retrieved_at.date()
    ):
        issues.append("Published application deadline has passed; next intake is unverified.")
    if (
        facts.get("application_opening_date")
        and facts.get("application_deadline_date")
        and facts["application_opening_date"] > facts["application_deadline_date"]
    ):
        for key in ("application_opening_date", "application_deadline_date"):
            facts.pop(key, None)
            provenance.pop(key, None)
        issues.append("Opening date follows deadline; normalized pair removed for review.")
    for key in ProgramFacts.model_fields:
        if facts.get(key) is None:
            issues.append(f"{key}: not established by supported extraction; left null.")
    identifier = hashlib.sha256(
        (canonical_url(page.url) + "|" + (facts.get("academic_year") or "")).encode()
    ).hexdigest()[:24]
    return RealProgram.model_validate(
        {
            **facts,
            "id": "real-" + identifier,
            "source_url": page.url,
            "retrieval_date": page.retrieved_at,
            "provenance": provenance,
            "issues": issues,
        }
    )
