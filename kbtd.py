#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["certifi"]
# ///
"""kanban-todo launcher.

Fetches index.html from KBTD_URL, serves it same-origin alongside a small
token-guarded /file API over the given todo.txt, and opens a browser
pointed at the local server. Blocks in the foreground until the browser
window closes (--app mode) or the server idles out (--browser mode) or
the user hits Ctrl-C.
"""

import argparse
import hashlib
import os
import platform
import secrets
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import certifi

IDLE_TIMEOUT_SECONDS = 10 * 60


def error_exit(message):
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


# --- Argument parsing ---

def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="kbtd.py",
        description="Launch a Kanban board for a todo.txt file.",
        add_help=False,
    )
    parser.add_argument("--browser", action="store_true",
                         help="Open in existing browser instead of app mode")
    parser.add_argument("--help", action="store_true", help="Show help message")
    parser.add_argument("file", nargs="?", help="Path to a todo.txt file")

    args = parser.parse_args(argv)

    if args.help:
        parser.print_help()
        sys.exit(0)

    if not args.file:
        parser.print_usage()
        error_exit("No file specified")

    return args


# --- Path resolution ---

def resolve_file_path(file_path):
    path = Path(file_path).expanduser()

    if not path.is_file():
        if not path.parent.is_dir():
            error_exit(f"Directory does not exist: {path.parent}")
        path.touch()

    abs_path = path.resolve()

    if not abs_path.is_file():
        error_exit(f"File not found: {abs_path}")

    return abs_path


# --- Browser detection ---

CHROMIUM_NAMES = ["google-chrome", "chromium", "chromium-browser", "microsoft-edge"]
FIREFOX_NAMES = ["firefox"]

MACOS_APP_PATHS = {
    "chromium": [
        ("/Applications/Google Chrome.app", "Contents/MacOS/Google Chrome"),
        ("/Applications/Chromium.app", "Contents/MacOS/Chromium"),
        ("/Applications/Microsoft Edge.app", "Contents/MacOS/Microsoft Edge"),
    ],
    "firefox": [
        ("/Applications/Firefox.app", "Contents/MacOS/firefox"),
    ],
}

WSL_CHROME_PATH = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"


def find_browser():
    """Returns (family, binary_path_or_name). family is 'chromium', 'firefox' or 'safari'."""

    env_browser = os.environ.get("BROWSER", "")
    if env_browser:
        lowered = env_browser.lower()
        if any(name in lowered for name in ("chrome", "chromium", "edge")):
            return "chromium", env_browser
        if "firefox" in lowered:
            return "firefox", env_browser
        if "safari" in lowered:
            return "safari", env_browser

    for name in CHROMIUM_NAMES:
        if shutil.which(name):
            return "chromium", name
    for name in FIREFOX_NAMES:
        if shutil.which(name):
            return "firefox", name

    if platform.system() == "Darwin":
        for family, candidates in MACOS_APP_PATHS.items():
            for app_dir, binary_rel in candidates:
                if os.path.isdir(app_dir):
                    return family, f"{app_dir}/{binary_rel}"
        if os.path.isdir("/Applications/Safari.app"):
            return "safari", "Safari"

    if os.environ.get("WSL_DISTRO_NAME") and os.path.isfile(WSL_CHROME_PATH):
        return "chromium", WSL_CHROME_PATH

    return None, None


def launch_browser(family, binary, target_url, app_mode):
    user_data_dir = None
    if family == "chromium":
        if app_mode:
            user_data_dir = Path(".kbtd-chrome-data")
            user_data_dir.mkdir(exist_ok=True)
            cmd = [binary, f"--user-data-dir={user_data_dir}", f"--app={target_url}"]
        else:
            cmd = [binary, "--new-window", target_url]
    elif family == "firefox":
        cmd = [binary, "--new-window", target_url]
    elif family == "safari":
        cmd = ["open", "-a", "Safari", target_url]
    else:
        error_exit(f"Unsupported browser family: {family}")

    return subprocess.Popen(cmd)


# --- index.html fetch ---

def load_index_html(base_url):
    local_copy = Path(__file__).resolve().parent / "index.html"
    if local_copy.is_file():
        print(f"Using local {local_copy}")
        return local_copy.read_bytes()
    return fetch_index_html(base_url)


def fetch_index_html(base_url):
    if base_url.endswith(".html") or base_url.endswith(".htm"):
        url = base_url
    else:
        url = base_url.rstrip("/") + "/index.html"
    # uv-managed Python builds don't always see the OS trust store (notably on
    # Nix), so use certifi's bundle explicitly rather than relying on the
    # platform default.
    ctx = ssl.create_default_context(cafile=certifi.where())
    try:
        with urllib.request.urlopen(url, timeout=10, context=ctx) as resp:
            return resp.read()
    except (urllib.error.URLError, OSError) as err:
        error_exit(f"Could not fetch index.html from {url}: {err}")


