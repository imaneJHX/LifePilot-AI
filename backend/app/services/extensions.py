"""Phase-2 boundaries. No models are downloaded or orchestration started in Phase 1."""

from typing import Protocol


class EvidenceRetriever(Protocol):
    async def retrieve(self, query: str, limit: int = 5) -> list[dict]:
        """Return source text, official URL, retrieval time and verification metadata."""
        ...


class DocumentIngestor(Protocol):
    async def ingest(self, source_url: str) -> str:
        """Validate provenance, chunk documents, and return an ingestion identifier."""
        ...


class DecisionAgent(Protocol):
    async def run(self, profile_id: str, question: str) -> dict:
        """Orchestrate tools without mixing agent output into deterministic ranking."""
        ...
