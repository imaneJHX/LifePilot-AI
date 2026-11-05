# GitHub publication review

Repository name: **LifePilot-AI**. This preparation is local only; it does not
create a GitHub repository, configure a remote, commit, or push files.

A local Git repository was initialized on `main` to validate ignore rules. Its
history and staging area remain empty, and it has no remote. No local application,
database, key, dataset or separate Expo repository was deleted.

## Commit boundary

| Include | Keep private |
| --- | --- |
| `backend/app/`, backend tests and dependency manifests | Local profile/staging/test databases and SQL dumps |
| `frontend/src/`, public PWA assets and frontend tests | Environment files, credentials and registry authentication configuration |
| Capacitor config and native Android source/Gradle wrapper | TLS certificates/private keys, signing keys and SDK-local paths |
| Package manifests and lockfiles | `node_modules/`, virtual environments and tool caches |
| Dockerfiles, sanitized `.env.example` files and build scripts | Next.js/native build output, generated Android web assets, APKs/AABs |
| Fictional `data/sample/` catalog and public setup guides | University raw snapshots, source registry, processed exports, RAG text and quality/diagnostic reports |
| This review and generic architecture/verification notes | Historical local TOPSIS/research reports containing profile context or source extracts |
| Explicit fictional regression examples | Browser screenshots/traces, personal documents and backups |

`MyMobileApp/` is a separate experimental Expo repository, not an application
dependency. It remains on disk and is excluded from the main publication scope.

The existing `.gitignore` exceptions that exposed processed university exports
have been removed. Ignore rules do not delete files and do not make previously
published material private. Inspect the candidate list before every commit.

## Findings

- The project root initially had no Git repository and therefore no root commit
  history to rewrite.
- The separate Expo repository had one reachable commit. Its 52 reachable file
  blobs were inspected for common credential signatures; none were found. Its
  author metadata and files remain outside the main repository's commit scope.
- A real local TLS private key and local databases were present. They are excluded;
  secret values and student records are not reproduced in this report.
- Credential-looking strings in included environment examples and retrieval tests
  are explicit placeholders, interpolation expressions or deliberately invalid
  test inputs. They are not live credentials.
- Personal LAN addresses were removed from the public explorer instructions.
  Android emulator aliases and clearly marked example addresses remain valid
  configuration documentation.
- The original TOPSIS regression inputs are retained as a fixed synthetic-catalog
  example, with live-profile attribution removed. The historical local audit
  narrative remains private.
- No public redistribution authorization for the university corpus is recorded in
  the local registry. The source/derived artifacts remain excluded.

The scan checks project-owned text and reachable history for common key/token,
private-key and credential patterns, plus local identity/address disclosures.
Generated artifacts and binary files are excluded from publication rather than
claimed to be free of personal information. Dependency and virtual-environment
contents are outside the source review. Pattern scanning cannot guarantee that an
arbitrary future credential or personal record will be recognized.

## Review before the first commit

```powershell
git status --short
git ls-files --others --exclude-standard
git add --dry-run .
```

Check that `.env`, keys, databases, private data and the Expo experiment do not
appear. After you choose to stage files, inspect `git diff --cached --stat`,
`git diff --cached --check`, and the actual staged diff before committing. This
task does not stage files or add a remote. Do not run a push until you have reviewed
the exact commit contents and selected the intended GitHub repository visibility.
Review the name/email you intend to use as the public commit author before the
first commit. No author identity was set or changed during this preparation.

A project license still needs an explicit owner decision; no license was assigned
automatically. The public README describes a reproducible checkout without the
private corpus, and the optional dataset-specific tests report skips honestly.

## Validation performed

- 185 commit-candidate files inspected after applying repository ignore rules.
- No high-confidence private-key or common provider-token signature in that set.
- The only email-like included source reference is deliberately invalid user-info
  in a retrieval rejection test. Password-like examples are documented placeholders.
- All local Markdown targets in the candidate set resolve to included files.
- The nested Expo repository's complete object store contains 52 file blobs; no
  common credential signatures were found, including its local repository config.
- Full local backend suite: **241 passed**. Ruff lint and formatting passed.
- Public-only backend snapshot: **227 passed, 14 explicitly skipped** because the
  private export is absent. Its API starts, serves 24 demo programs, and returns an
  empty real catalog without the research files.
- Frontend lint, TypeScript checks and production build passed.

The public-only snapshot and candidate manifest are kept under the ignored
`.publication-private/` directory for local review. No private file was temporarily
removed to perform the clean-checkout checks. Source runtime, datasets, native
Android files and stored profiles are checked separately for preservation.
