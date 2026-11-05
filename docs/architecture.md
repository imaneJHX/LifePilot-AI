# Architecture and decisions

The Phase 1 application is a local demonstration with production-oriented boundaries. It is not a public multi-user service: authentication, authorization, migrations, throttling and operational hardening remain future work.

## Request path

Browser → Next.js same-origin `/api/*` rewrite → FastAPI router → schema → service/repository → SQLAlchemy or fixture catalog. Ollama is called asynchronously only by the chat endpoint. API docs are at `/docs` on FastAPI.

The frontend uses App Router route groups, reusable shell and cards, a typed API client, strict TypeScript, Tailwind's CSS pipeline, Framer Motion, Lucide and a Recharts comparison. No remote fonts or image services are needed at runtime or build time. CSS variables implement both themes. Motion respects the system preference. Native dialogs provide focus containment and Escape dismissal.

## Persistence and deployment

PostgreSQL is the Docker Compose database, with a persistent volume and readiness dependencies. SQLite is the zero-service local default. Both use the same SQLAlchemy repository. Profiles are immutable snapshots: editing creates a new profile ID. The browser stores only the current ID. Forgetting removes the browser pointer, not server records. Chat history lives only in component memory and is sent with each request; it is not stored in the database.

Schema creation at startup is appropriate for this one-table demonstration. Adopt Alembic migrations before modifying deployed schema. Use per-user ownership checks before exposing profile lookup to multiple users. A UUID is an identifier, not an authorization mechanism. Backend database work uses sync SQLAlchemy sessions in FastAPI's worker pool. Catalog and ranking are small, deterministic operations.

Configuration is environment-based, with the root `.env` read independently of the process working directory. The frontend's `BACKEND_URL` is baked into Next rewrites at build time. Changing a production target requires rebuilding. Docker binds app ports to loopback; PostgreSQL is internal-only. Neither service runs as root in its final container.

## Decision model

Only the fixture dataset is used. Every institution, program, financial figure and numerical index is fictional. Real city/country names serve as illustrative geography. Programs match the exact field and any selected countries. Annual tuition plus annual living cost must not exceed the supplied cap. All amounts are EUR; no conversion is performed. Costs are annual rather than full-degree totals.

The pure TOPSIS service takes a nonnegative finite matrix and configurable benefit/cost criteria. It normalizes column vectors and priority weights, constructs ideal/worst points, and calculates Euclidean relative closeness. Empty candidates return an empty ranking. Zero columns contribute zero. Identical and single alternatives score 0.5, and stable input order resolves ties. Scores depend on the available alternatives. No probability or admission estimate is computed.

Academic alignment is **100 − |synthetic academic index − (60 + 10 × GPA)|**. Career and experience indices are arbitrary fixture values. GPA is constrained to a 4.0 scale. This formula illustrates personalized decision criteria and has no empirical validation. Goals are assistant context only; they do not affect ranking. Explanation ordering uses the difference between anti-ideal and ideal weighted distance components, with actual input values and weights exposed. It is a deterministic tradeoff explanation, not causal feature attribution.

The API and UI label the results as decision-ranking scores. Budget, field and country are hard constraints. Ranking priorities can be changed temporarily on the dashboard or saved through a new profile snapshot.

## AI boundary

An `httpx.AsyncClient` calls Ollama's `/api/chat` with `stream=false`, bounded messages and output tokens, a configurable model and bounded timeout. Connection failure, model absence, timeout and invalid output have distinct structured errors. Startup, catalog access and ranking never contact Ollama. The system prompt identifies synthetic data and the absence of web tools. LLM output is untrusted plain text; no model-supplied HTML is rendered and no tools execute from it.

All supported catalog records for the user's field are supplied as small structured context. This is not RAG or verified retrieval. Set the Ollama URL to a server you control; profile context and messages go to that server. The application does not send queries to a hosted model by default.

## Extension points (not implemented)

`services/extensions.py` defines boundaries for `EvidenceRetriever`, `DocumentIngestor` and `DecisionAgent`. Future implementations may use LangChain, Sentence Transformers, FAISS and LangGraph. Keep these optional dependencies in separate extras and avoid loading models at API startup. Store official URLs, source text, retrieval times and verification status before promoting any record from synthetic to real.

AHP can supply criterion weights through a separate pairwise-comparison adapter with consistency checks. TOPSIS already accepts the resulting weight vector. SHAP belongs with a validated future predictive model; it should not be represented as an explanation for TOPSIS. Authentication should establish request-scoped identity and repository ownership filters before any shared deployment.

Official API references consulted: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), [FastAPI errors](https://fastapi.tiangolo.com/tutorial/handling-errors/), [Ollama chat](https://docs.ollama.com/api/chat).
