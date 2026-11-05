"""Bounded official catalog discovery, collection and offline replay."""

import hashlib
import json
import re
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from pydantic import ValidationError

from app.repositories.real_programs import deduplicate, export_json
from app.schemas.real_programs import CollectionExport, SourceRegistry, SourceSeed, canonical_url
from app.services.llama_extraction import LlamaExtractor
from app.services.program_documents import ProgramDocument
from app.services.real_program_extraction import extract_program
from app.services.university_retrieval import (
    AuthorizedRetriever,
    RetrievalError,
    RetrievedPage,
    decode_html,
    html_text,
)


def discover_sources(registry: SourceRegistry):
    """Reviewed official seed discovery; no broad crawl or unofficial admissions feed."""
    origins = {str(policy.origin).rstrip("/") for policy in registry.policies}
    seen = set()
    for seed in registry.programs:
        url = canonical_url(str(seed.program_url))
        origin = "/".join(url.split("/", 3)[:3])
        if origin not in origins:
            raise ValueError(f"Discovery URL lacks an approved source policy: {url}")
        if url not in seen:
            seen.add(url)
            yield seed


def infer_focus(name: str):
    for label, pattern in [
        ("Business Analytics", r"business analytics|^Analytics\b|Management in Analytics"),
        ("Artificial Intelligence", r"artificial intelligence|intelligence artificielle"),
        ("Data Science", r"data science|data analytics|science des donn"),
        ("Computer Science", r"computer science|computing|informatique"),
        ("Finance", r"financ|actuarial"),
        ("Management", r"management|business administration"),
        ("Engineering", r"engineering|ingegneria|ingénierie|ingenieur"),
    ]:
        if re.search(pattern, name, re.I):
            return label
    return None


def discover_catalogs(registry, retriever, snapshots, failures, duplicates):
    seeds = list(discover_sources(registry))
    seen = {canonical_url(str(seed.program_url)) for seed in seeds}
    for listing in registry.discovery_pages:
        try:
            page = retriever.fetch(str(listing.url))
            snapshots.append({key: value for key, value in asdict(page).items() if key != "html"})
            snapshots[-1]["retrieved_at"] = page.retrieved_at.isoformat()
            doc = ProgramDocument(page.html or "")
            added = 0
            for url, name in doc.links(page.url):
                if added >= listing.max_programs or len(seeds) >= registry.max_programs:
                    break
                parsed = urlsplit(url)
                if parsed.query or not re.search(listing.program_path_pattern, parsed.path):
                    continue
                if not re.search(listing.name_pattern, name):
                    continue
                # Discovery follows only same-origin links; other origins need their own listing.
                if (parsed.scheme, parsed.netloc) != (
                    urlsplit(page.url).scheme,
                    urlsplit(page.url).netloc,
                ):
                    continue
                focus = infer_focus(name)
                if focus is None:
                    continue
                key = canonical_url(url)
                if key in seen:
                    duplicates.append({"url": url, "duplicate_of": key, "stage": "discovery"})
                    continue
                seeds.append(
                    SourceSeed(
                        program_url=url,
                        discovery_url=page.url,
                        country=listing.country,
                        focus=focus,
                        adapter=listing.adapter,
                        university_name=listing.university_name,
                        expected_name=name,
                    )
                )
                seen.add(key)
                added += 1
            if not added:
                failures.append(
                    {"url": str(listing.url), "reason": "No new matching program links discovered."}
                )
        except (RetrievalError, ValueError, OSError) as exc:
            failures.append({"url": str(listing.url), "reason": str(exc)})
    return seeds


