"""Serve isolated browser-test data; never import fixtures into the user's database."""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--database", choices=["e2e.db", "android-e2e.db"], required=True)
    args = parser.parse_args()
    database = ROOT / args.database
    os.environ["DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
    sys.path.insert(0, str(ROOT / "backend"))

    import uvicorn

    from app.core.database import engine
    from app.repositories.real_programs import import_programs, read_export

    path = ROOT / "data/processed/real_university_programs.json"
    if path.is_file():
        import_programs(read_export(path), engine)
    else:
        print("Private university export absent; real-program explorer will be empty.", flush=True)
    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
