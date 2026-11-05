import json
from functools import lru_cache

from app.core.config import get_settings
from app.schemas.contracts import Program


@lru_cache
def get_catalog() -> tuple[Program, ...]:
    path = get_settings().dataset_path
    with path.open(encoding="utf-8") as file:
        raw = json.load(file)
    programs = tuple(Program.model_validate(item) for item in raw["programs"])
    if len({program.id for program in programs}) != len(programs):
        raise ValueError("Program identifiers must be unique.")
    return programs
