# LifePilot AI on iPhone as a PWA

LifePilot uses its existing Next.js website on iPhone. No Mac, Xcode, native iOS
project, or App Store upload is needed for Safari Home Screen installation.
Nothing has been deployed. Android's native project, Capacitor configuration and
build scripts are preserved.

## What was added

- `frontend/public/manifest.webmanifest`: app name, stable ID, standalone display,
  start URL, scope, colors and icons.
- `frontend/public/icons/`: 192px and 512px PNGs, a maskable 512px icon, and a 180px
  Apple touch icon derived from the existing compass brand. Regenerate with
  `npm.cmd --prefix frontend run icons:generate`.
- Root layout metadata: iOS standalone capability, Apple icon/title/status bar,
  light/dark theme colors, and `viewport-fit=cover` without disabling zoom.
- `frontend/public/sw.js`: a small service worker with a generic offline fallback.
- iPhone spacing for safe areas, 44px touch targets, 16px form controls to avoid
  focus zoom, readable dashboard cards, and horizontal comparison scrolling with
  pinned row labels. Existing dark/light controls also update the browser color.
- `scripts/serve-pwa-https.mjs`: local HTTPS forwarding to Next.js for iPhone tests.

## Start on Windows and test your local network

Use PowerShell in `C:\coding\LifePilot-AI`. Install dependencies once if needed:

```powershell
Set-Location C:\coding\LifePilot-AI
npm.cmd --prefix frontend ci
# If the Python environment has not been created yet:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
```

Terminal 1 — keep FastAPI on the PC's loopback interface:

```powershell
Set-Location C:\coding\LifePilot-AI
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Terminal 2 — build and start the production website:

```powershell
Set-Location C:\coding\LifePilot-AI
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run start
```

`start` listens on `0.0.0.0:3000`. Run `ipconfig` and find your Wi-Fi adapter's
IPv4 address. Put the phone and PC on the same private Wi-Fi network, then visit
`http://YOUR_PC_IP:3000` in Safari. Use your actual IP, not `localhost` or `0.0.0.0`.

The browser sends **relative `/api/*` requests to the website's own origin**.
Next.js forwards them to FastAPI on the PC. FastAPI does not need to listen on
`0.0.0.0`, and the phone does not need port 8000 or additional backend CORS origins.
`BACKEND_URL`, when needed, is a server-only setting in `frontend/.env.local`;
website builds ignore the Android `NEXT_PUBLIC_API_BASE_URL` override.

If Windows Firewall asks about Node.js, allow your **private** network. If a rule
is needed, an Administrator PowerShell can add a rule restricted to the local subnet:

```powershell
New-NetFirewallRule -DisplayName 'LifePilot local PWA testing' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 3000,3443 -Profile Private -RemoteAddress LocalSubnet
```

Guest Wi-Fi client isolation, a VPN, or a public network profile can prevent access.
Keep port 8000 private. These are local test servers; do not forward router ports.

HTTP on a LAN IP is useful for checking layout and API connectivity. **Use trusted
HTTPS for the service worker, offline behavior, and complete PWA testing on iPhone.**
Windows loopback addresses are treated as secure contexts by browsers, but an
iPhone's HTTP LAN URL is not.

For ordinary coding, the existing `scripts/dev.py` remains unchanged and local-only;
`npm.cmd --prefix frontend run dev` can also expose the development UI on the LAN.
The service worker deliberately does not register in Next.js development mode.
Use the production commands above for installation and offline tests.

## HTTPS option: a locally trusted certificate

