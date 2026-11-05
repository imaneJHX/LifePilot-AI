# Real university program explorer

The existing `/explore` page now has two explicit modes:

- **Demo Recommendations** is the initial mode. It retains the 24 fictional
  programs, comparison tools, profiles and existing TOPSIS recommendations.
- **Real Programs** lists source-linked staging records. All 78 current records
  are displayed as **Not verified** and are not used for recommendations.

No programs were reviewed, promoted, recollected or edited as part of this change.
The real explorer does not send any request to the recommendation endpoint.

## Data and API

`GET /api/real-programs` reads the existing SQLAlchemy staging table
`real_university_programs`. It never imports the JSON export on a normal request
or at application startup. A database without staged rows returns an empty catalog;
it does not substitute fictional data or silently fall back to the export.

Optional query parameters are `country`, `university`, `study_area`, and `search`.
They can be combined; matching is case/accent insensitive. Keyword search covers
program, university, country, city, field and degree. For example:

```text
/api/real-programs?country=France&study_area=Artificial%20Intelligence
/api/real-programs?university=University%20of%20Glasgow&search=aerospace
```

The response contains `programs`, `count`, overall `total`, full-catalog filter
options (`countries`, `universities`, `study_areas`), `as_of_date`, and
`recommendation_eligible: false`. Each program has nullable source fields,
verification status, retrieval date and deadline status. Provenance/review payloads
remain in staging and are not duplicated into this listing response. Full staging
validation still runs before projection, including the requirement for a real
human review before a `verified` label. Invalid staging data returns a structured
503 error instead of silently accepting a forged review label.

The UI loads the catalog once when entering Real Programs and filters that snapshot
locally. Filter options come from the full database catalog, covering Belgium,
Canada, France, Germany, Italy, the Netherlands and the United Kingdom. These
filters are independent of the demonstration profile's country/field controls.

## Display rules

- Null fields show **Information unavailable**. No missing value becomes a zero,
  inferred requirement or invented duration.
- Teaching language and duration retain their original wording when present;
  canonical language/month values are only fallbacks when explicitly stored.
- Tuition is shown as expandable **published tuition information**, preserving
  applicant categories, fee periods, currencies and qualifications. No amount is
  selected automatically and no conversion to EUR is performed.
- Fully dated deadlines are **Expired deadline**, **Future deadline**, or
  **Deadline today**, based on the API's UTC `as_of_date`. This compares published
  calendar dates, not an invented deadline time or application eligibility.
- An undated deadline paragraph remains available under source details but is not
  classified as a future deadline. Expired dates are never advanced to a new year.
- Official program links open in a separate tab. Requirements and source details
  show the stored text, including missing-information labels.

All API responses retain `Cache-Control: no-store`. The PWA's existing worker
excludes API responses and continues to cache only its seven public resources.
The page remains client-rendered for Android static export compatibility.

## Test on your iPhone

Restart the existing backend and website processes after updating the source; a
running production process does not automatically reload these changes. From
`C:\coding\LifePilot-AI`, build the normal website:

```powershell
npm.cmd --prefix frontend run build
```

Terminal 1:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
npm.cmd --prefix frontend run start
```

Keep your existing local HTTPS helper running, or start it in Terminal 3 if stopped:

```powershell
npm.cmd --prefix frontend run pwa:https
```

Open your existing trusted `https://YOUR_PC_IP:3443/explore` address in Safari or
the installed LifePilot PWA. Use the PC's current LAN IPv4 address rather than
a previously assigned address.
The certificate must match the current IP. The existing HTTPS/certificate setup is
documented in [IOS_PWA.md](IOS_PWA.md).

1. Select **Real Programs** and expect 78 source-linked records, all Not verified.
2. Try each country and combine university, study-field and keyword filters.
3. Select France and check expired deadline labels. Current staging has 10
   explicit dates, all expired, and no future confirmed deadline.
4. Select Glasgow and expand tuition text to check fee-category context. Missing
   values elsewhere must say Information unavailable.
5. Check portrait/landscape scrolling, source links and dark/light themes.
6. Switch to **Demo Recommendations**: the 24 fictional programs and existing
   comparison/ranking journey remain available. Saved profiles are unchanged.
7. In Airplane Mode, a fresh navigation should use the generic offline page;
   neither real catalog API data nor student information is added to worker caches.

No new deployment or certificate changes are required.

## Automated checks

Backend tests use in-memory SQLite and cover the real database source, every
country, combined filters, null preservation, immutable review/eligibility flags,
invalid records, deadline boundaries and unchanged demo recommendation behavior.

Browser tests use `scripts/serve_test_api.py` to seed only the explicitly allowed
ignored `e2e.db` or `android-e2e.db`. This helper is not used by the application.
Real dataset fixtures are read without changing the export or the user's database.
Future/today/nullable UI examples are explicitly fictitious browser-only fixtures.

```powershell
# Backend
Set-Location C:\coding\LifePilot-AI\backend
..\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
..\.venv\Scripts\python.exe -B -m ruff check --no-cache app tests
..\.venv\Scripts\python.exe -B -m ruff format --check --no-cache app tests

# Isolated website tests; existing servers on 3000/8000 can stay running
Set-Location C:\coding\LifePilot-AI\frontend
$env:BACKEND_URL = 'http://127.0.0.1:8002'
npm.cmd run build
$env:CI = '1'
$env:PLAYWRIGHT_WEB_PORT = '3002'
$env:PLAYWRIGHT_API_PORT = '8002'
npm.cmd run test:e2e
Remove-Item Env:CI,Env:PLAYWRIGHT_WEB_PORT,Env:PLAYWRIGHT_API_PORT,Env:BACKEND_URL
```

For Android export regression tests, run `npm.cmd run android:test` from the project
root, then restore the normal website with `npm.cmd --prefix frontend run build`.
Do not build website and Android exports concurrently. The tests do not synchronize
or modify the native Android project. Browser checks on Windows use Edge with an
emulated iPhone viewport; installation and real Safari device behavior still need
the manual checklist above.
