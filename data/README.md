# Data included in the public repository

`sample/universities.json` contains 24 explicitly fictional demonstration programs.
It is the public catalog used by the existing explorer, comparison tools and TOPSIS
recommendations. Sample names, costs, curricula and indices are illustrative.

## Local research artifacts

The following directories are intentionally ignored, except for empty `.gitkeep`
files where present:

- `raw/`: downloaded official HTML, policy/robots snapshots and request receipts.
- `processed/`: the 78-record real-program export, reports, diagnostics and RAG text.
- `sources/`: the locally reviewed collection registry and source-policy decisions.

The current registry labels the university material `local_research_only`. The
processed export includes extensive source quotations, unreviewed academic facts,
fee paragraphs and application text; RAG documents reproduce that material. A URL
or a successful extraction is not an authorization to redistribute the corpus.
These files are kept private pending a separate evidence and publication review.
The original local files remain untouched by Git ignore rules.

All 78 current records require verification. The local database also contains
student profile snapshots and must never be committed. Quality reports and
diagnostics are excluded with the data they describe, rather than being treated as
automatically safe summaries.

## Behavior without private data

The website, demo recommendations, profiles, PWA and Android source remain usable
without the research files. The read-only real explorer shows an empty catalog
until its database is explicitly populated with authorized records. It never
silently imports a JSON file or promotes a record to verified status.

Data-specific integration tests explicitly skip when the optional export is absent.
Other tests use fictional records or synthetic HTTP fixtures. The browser-test API
helper seeds only allowed ignored test databases, and runs with an empty real
catalog when the export is not supplied.

The collector code is public, but its default private registry is not included.
Running a collection requires your own reviewed source configuration. Do not run
bulk collection or publish a corpus on the assumption that a public URL grants
reuse permission. The existing validators preserve evidence, dates and review
status; they do not invent missing facts or grant publication rights.