def collect(
    registry: SourceRegistry,
    client: httpx.Client,
    raw_dir: Path,
    output: Path,
    *,
    extractor: LlamaExtractor | None = None,
    interval: float = 2.0,
    replay_dir: Path | None = None,
) -> CollectionExport:
    raw_dir.mkdir(parents=True, exist_ok=True)
    retriever = AuthorizedRetriever(client, registry.policies, raw_dir, interval=interval)
    programs, failures, snapshots, discovery_duplicates = [], [], [], []
    archived = {}
    redirects = {}
    if replay_dir:
        archive = json.loads((replay_dir / "manifest.json").read_text(encoding="utf-8"))
        archived = {page["url"]: page for page in archive["pages"]}
        redirects = archive.get("redirects", {})
        failures.extend(archive.get("failures", []))
    if replay_dir:
        seed_data = archive.get("discovered_programs")
        seeds = (
            [SourceSeed.model_validate(s) for s in seed_data]
            if seed_data
            else list(discover_sources(registry))
        )
        discovery_duplicates = archive.get("discovery_duplicates", [])
    else:
        seeds = discover_catalogs(registry, retriever, snapshots, failures, discovery_duplicates)

    def checkpoint():
        if replay_dir:
            return
        (raw_dir / "source_registry.json").write_text(
            registry.model_dump_json(indent=2), encoding="utf-8"
        )
        (raw_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "pages": [{k: v for k, v in item.items() if k != "text"} for item in snapshots],
                    "failures": failures,
                    "discovered_programs": [s.model_dump(mode="json") for s in seeds],
                    "discovery_duplicates": discovery_duplicates,
                    "redirects": redirects,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    checkpoint()
    collected_urls = set()
    for seed in seeds:
        url = str(seed.program_url)
        try:
            if replay_dir:
                resolved_url = redirects.get(url, url)
                if urlsplit(resolved_url).netloc != urlsplit(url).netloc:
                    raise ValueError("Archive redirect crosses an unapproved origin.")
                if resolved_url not in archived:
                    raise RetrievalError(
                        "No authorized response snapshot; see original request failures."
                    )
                item = archived[resolved_url]
                raw_file = (replay_dir / item["raw_file"]).resolve()
                if not raw_file.is_relative_to(replay_dir.resolve()):
                    raise ValueError("Invalid archive path.")
                content = raw_file.read_bytes()
                if hashlib.sha256(content).hexdigest() != item["sha256"]:
                    raise ValueError("Archive content hash mismatch.")
                html = decode_html(content)
                page = RetrievedPage(
                    resolved_url,
                    datetime.fromisoformat(item["retrieved_at"]),
                    item["sha256"],
                    html_text(html),
                    item["raw_file"],
                    html,
                )
            else:
                page = retriever.fetch(url)
                if page.url != url:
                    redirects[url] = page.url
                snapshots.append(
                    {key: value for key, value in asdict(page).items() if key != "html"}
                )
                snapshots[-1]["retrieved_at"] = page.retrieved_at.isoformat()
                checkpoint()
            canonical = canonical_url(page.url)
            if canonical in collected_urls:
                discovery_duplicates.append(
                    {"url": url, "duplicate_of": canonical, "stage": "resolved_program_url"}
                )
                continue
            program = extract_program(page, seed)
            if extractor:
                program = extractor.augment(program, page)
            programs.append(program)
            collected_urls.add(canonical)
        except (RetrievalError, ValidationError, ValueError, KeyError, OSError) as exc:
            failures.append({"url": url, "reason": str(exc)})
        checkpoint()
    unique, duplicates = [], []
    for program in programs:
        try:
            unique, repeated = deduplicate([*unique, program])
            duplicates.extend(repeated)
        except ValueError as exc:
            failures.append({"url": str(program.official_program_url), "reason": str(exc)})
            duplicates.append({"id": program.id, "stage": "conflict", "reason": str(exc)})
    programs = unique
    failures.extend(registry.excluded_sources)
    failures = list({(f["url"], f["reason"]): f for f in failures}.values())
    export = CollectionExport(
        generated_at=datetime.now(UTC),
        programs=programs,
        failures=failures,
        duplicates=duplicates + discovery_duplicates,
        notes=[
            "Local factual-data staging only; no right to republish source HTML/text is asserted.",
            "Source-supported extraction is not independently verified admission advice.",
            "Country and institution origin are unverified discovery metadata, explicitly marked.",
            "No real record is enabled for recommendations; no synthetic costs/indices are added.",
            "Replayed historical snapshots; no live retrieval."
            if replay_dir
            else "Live retrieval run.",
        ],
    )
    if not replay_dir:
        checkpoint()
    elif archive.get("recovery_note"):
        export.notes.append(archive["recovery_note"])
    export_json(export, output)
    return export
