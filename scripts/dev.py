"""Start both local development servers. Run with the project virtualenv Python."""

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    node = shutil.which("node")
    next_cli = ROOT / "frontend" / "node_modules" / "next" / "dist" / "bin" / "next"
    if not node or not next_cli.exists():
        sys.exit("Install Node.js, then run npm install in frontend/ first.")
    processes = []
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--reload",
                    "--host",
                    "127.0.0.1",
                ],
                cwd=ROOT / "backend",
                creationflags=flags,
            )
        )
        processes.append(
            subprocess.Popen(
                [node, str(next_cli), "dev", "--hostname", "127.0.0.1"],
                cwd=ROOT / "frontend",
                creationflags=flags,
            )
        )
        print("LifePilot: http://localhost:3000 | API: http://localhost:8000/docs", flush=True)
        print("Press Ctrl+C to stop both servers.", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                if sys.platform == "win32":
                    # Stop only this launcher's owned process trees (including reload workers).
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        creationflags=flags,
                        check=False,
                    )
                else:
                    process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
