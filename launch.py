#!/usr/bin/env python3
"""Cross-platform one-click launcher for the Fantasy Lineup Optimizer."""

from __future__ import annotations

import atexit
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import venv
import webbrowser
from pathlib import Path

# Unbuffered-ish progress output when launched by double-click wrappers
try:
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
FRONTEND_DIR = ROOT / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"
HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"
MARKER = VENV_DIR / ".deps_installed"


def pause_on_error() -> None:
    if sys.platform == "win32":
        input("\nPress Enter to close this window...")


def fail(message: str, code: int = 1) -> None:
    print(f"\nERROR: {message}", file=sys.stderr)
    pause_on_error()
    sys.exit(code)


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def venv_python() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def venv_uvicorn() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "uvicorn.exe"
    return VENV_DIR / "bin" / "uvicorn"


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print(f"> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or ROOT, env=env)
    if result.returncode != 0:
        fail(f"Command failed ({result.returncode}): {' '.join(cmd)}", result.returncode)


def ensure_python() -> None:
    if sys.version_info < (3, 9):
        fail(
            f"Python 3.9+ is required. This interpreter is "
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}."
        )


def ensure_node() -> None:
    if which("node") is None or which("npm") is None:
        fail(
            "Node.js 18+ and npm are required for the first frontend build.\n"
            "Install from https://nodejs.org/ then run this launcher again.\n"
            "(Later launches only need Python once frontend/dist exists.)"
        )


def ensure_venv() -> None:
    py = venv_python()
    if not py.exists():
        print("Creating virtual environment (.venv)...")
        venv.create(VENV_DIR, with_pip=True)
    if not py.exists():
        fail(f"Could not create virtual environment at {VENV_DIR}")


def ensure_python_deps() -> None:
    py = str(venv_python())
    needs_install = not MARKER.exists() or (
        REQUIREMENTS.exists() and MARKER.stat().st_mtime < REQUIREMENTS.stat().st_mtime
    )
    if not needs_install:
        # Quick sanity check that uvicorn is importable
        check = subprocess.run(
            [py, "-c", "import uvicorn, fastapi"],
            cwd=ROOT,
            capture_output=True,
        )
        if check.returncode == 0:
            return
    print("Installing Python dependencies...")
    run([py, "-m", "pip", "install", "--upgrade", "pip"])
    run([py, "-m", "pip", "install", "-r", str(REQUIREMENTS)])
    MARKER.write_text("ok\n", encoding="utf-8")


def ensure_frontend_build() -> None:
    if DIST_DIR.exists() and (DIST_DIR / "index.html").exists():
        return
    ensure_node()
    print("Installing frontend dependencies and building UI...")
    npm = "npm.cmd" if sys.platform == "win32" and which("npm.cmd") else "npm"
    run([npm, "install"], cwd=FRONTEND_DIR)
    run([npm, "run", "build"], cwd=FRONTEND_DIR)
    if not (DIST_DIR / "index.html").exists():
        fail("Frontend build finished but frontend/dist/index.html was not found.")


def wait_for_server(timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    health = f"{URL}/api/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.25)
    return False


def open_browser_when_ready() -> None:
    if wait_for_server():
        print(f"Opening {URL} in your default browser...")
        webbrowser.open(URL)
    else:
        print(
            f"Server did not become ready in time. Open {URL} manually once it is up.",
            file=sys.stderr,
        )


def port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def start_server() -> int:
    if not port_available(HOST, PORT):
        fail(
            f"Port {PORT} is already in use on {HOST}.\n"
            f"Stop the other process using that port, then run this launcher again.\n"
            f"Or open {URL} if the app is already running."
        )

    uvicorn = venv_uvicorn()
    py = venv_python()
    if uvicorn.exists():
        cmd = [
            str(uvicorn),
            "backend.app.main:app",
            "--host",
            HOST,
            "--port",
            str(PORT),
        ]
    else:
        cmd = [
            str(py),
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            HOST,
            "--port",
            str(PORT),
        ]

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    print(f"\nStarting Fantasy Lineup Optimizer at {URL}")
    print("Press Ctrl+C to stop the server.\n")

    opener = threading.Thread(target=open_browser_when_ready, daemon=True)
    opener.start()

    process = subprocess.Popen(cmd, cwd=ROOT, env=env)

    def _stop_server() -> None:
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    atexit.register(_stop_server)

    def _signal_handler(signum: int, frame: object) -> None:
        _stop_server()
        raise SystemExit(0)

    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _signal_handler)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, _signal_handler)

    try:
        return process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        _stop_server()
        return 0


def main() -> None:
    os.chdir(ROOT)
    print("Fantasy Lineup Optimizer — one-click launch")
    print(f"Project: {ROOT}\n")
    ensure_python()
    ensure_venv()
    ensure_python_deps()
    ensure_frontend_build()
    code = start_server()
    if code != 0:
        pause_on_error()
    sys.exit(code)


if __name__ == "__main__":
    main()
