"""Regenerate the fully fictional catalog. No real institution claims are represented."""

import json
from pathlib import Path

INSTITUTIONS = [
    ("alder", "Alder Institute of Technology", "Germany", "Berlin", 2400, 11200, 91, 88, 79),
    ("canal", "Canal Metropolitan University", "Netherlands", "Utrecht", 11200, 13400, 88, 94, 92),
    ("lumiere", "Lumière Graduate Institute", "France", "Lyon", 4200, 10200, 84, 84, 88),
    ("nordvik", "Nordvik School of Science", "Sweden", "Lund", 9800, 10800, 96, 90, 95),
    ("westbridge", "Westbridge International College", "Ireland", "Cork", 13800, 12800, 87, 96, 86),
    ("atlantic", "Atlantic Heights University", "Portugal", "Porto", 3200, 7600, 78, 79, 90),
]
AREAS = [
    ("cs", "Computer Science", "MSc Computer Science", ["Algorithms", "Distributed systems", "AI"]),
    (
        "ds",
        "Data Science",
        "MSc Data Science & AI",
        ["Machine learning", "Statistics", "Data engineering"],
    ),
    (
        "ba",
        "Business Analytics",
        "MSc Business Analytics",
        ["Decision science", "Analytics", "Strategy"],
    ),
    (
        "eng",
        "Engineering",
        "MSc Sustainable Engineering",
        ["Energy systems", "Design", "Optimization"],
    ),
]


def main():
    programs = []
    for i, institution in enumerate(INSTITUTIONS):
        slug, name, country, city, tuition, living, academic, career, experience = institution
        for j, (code, area, title, curriculum) in enumerate(AREAS):
            programs.append(
                {
                    "id": f"{slug}-{code}",
                    "university": name,
                    "program": title,
                    "country": country,
                    "city": city,
                    "study_area": area,
                    "tuition_eur": tuition + j * 400,
                    "living_cost_eur": living,
                    "duration_months": 24 if i != 4 else 12,
                    "language": "English",
                    "curriculum": curriculum,
                    "academic_index": academic - j,
                    "career_index": career - (j * 2) + (i % 2),
                    "experience_index": experience,
                    "synthetic": True,
                    "provenance": "Fictional LifePilot demonstration fixture v1. "
                    "Institution, program, costs and indices are invented; "
                    "city and country names provide illustrative geography only.",
                }
            )
    path = Path(__file__).resolve().parents[1] / "data" / "sample" / "universities.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "synthetic": True,
                "notice": (
                    "ALL institutions, programs, financial figures and indices are fictional."
                ),
                "currency": "EUR",
                "cost_period": "annual",
                "programs": programs,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(programs)} synthetic programs to {path}")


if __name__ == "__main__":
    main()
