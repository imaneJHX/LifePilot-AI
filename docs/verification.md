# Verification

Executed in this workspace on November 1, 2026, using Windows, Node.js 24.15.0, npm 11.12.1, and Python 3.12.3.

| Check | Result |
| --- | --- |
| Backend `python -m pytest -q` | **48 passed** |
| Backend `python -m ruff check app tests` | Passed |
| Backend `python -m ruff format --check app tests` | Passed |
| Python compilation (`compileall`) | Passed |
| Python dependency consistency (`pip check`) | Passed |
| Frontend `npm run typecheck` | Passed |
| Frontend `npm run lint` | Passed |
| Frontend `npm run build` | Passed; all seven App Router entries generated (including the not-found route) |
| Frontend `npm run test:e2e` | **4 passed**, desktop + mobile viewport in installed Microsoft Edge |
| `docker compose --env-file .env.example config --quiet` | Passed configuration validation |
| Local frontend HTTP readiness | HTTP 200; browser tests also use both live application servers |

The browser journeys create a profile through the real API, verify two hard-filtered ranked programs, change priorities, restore the profile after reload, filter the real catalog, open/close program details, compare programs, and exercise chat error/retry behavior. They also cover empty recommendations, light/dark preference persistence and horizontal overflow. Chat is mocked only at the Ollama-facing browser request for deterministic offline and successful retry scenarios; other requests use the live FastAPI backend and SQLite. Backend service tests independently mock Ollama's HTTP responses, model absence, connection errors and timeout cases. This does not verify inference by an actual Llama model.

Playwright runs the production Next.js build. It uses installed Edge on Windows, with desktop and emulated mobile viewports. Mobile coverage does not claim real iOS/Safari validation. Screenshots are generated in the ignored `frontend/test-results/` directory and were visually inspected for the landing page and dashboard. Initial browser runs exposed two ambiguous test selectors, which were corrected; the final runs passed. Windows process-tree cleanup required execution outside the restrictive sandbox; Playwright then exited successfully and stopped its owned servers.

## Runtime limits

- Docker CLI is installed, but the daemon was not running. Images were not built and PostgreSQL/container runtime behavior was not exercised. The CLI also warned that the sandbox could not read the host Docker configuration; static Compose validation still exited successfully.
- Ollama is not available on the command path. No model was installed or downloaded, and live Llama inference remains unverified. The rest of the application runs without it.
- Backend tests and the local browser journeys use SQLite. PostgreSQL is configured through the SQLAlchemy psycopg driver and Compose, but has not been runtime-tested here.
- The installed Starlette TestClient emits a deprecation warning for its HTTPX adapter. Tests pass; no extra HTTPX2 dependency was introduced solely to hide that warning.
- Authentication, shared-user authorization, migrations, RAG, real program data, agent orchestration and predictive ML are outside Phase 1. The application is a local demonstration, not a hardened public deployment.

Exact local, Docker Desktop and Ollama installation/launch commands are in the root [README](../README.md).

## Android packaging verification — November 3, 2026

Environment: Windows, Node.js 24.15.0, Next.js 16.4.3, Capacitor 8.6.0.
See [Android setup and APK instructions](ANDROID.md).

| Check | Result |
| --- | --- |
| Backend `pytest -q` | **211 passed, 2 xfailed**; expected failures belong to the existing TOPSIS audit |
| Backend Ruff lint and format checks | Passed |
| Frontend lint and typecheck | Passed |
| Android static export | Passed; all application pages exported |
| Static-export browser tests | **6 passed**; desktop and mobile viewports in Edge |
| Android platform creation and final `android:sync` | Passed |
| Copied Android web assets | **66 export files verified byte-for-byte** |
| Final packaged API address | `http://10.0.2.2:8000` (Android Studio emulator development backend) |
| Normal website production build | Passed; API proxy retained even with Android API environment variable set |
| Existing website browser tests | **4 passed**; desktop and mobile viewports |
| Invalid build configurations | Loopback API URLs, HTTP release URLs and release exports without an explicit API URL rejected |
| Docker Compose static configuration | Passed; host Docker config access warning remains; container runtime not exercised |
| Recommendation and dataset preservation | SHA-256 aggregate unchanged for TOPSIS, recommendation service, catalog loader and every file under `data/` |
| APK/native compilation | Blocked at Gradle prerequisite check: Java unavailable; Android SDK/Studio not found in standard locations |

The static suite runs the exported files with Python's static HTTP server and a
separate live FastAPI process/database, without a Next.js proxy. It exercises
profile creation/restoration, recommendations, catalog exploration/comparison,
chat error/retry behavior, navigation and exported RSC file availability. Chat
inference is mocked in the browser journeys; live Ollama inference was not checked.
Backend tests cover CORS preflights for every API route from `https://localhost`
and rejection of an unrelated origin.

Testing exposed and resolved Windows-specific nested RSC export filenames, and
verified active navigation with exported trailing-slash routes. Test selector
issues involving a hidden mobile sidebar and normalized link URLs were corrected;
the final static suite passed in full. Windows browser suites ran with permission
to clean up their own server process trees.