# --- HTTP server ---

def make_handler(file_path, html_bytes, token):
    def current_etag():
        try:
            data = file_path.read_bytes()
        except FileNotFoundError:
            return None, None
        digest = hashlib.sha256(data).hexdigest()[:16]
        return data, f'"{digest}"'

    class Handler(BaseHTTPRequestHandler):
        server_version = "kbtd/1.0"

        def log_message(self, fmt, *args):
            pass

        def _check_token(self):
            if self.headers.get("X-Kbtd-Token") != token:
                self.send_response(403)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return False
            return True

        def _send_file_headers(self, etag, length, extra=None):
            self.send_header("ETag", etag)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            if extra:
                for key, value in extra.items():
                    self.send_header(key, value)

        def do_GET(self):
            self.server.touch()
            if self.path == "/" or self.path.startswith("/?"):
                body = html_bytes
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if self.path == "/file":
                if not self._check_token():
                    return
                data, etag = current_etag()
                if data is None:
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self.send_response(200)
                self._send_file_headers(etag, len(data))
                self.end_headers()
                self.wfile.write(data)
                return

            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_HEAD(self):
            self.server.touch()
            if self.path != "/file":
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if not self._check_token():
                return
            data, etag = current_etag()
            if data is None:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(200)
            self._send_file_headers(etag, len(data))
            self.end_headers()

        def do_PUT(self):
            self.server.touch()
            if self.path != "/file":
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if not self._check_token():
                return

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)

            if_match = self.headers.get("If-Match", "")
            _, existing_etag = current_etag()

            if if_match and if_match != (existing_etag or ""):
                self.send_response(412)
                if existing_etag:
                    self.send_header("ETag", existing_etag)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            fd, tmp_path = tempfile.mkstemp(
                dir=str(file_path.parent), prefix=f".{file_path.name}.", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "wb") as tmp_file:
                    tmp_file.write(body)
                os.replace(tmp_path, file_path)
            except Exception:
                os.unlink(tmp_path)
                raise

            new_etag = f'"{hashlib.sha256(body).hexdigest()[:16]}"'
            self.send_response(200)
            self.send_header("ETag", new_etag)
            self.send_header("Content-Length", "0")
            self.end_headers()

    return Handler


class KbtdServer(HTTPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_activity = time.monotonic()
        self._lock = threading.Lock()

    def touch(self):
        with self._lock:
            self.last_activity = time.monotonic()

    def idle_seconds(self):
        with self._lock:
            return time.monotonic() - self.last_activity


def run_idle_watchdog(server, timeout_seconds):
    while True:
        time.sleep(5)
        if server.idle_seconds() > timeout_seconds:
            server.shutdown()
            return


# --- Main ---

def main(argv=None):
    sys.stdout.reconfigure(line_buffering=True)
    args = parse_args(sys.argv[1:] if argv is None else argv)

    abs_path = resolve_file_path(args.file)

    base_url = os.environ.get("KBTD_URL", "https://mccormick.cx/apps/kanban-todo")
    html_bytes = load_index_html(base_url)

    token = secrets.token_urlsafe(24)
    handler_cls = make_handler(abs_path, html_bytes, token)
    server = KbtdServer(("127.0.0.1", 0), handler_cls)
    port = server.server_address[1]

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    watchdog_thread = threading.Thread(
        target=run_idle_watchdog, args=(server, IDLE_TIMEOUT_SECONDS), daemon=True
    )
    watchdog_thread.start()

    encoded_path = urllib.parse.quote(str(abs_path))
    target_url = f"http://127.0.0.1:{port}/?file={encoded_path}&token={token}"

    print(f"Serving {abs_path}")
    print(f"URL: {target_url}")

    family, binary = find_browser()
    app_mode = not args.browser
    browser_process = None
    if family:
        browser_process = launch_browser(family, binary, target_url, app_mode)
    else:
        print("No browser auto-detected. Open the URL above manually in any browser.")

    def shutdown():
        server.shutdown()
        server_thread.join(timeout=5)

    try:
        if app_mode and browser_process:
            browser_process.wait()
            shutdown()
        else:
            print(f"Server running on 127.0.0.1:{port}; shuts down after "
                  f"{IDLE_TIMEOUT_SECONDS // 60} min idle.")
            server_thread.join()
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
