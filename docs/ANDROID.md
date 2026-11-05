# LifePilot AI on Android

The website lives in `frontend/` (Next.js App Router). FastAPI lives in `backend/`.
Capacitor 8.6 is installed in the project root. The Android application ID remains
`com.lifepilot.ai`, and its display name remains **LifePilot AI**.

## Build modes

| Target | Command from project root | Result |
| --- | --- | --- |
| Website | `npm --prefix frontend run build` | Normal Next.js build with `/api/*` proxy to FastAPI |
| Docker website | Existing Docker Compose workflow | Existing standalone Next.js server |
| Android emulator | `npm run android:sync` | Static export in `frontend/out`, copied to `android/` |
| Android release | Set HTTPS API address, then `npm run android:sync:release` | Static export with deployed backend address, then Capacitor sync |
| Export browser tests | `npm run android:test` | Rebuilds an export for browser testing and runs six browser journeys |

Next.js supports this application's static export: there are no server actions,
dynamic server-only pages, or Next API handlers in its frontend. Export mode is
enabled only when `CAPACITOR_BUILD=true`. The Android build omits Next.js rewrites;
all API methods use the build-time `NEXT_PUBLIC_API_BASE_URL` instead. Website
builds keep their original relative `/api` proxy, including when an Android API
variable is still set in the shell.

`capacitor.config.json` uses `webDir: "frontend/out"`, relative to the project root.
It packages local files and does not load a remote website through `server.url`.
There is no Next.js or Python server bundled inside the APK. FastAPI must remain
reachable whenever the app needs profiles, programs, recommendations or chat.
Ollama, when used, is reached by FastAPI on the server, not directly by Android.

Android exports use trailing slashes and one HTML file per page. The small native
`NextExportWebViewClient` serves that page's `index.html` on initial navigation or
reload; Capacitor's default home-page fallback is intended for single-page apps.
The build also adds aliases for the incorrectly nested navigation-data filenames
emitted by Next.js 16.4 on Windows. Original generated files are retained. These
changes affect packaging and navigation, not recommendation logic or datasets.

## Install prerequisites