This option stays on your local network and does not create a public tunnel.
Install [mkcert](https://github.com/FiloSottile/mkcert) on Windows:

```powershell
winget install --id FiloSottile.mkcert -e
```

Open a new PowerShell after installation. Create the development certificate with
your **actual PC IP**; the example value below must be replaced:

```powershell
Set-Location C:\coding\LifePilot-AI
$pcIp = '192.168.1.20'
New-Item -ItemType Directory -Path .certificates -Force | Out-Null
mkcert -install
mkcert -cert-file .certificates/lifepilot.pem -key-file .certificates/lifepilot-key.pem localhost 127.0.0.1 $pcIp
```

The `.certificates/` directory is ignored by Git and excluded from Docker contexts.
Never copy a private key or `rootCA-key.pem` to your phone. Transfer only mkcert's
public root certificate. To make a temporary download directory containing only
that public certificate:

```powershell
$caRoot = mkcert -CAROOT
New-Item -ItemType Directory -Path .certificates/public-ca -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $caRoot 'rootCA.pem') -Destination .certificates/public-ca/lifepilot-rootCA.cer
.\.venv\Scripts\python.exe -m http.server 8765 --bind 0.0.0.0 --directory .certificates/public-ca
```

Open `http://YOUR_PC_IP:8765/lifepilot-rootCA.cer` in Safari. Allow this temporary
port on your private network only if Windows asks. Install the downloaded profile
in **Settings > General > VPN & Device Management** (or **Profile Downloaded**),
then enable it in **Settings > General > About > Certificate Trust Settings**.
Stop the certificate download server with Ctrl+C afterward. See
[Apple's root certificate trust instructions](https://support.apple.com/102390).

With the backend and production Next.js server from Terminals 1 and 2 still
running, start Terminal 3:

```powershell
Set-Location C:\coding\LifePilot-AI
npm.cmd --prefix frontend run pwa:https
```

Open **`https://YOUR_PC_IP:3443`** in Safari. The certificate must be trusted and
match that IP; bypassing a certificate warning is not the same as trusting it.
If your PC's IP changes, regenerate the leaf certificate with the new IP and restart
the HTTPS helper. The Home Screen app should use the same stable HTTPS address.

The helper reads `.certificates/lifepilot.pem` and `lifepilot-key.pem`, listens on
3443, and forwards to the fixed loopback Next.js server on port 3000. Optional
variables are `PWA_CERT_PATH`, `PWA_KEY_PATH`, and `PWA_HTTPS_PORT`. It streams
requests/responses and does not store them. No OS trust configuration or firewall
rules are changed automatically by this project.

## Install with Safari

1. Open the trusted HTTPS address in **Safari** and wait for the page to load.
2. Open **Share** (through the page menu on versions that put it there).
3. Choose **Add to Home Screen**. If absent, check **Edit Actions**.
4. Keep **Open as Web App** enabled when offered, then tap **Add**.
5. Open **LifePilot AI** from its Home Screen icon. It should launch in standalone
   mode with the application icon and respect the safe areas.

Safari installation does not rely on Chromium's `beforeinstallprompt` event.
See [Apple's Safari installation guide](https://support.apple.com/guide/iphone/iphea86e5236/ios)
and [WebKit's Home Screen behavior](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/).
Menu wording depends on your iOS version. A plain HTTP bookmark does not validate
offline PWA support.

## Offline behavior and privacy

The service worker registers only in production website builds on a secure origin.
It is disabled in `CAPACITOR_BUILD=true` exports, so it does not take over Android's
local WebView routing.

Only seven explicitly listed public resources enter Cache Storage: the generic
offline HTML and CSS, manifest, and four PNG icons. App pages, Next.js RSC payloads,
JavaScript bundles, API responses, chat messages, profiles and rankings are not
cached by the worker. All API responses also receive `Cache-Control: no-store`
from FastAPI, including profile responses and validation errors. No background
request queue or offline form submission is added.

A failed full-page navigation shows the offline page, which asks you to reconnect.
The fallback requires one successful online worker installation; browsers may
evict site storage, so it is not a durable offline database.
An already open page may still show its current in-memory data; API requests fail
normally with the existing error/retry behavior. Offline editing, recommendations
and Ollama inference are not supported. The existing browser preference and saved
profile-ID pointer remain unchanged; they do not contain the profile's fields or
chat transcript. Safari's own session storage behavior is outside the worker cache.

The offline page follows the device's light/dark preference. Online pages retain
the saved manual theme. Worker updates wait for existing app windows to close;
they never force a reload while you are filling a form. Bump `CACHE_NAME` in
`public/sw.js` whenever changing a precached resource. Old LifePilot public caches
are removed when the new worker activates; unrelated caches are preserved.

## Test the PWA

Stop other servers on ports 3000/8000 before browser tests. From the project root:

```powershell
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run build
$env:CI = '1'
npm.cmd --prefix frontend run test:e2e
Remove-Item Env:CI

Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m ruff check app tests
..\.venv\Scripts\python.exe -m ruff format --check app tests
```

The full browser suite includes the existing journeys plus PWA metadata/icon
checks, real service-worker registration, offline navigation/recovery, Cache
Storage privacy assertions, API no-store headers, three-program comparison,
touch target sizes and theme persistence. Run only PWA checks with
`npm.cmd --prefix frontend run test:pwa`. Tests launch an isolated database and
their own servers. Windows uses Edge; a Chromium iPhone viewport is not a real
Safari test. Live Ollama inference remains mocked in browser journeys.

Android export compatibility can be checked without changing the native project:

```powershell
# Project root; do not run concurrently with a website build or server
npm.cmd run android:test
# Restore the normal website build afterward
npm.cmd --prefix frontend run build
```

This builds and tests the frontend export; it does not run Capacitor sync or modify
`android/`. Existing Android configuration, native files and copied assets are left
unchanged by this PWA task.

On your iPhone, manually check:

1. HTTPS opens without a certificate warning; Home Screen launch has no Safari bar.
2. Profile creation, restoration, ranking adjustments and program comparison work.
3. Rotate to landscape and check the notch, home indicator, navigation and table.
4. Focus a form input; text stays readable and pinch zoom remains available.
5. Toggle both themes and reopen the app.
6. After an online visit, enable Airplane Mode with Wi-Fi off, close/reopen the app,
   and confirm the generic offline page shows no student information. Reconnect
   and use **Try again**. An existing in-memory page can remain visible until reload.

In desktop DevTools, inspect **Application > Manifest / Service Workers / Cache
Storage**. There should be exactly the seven public cached resources. For a fresh
installation test, unregister this site's worker and clear its site data (this also
removes its saved browser preferences/profile pointer).

## Deploy later

Use a stable HTTPS domain and a production TLS certificate. Prefer one origin for
the website and `/api/*`; Next.js forwards to a private FastAPI address configured
through `BACKEND_URL` before the production build. Keep Ollama behind FastAPI.
Run the normal website build, not the Capacitor export. The existing standalone
Docker build now copies `public/`, so the manifest, worker, offline page and icons
are included in its runtime image.

Preserve the worker's JavaScript content type and update headers, serve the manifest
and icons at their declared paths, and keep `/api/*` out of proxy/CDN caches. A
static-only host would need an explicit same-origin `/api` reverse proxy; the
Android export's emulator URL is not an iPhone deployment setting. Add the identity
and ownership controls documented in the main README before shared production use.
Run browser/API checks and the real-device checklist at the final HTTPS origin.
No hosting, tunnel, DNS, certificate trust changes, or public deployment was performed.
