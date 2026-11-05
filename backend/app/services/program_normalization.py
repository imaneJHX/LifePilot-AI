"""Normalize only explicitly evidenced units, currencies and complete calendar dates."""

import re
from datetime import date


def currency_code(value: str) -> str | None:
    found = set()
    for code, pattern in {
        "EUR": r"\bEUR\b|€|\beuros?\b",
        "GBP": r"\bGBP\b|£|\bpounds? sterling\b",
        "CAD": r"\bCAD\b|CA\$|C\$|Canadian dollars?",
        "USD": r"\bUSD\b|US\$|US dollars?",
        "CHF": r"\bCHF\b",
    }.items():
        if re.search(pattern, value, re.I):
            found.add(code)
    return next(iter(found)) if len(found) == 1 else None


def teaching_languages(value: str) -> list[str] | None:
    languages = []
    for label, pattern in {
        "English": r"\b(?:English|Anglais|Inglese|Englisch|ENG)\b",
        "French": r"\b(?:French|Français|Frans|Französisch|FRA)\b",
        "German": r"\b(?:German|Deutsch|Allemand|Tedesco|DEU)\b",
        "Italian": r"\b(?:Italian|Italiano|Italien|ITA)\b",
        "Dutch": r"\b(?:Dutch|Nederlands|Néerlandais|NLD)\b",
    }.items():
        if re.search(pattern, value, re.I):
            languages.append(label)
    return languages or None


def explicit_date(value: str) -> date | None:
    value = value.strip()
    match = re.fullmatch(r"(20\d{2})-(\d{2})-(\d{2})", value)
    if match:
        return date(*map(int, match.groups()))
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(20\d{2})", value)
    if match:
        day, month, year = map(int, match.groups())
        if day <= 12 and month <= 12 and day != month:
            return None  # Locale-ambiguous dates need adapter-specific interpretation.
        return date(year, month, day)
    months = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    match = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(20\d{2})", value)
    if match and match[2].lower() in months:
        return date(int(match[3]), months[match[2].lower()], int(match[1]))
    match = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d{2})", value)
    if match and match[1].lower() in months:
        return date(int(match[3]), months[match[1].lower()], int(match[2]))
    return None


def duration_months(value: str) -> int | None:
    match = re.fullmatch(r"(\d+)\s*(months?|mois|mesi)", value.strip(), re.I)
    if match:
        return int(match[1])
    match = re.fullmatch(r"(\d+)\s*(years?|ans?|anni)", value.strip(), re.I)
    return int(match[1]) * 12 if match else None


def academic_year(value: str) -> str | None:
    match = re.fullmatch(r"(20\d{2})\s*[-/]\s*(20\d{2}|\d{2})", value.strip())
    if not match:
        return None
    start = int(match[1])
    end = int(match[2]) if len(match[2]) == 4 else start + 1
    if (end % 100 != int(match[2]) % 100) or end != start + 1:
        raise ValueError("Nonconsecutive academic year.")
    return f"{start}/{end}"