1. Install [Android Studio 2025.2.1 or newer](https://developer.android.com/studio).
2. In **Tools > SDK Manager**, install Android SDK Platform **36**, SDK Build-Tools,
   and Android SDK Platform-Tools. Install Android Emulator and an API 36 system
   image if you want an emulator. The generated app supports API 24 and newer.
3. Select Android Studio's bundled **JDK 21** as the Gradle JDK in
   **Settings > Build, Execution, Deployment > Build Tools > Gradle**.
4. Install project dependencies if needed:

```powershell
# Project root
npm.cmd ci
npm.cmd --prefix frontend ci
```

Node.js 22+ is required by Capacitor 8; Node.js 24 is installed in this workspace.
See [Capacitor's environment requirements](https://capacitorjs.com/docs/getting-started/environment-setup).

## Use the Android Studio emulator

In a separate terminal, from the project root, start FastAPI:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Then build/sync from another terminal:

```powershell
npm.cmd run android:sync
npm.cmd run android:open
```

The default Android API address is `http://10.0.2.2:8000`. Android Studio's emulator
uses [10.0.2.2 to reach the development PC's loopback address](https://developer.android.com/studio/run/emulator-networking).
`localhost` inside the app refers to the Android device, not the PC. The build script
rejects loopback URLs for a packaged app to catch that mistake.

`android:open` runs `cap open android`. Alternatively, select **Open** in Android
Studio and choose `C:\coding\LifePilot-AI\android` (the Gradle project, not the
frontend folder). Let Gradle synchronize, select an emulator, and click **Run**.
See [Capacitor's Android workflow](https://capacitorjs.com/docs/android).

## Use a physical phone

Use the PC's actual LAN IPv4 address, with the phone on the same reachable network:

```powershell
# Backend terminal
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000

# Build terminal: replace this example IP with your PC's IP
$env:NEXT_PUBLIC_API_BASE_URL = 'http://192.168.1.20:8000'
npm.cmd run android:sync
npm.cmd run android:open
```

Allow the local backend connection through Windows Firewall on your private
network. Confirm `http://YOUR_PC_IP:8000/api/health` opens in the phone's browser.
Enable USB debugging to run from Android Studio, or install a debug APK manually.
For a deployed server use its HTTPS base URL instead. Do not append `/api` to the
base URL; the shared API client appends it. A backend mounted under a path prefix
can use, for example, `https://example.com/lifepilot`.

The API address is embedded in the JavaScript at build time, is public, and cannot
contain passwords or tokens. Rebuild and sync after changing it. To restore the
emulator default:

```powershell
Remove-Item Env:NEXT_PUBLIC_API_BASE_URL -ErrorAction SilentlyContinue
npm.cmd run android:sync
```

## CORS and local HTTP

The packaged WebView's origin is **`https://localhost`**, regardless of whether the
API lives on the emulator host, a LAN machine, or a deployed server. FastAPI's
default CORS list, `.env.example`, and Docker Compose include this exact origin.
If you have an existing root `.env`, its `CORS_ORIGINS` overrides those defaults;
add the Android origin and restart FastAPI:

```dotenv
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000","https://localhost"]
```

The native app already has Android's INTERNET permission. Debug builds allow
cleartext HTTP and mixed-content requests to the development backend. Release
builds retain HTTPS-only transport: cleartext is disabled in the main manifest,
and the WebView's HTTP allowance runs only when the native app is debuggable.
No wildcard navigation allowlist or global production mixed-content switch is used.

## Generate a debug APK

After installing the prerequisites, from the project root:

```powershell
npm.cmd run android:sync
# For CLI Gradle only, if Java is not already on PATH:
$env:JAVA_HOME = 'C:\Program Files\Android\Android Studio\jbr'
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
npm.cmd run android:apk
```

If Android Studio is installed elsewhere, adjust `JAVA_HOME` to its JDK 21 path.
Opening the project in Android Studio normally creates `android/local.properties`
with the SDK path; the CLI can also discover it through `ANDROID_HOME`.
The APK command runs `android/gradlew.bat assembleDebug` on Windows
(`./gradlew assembleDebug` on Linux/macOS). Output:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

This debug APK is automatically signed with the development key. Android Studio
can also generate it through its **Build APK(s)** action. See
[Android's command-line build documentation](https://developer.android.com/build/building-cmdline).

## Generate a signed release APK

Configure the actual deployed backend first:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL = 'https://your-backend.example.com'
npm.cmd run android:sync:release
npm.cmd run android:open
```

The release export command requires an explicit HTTPS API URL. In Android Studio,
choose **Build > Generate Signed App Bundle or APK > APK**, choose/create your
keystore, select **release**, and finish the wizard. Android Studio reports the
output directory. Keep the signing key and passwords outside version control;
the generated Android ignore file excludes keystores. An unsigned `assembleRelease`
artifact alone is not an installable signed release. See
[Android's signing instructions](https://developer.android.com/studio/publish/app-signing).

## Test and return to the website

```powershell
# Root: isolated export + live API tests, desktop and mobile viewports
npm.cmd run android:test

# Package an address reachable by the device after browser testing
npm.cmd run android:sync

# Root: rebuild normal website assets before next start
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run start
```

Android and website builds share Next.js's intermediate `frontend/.next` directory;
do not build them concurrently. A website build does not remove the already copied
Android assets. Export browser tests use ports 3001/8001 and a separate ignored
`android-e2e.db`; website tests keep their existing ports and database. The export
tests exercise direct API URLs, CORS in a browser, saved profiles, ranking,
comparison, chat error/retry behavior and navigation-data availability. Backend
tests cover preflight authorization for every API method from `https://localhost`.
Chat success/failure remains mocked at the Ollama boundary in browser journeys.

These browser tests do not substitute for running the native app in an emulator
or phone. On November 3, 2026, no Java executable, Android SDK, or Android Studio
was available in this workspace's execution environment. APK compilation could
not proceed beyond the Gradle wrapper's Java prerequisite check. Native device
behavior and Gradle compilation require the Android toolchain above.
