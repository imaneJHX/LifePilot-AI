"""Check configured local Ollama without installing/downloading anything."""

import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.services.ollama_diagnostics import diagnose_ollama  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print the diagnostic report as JSON.")
    parser.add_argument("--output", type=Path, help="Also save the report to this JSON file.")
    args = parser.parse_args()
    settings = get_settings()
    with httpx.Client(
        timeout=httpx.Timeout(settings.ollama_timeout_seconds, connect=3.0), trust_env=False
    ) as client:
        report = diagnose_ollama(settings, client)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        print(f"Server: {report.server_url}")
        print(f"Reachable: {report.reachable}")
        print("Installed models: " + json.dumps(report.installed_models))
        print(f"Configured model: {report.configured_model}; available: {report.model_available}")
        print(f"Model response: {report.response or '(not obtained)'}")
        print(
            f"Inference time: {report.response_seconds}; total seconds: {report.total_seconds:.3f}"
        )
        if report.error:
            print("Error: " + report.error)
        for instruction in report.instructions:
            print(instruction)
    return 0 if report.response is not None and report.error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
