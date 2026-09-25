"""
A tiny local HTTP server so the PassForge browser extension can hand off a
password for saving, without the browser ever touching the vault database
or the encryption key directly.

Trust model (read this before relying on it for anything sensitive):
- The server only ever binds to 127.0.0.1 — it is not reachable from the
  network, only from processes on the same machine.
- A random pairing token is generated on first run and stored at
  ~/.passforge/ext_token.txt. You paste this once into the extension's
  options page. Requests without the correct token are rejected.
- This is an appropriate trust model for a personal, single-user tool on
  your own machine. It is *not* the same level of isolation as browsers'
  native-messaging APIs, which is what production password managers use.
  Treat this integration as a convenience layer, not a hardened boundary.
- The server only accepts new entries while the vault is unlocked. If it's
  locked, the extension is told so and shows nothing sensitive.
"""

import json
import secrets as _secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

DEFAULT_PORT = 47832
TOKEN_PATH = Path.home() / ".passforge" / "ext_token.txt"


def get_or_create_token() -> str:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    if TOKEN_PATH.exists():
        token = TOKEN_PATH.read_text().strip()
        if token:
            return token
    token = _secrets.token_hex(24)
    TOKEN_PATH.write_text(token)
    return token


class BridgeServer:
    """Owns the background HTTP thread. Call start() after login, stop() on
    lock/quit. `controller` gives the handler access to the live session."""

    def __init__(self, controller, port: int = DEFAULT_PORT):
        self.controller = controller
        self.port = port
        self.token = get_or_create_token()
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.start_error: Optional[str] = None

    def start(self):
        if self._httpd is not None:
            return
        handler_cls = _make_handler(self.controller, self.token)
        try:
            self._httpd = ThreadingHTTPServer(("127.0.0.1", self.port), handler_cls)
        except OSError as exc:
            # Most likely another PassForge instance already owns this port.
            # The browser-extension integration just won't be available this
            # session — that must never take down login/unlock.
            self._httpd = None
            self.start_error = str(exc)
            return
        self.start_error = None
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
            self._thread = None


def _make_handler(controller, expected_token):
    from core import crypto_utils as cu
    from core.password_tools import analyze_strength

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # keep the app's console quiet

        def _send_json(self, status: int, payload: dict):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self):
            if self.path == "/status":
                self._send_json(200, {
                    "app": "PassForge",
                    "unlocked": controller.session is not None,
                })
            else:
                self._send_json(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/save":
                self._send_json(404, {"error": "not found"})
                return

            length = int(self.headers.get("Content-Length", 0))
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                self._send_json(400, {"error": "bad request"})
                return

            if not _secrets.compare_digest(str(data.get("token", "")), expected_token):
                self._send_json(401, {"error": "invalid pairing token"})
                return

            if controller.session is None:
                self._send_json(423, {"error": "PassForge is locked — open and unlock it first"})
                return

            reason = str(data.get("reason", "")).strip()
            password = str(data.get("password", ""))
            if not reason or not password:
                self._send_json(400, {"error": "reason and password are required"})
                return

            result = analyze_strength(password)
            ciphertext = cu.encrypt_value(controller.session.vault_key, password)
            entry_id = controller.db.add_entry(reason, ciphertext, result.label, result.score)

            # Ask the UI thread to refresh the vault list if it's on screen.
            controller.notify_entry_added()

            self._send_json(200, {"ok": True, "id": entry_id})

    return Handler
