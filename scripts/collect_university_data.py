"""Discover and collect bounded official master's programs into separate real staging."""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.core.database import build_engine  # noqa: E402
from app.repositories.real_programs import (  # noqa: E402
    export_json,
    import_programs,
    migrate_staging_payloads,
    read_export,
)
from app.schemas.real_programs import SourceRegistry  # noqa: E402
from app.services.llama_extraction import LlamaExtractor  # noqa: E402
from app.services.program_quality import write_quality_artifacts  # noqa: E402
from app.services.university_collection import collect  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sources", type=Path, default=ROOT / "data/sources/official_master_programs.json"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "data/processed/real_university_programs.json"
    )
    parser.add_argument("--raw-dir", type=Path, help="New directory for this run's raw snapshots.")
    parser.add_argument(
        "--replay", type=Path, help="Replay a raw run without university HTTP requests."
    )
    parser.add_argument(
        "--use-ollama", action="store_true", help="Try optional unverified Llama extraction."
    )
    parser.add_argument(
        "--import-db", action="store_true", help="Upsert to the real staging table only."
    )
    parser.add_argument(
        "--import-only", type=Path, help="Import an existing validated JSON export; no HTTP."
    )
    parser.add_argument(
        "--merge-existing",
        action="store_true",
        help="Preserve older programs not returned by this collection run.",
    )
    args = parser.parse_args()
    settings = get_settings()
    if args.import_only:
        report = read_export(args.import_only)
    else:
        previous = (
            read_export(args.output) if args.merge_existing and args.output.exists() else None
        )
        registry = SourceRegistry.model_validate_json(args.sources.read_text(encoding="utf-8"))
        raw_dir = args.raw_dir or (
            ROOT
            / "data/raw"
            / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
        )
        if raw_dir.exists() and any(raw_dir.iterdir()):
            parser.error(
                "--raw-dir must be new or empty; historical snapshots cannot be overwritten."
            )
        with (
            httpx.Client(timeout=httpx.Timeout(25, connect=5), follow_redirects=False) as client,
            httpx.Client(
                timeout=httpx.Timeout(settings.ollama_timeout_seconds, connect=3), trust_env=False
            ) as model_client,
        ):
            report = collect(
                registry,
                client,
                raw_dir,
                args.output,
                extractor=LlamaExtractor(settings, model_client) if args.use_ollama else None,
                replay_dir=args.replay,
            )
        print(f"Collected {len(report.programs)} real staging records; output: {args.output}")
        print(f"Raw run: {args.replay or raw_dir}")
        if previous:
            from app.schemas.real_programs import canonical_url

            merged = {
                (canonical_url(str(p.official_program_url)), p.academic_year): p
                for p in previous.programs
            }
            for program in report.programs:
                key = (canonical_url(str(program.official_program_url)), program.academic_year)
                if key not in merged or merged[key].retrieval_date <= program.retrieval_date:
                    merged[key] = program
            report.programs = list(merged.values())
            report.notes.append(
                "Older unmatched programs retained with their original retrieval dates."
            )
            export_json(report, args.output)
        for failure in report.failures:
            print(f"Skipped: {failure.get('url', '(source)')}: {failure.get('reason', '')}")
    quality = write_quality_artifacts(report, args.output.parent)
    print(
        f"Quality: {quality['total_programs']} records, {quality['verified_programs']} verified, "
        f"{quality['rag_documents']} RAG preparation documents."
    )
    if args.import_db or args.import_only:
        engine = build_engine(settings.database_url)
        try:
            print(
                f"Additive staging payload migration: {migrate_staging_payloads(engine)} updated."
            )
            print("Staging DB import: " + str(import_programs(report, engine)))
        finally:
            engine.dispose()
    return 0 if report.programs else 2


if __name__ == "__main__":
    raise SystemExit(main())