The final synchronized assets target the emulator, and the final `.next` directory
is a normal website build. No signing key or APK was generated. Native Java
compilation, Android manifest merging, emulator/device execution, release signing,
and on-device HTTP/TLS behavior remain unverified until the Android toolchain is
installed. The two pre-existing numerical audit failures remain expected; ranking
algorithms and datasets were not modified.

## iPhone PWA verification — November 3, 2026

The [iOS PWA guide](IOS_PWA.md) contains the Windows, LAN, local HTTPS, Safari
installation and future deployment instructions. Nothing was deployed.

| Check | Result |
| --- | --- |
| Backend tests | **215 passed, 2 xfailed**; existing TOPSIS audit expected failures retained |
| Backend Ruff lint/format | Passed |
| Frontend lint/typecheck | Passed |
| Website production build | Passed |
| Website + PWA browser tests | **10 passed** across desktop and iPhone viewport in Edge |
| Final focused PWA suite | **6 passed**, including phone landscape navigation after the final responsive adjustment |
| Existing Android export browser tests | **6 passed**, without Capacitor synchronization |
| Standalone website build | Passed; Docker runtime updated to copy public PWA assets |
| HTTPS helper smoke test | Passed: manifest, worker headers and same-origin FastAPI health through local TLS |
| Script syntax checks | Passed for service worker, HTTPS helper and icon generator |
| Android preservation | SHA-256 aggregate unchanged for all native files/assets, Capacitor config, root package files and Android build/test scripts |
| Algorithm/data/endpoint preservation | SHA-256 aggregate unchanged for ranking services, all datasets and backend API route files |

PWA tests verify manifest and legacy iOS standalone metadata, actual PNG dimensions,
service-worker headers, registration/control, offline navigation and reconnection,
exactly seven generic resources in Cache Storage, absence of student fields from
that cache, network-only API behavior, API `no-store` responses, theme persistence,
touch targets, no page overflow, and scrollable three-program comparison.

Two integration issues were found and corrected: Next.js 16 emits the generic
mobile-web-app-capable tag, so the legacy Apple tag is added explicitly; proxy
configuration alone did not preserve API cache headers, so FastAPI now supplies
`Cache-Control: no-store` without changing endpoint paths or payloads. The complete
website/PWA suite passed after both fixes. The service worker is disabled in the
Android export, which remains compatible with its existing browser journeys.

The HTTPS smoke test used a disposable self-signed localhost certificate and a
test-only certificate validation bypass. No OS trust store was changed. The test
key and certificate were removed afterward. The user-facing guide requires a
trusted mkcert certificate on the real iPhone; it does not recommend bypassing TLS
errors. HTTPS helper processes and browser test servers were stopped after checks.

These checks do not validate installation or safe-area/keyboard behavior on real
iPhone Safari. That manual checklist is in the guide. Live Ollama inference and
Docker container runtime remain unverified; no push notification integration,
student data offline storage, or background submission queue was added.

## Real-program explorer — November 5, 2026

Implemented a separate read-only `/api/real-programs` endpoint and Real Programs
mode in `/explore`. See [the feature and iPhone test guide](REAL_PROGRAM_EXPLORER.md).
Normal application startup does not import the export. The existing demonstration
catalog, profile contracts, TOPSIS code and recommendation routes remain separate.

| Check | Result |
| --- | --- |
| Full backend suite | **241 passed**, no expected failures |
| Backend Ruff lint/format, including the isolated browser-test API helper | Passed |
| Frontend lint/typecheck | Passed |
| Website, PWA and explorer browser suite | **16 passed**, desktop and iPhone viewport in Edge |
| Android static-export browser suite, including the real explorer | **12 passed** |
| Normal and standalone website builds | Passed |
| Static Android export build | Passed; native project was not synchronized |
| Data/ranking/PWA/native Android preservation | SHA-256 aggregates unchanged for all datasets, ranking services, demo API contracts, PWA assets/configuration and native Android files |
| User database preservation | Saved profile and all 78 staged row payloads unchanged, checked through read-only SQLite |

Backend coverage includes an empty database (no JSON fallback), deletion from an
isolated database changing the result count, all seven countries, combined
case/accent-insensitive filters, nullable source values, no-store headers, rejection
of unsupported verified labels or ranking eligibility, date-only deadline status,
and identical demo recommendations before/after reading the real catalog.

Frontend coverage uses the 78 existing records through an isolated database and
live endpoint. It checks seven-country filtering, university/field/keyword
combinations, original applicant-specific tuition text, official links, missing
values, review labels, no ranking requests, no API worker caching, portrait and
landscape overflow, error/retry/empty states, and switching back to demo mode.
Future/today/undated UI cases are explicitly fictitious mocked fixtures and were
never saved to staging. Initial tests exposed two incorrect test assumptions
(a management program was excluded by the engineering filter, and Next.js adds its
own route-announcer alert); assertions were corrected and both suites passed.

Browser-test fixture imports target only ignored `e2e.db`/`android-e2e.db` through
an explicit filename allowlist. The user's running servers were left in place;
website browser tests used isolated ports 3002/8002. The final build restores normal
website mode and its usual backend proxy target. Restart the existing API and
website processes to serve the new source to the iPhone.

Real iPhone Safari execution and native APK compilation were not performed in this
change. Existing PWA registration/cache policy and Android native assets were
preserved, no university information was invented or approved, and nothing was
deployed.
