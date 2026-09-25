"""
Local SQLite storage for PassForge.

PassForge is a single-user desktop vault: one owner account per database
file. The owner's email is where unauthorized-access alerts are sent.
Vault entries store the password ciphertext only — decryption happens in
memory using the session's derived key (see core/crypto_utils.py).
"""

import datetime
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path.home() / ".passforge" / "vault.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS owner (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    email TEXT NOT NULL,
    salt BLOB NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS vault_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reason TEXT NOT NULL,
    ciphertext TEXT NOT NULL,
    strength_label TEXT NOT NULL,
    strength_score INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    success INTEGER NOT NULL,
    attempted_at TEXT NOT NULL
);
"""


@dataclass
class Owner:
    email: str
    salt: bytes
    password_hash: str
    created_at: str
    failed_attempts: int = 0


@dataclass
class VaultEntry:
    id: int
    reason: str
    ciphertext: str
    strength_label: str
    strength_score: int
    created_at: str


class Database:
    def __init__(self, path: Path = DEFAULT_DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False because the local bridge server (used by
        # the browser extension) handles each request on its own thread.
        # The lock below serializes all access, since a single sqlite3
        # connection still isn't safe for concurrent use across threads.
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()
            self._migrate()

    def _migrate(self):
        """Best-effort additive migration for databases created by an
        earlier version of PassForge (before failed_attempts existed)."""
        cols = [r["name"] for r in self._conn.execute("PRAGMA table_info(owner)")]
        if "failed_attempts" not in cols:
            self._conn.execute(
                "ALTER TABLE owner ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0"
            )
            self._conn.commit()

    def close(self):
        with self._lock:
            self._conn.close()

    # ------------------------------------------------------------- owner --
    def has_owner(self) -> bool:
        with self._lock:
            row = self._conn.execute("SELECT 1 FROM owner WHERE id = 1").fetchone()
            return row is not None

    def create_owner(self, email: str, salt: bytes, password_hash: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO owner (id, email, salt, password_hash, created_at) "
                "VALUES (1, ?, ?, ?, ?)",
                (email, salt, password_hash, datetime.datetime.now().isoformat()),
            )
            self._conn.commit()

    def get_owner(self) -> Optional[Owner]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM owner WHERE id = 1").fetchone()
            if row is None:
                return None
            return Owner(row["email"], row["salt"], row["password_hash"], row["created_at"],
                         row["failed_attempts"])

    def update_owner_credentials(self, salt: bytes, password_hash: str) -> None:
        """Used when changing the master password."""
        with self._lock:
            self._conn.execute(
                "UPDATE owner SET salt = ?, password_hash = ? WHERE id = 1",
                (salt, password_hash),
            )
            self._conn.commit()

    def increment_failed_attempts(self) -> int:
        with self._lock:
            self._conn.execute(
                "UPDATE owner SET failed_attempts = failed_attempts + 1 WHERE id = 1"
            )
            self._conn.commit()
            row = self._conn.execute("SELECT failed_attempts FROM owner WHERE id = 1").fetchone()
            return row["failed_attempts"]

    def reset_failed_attempts(self) -> None:
        with self._lock:
            self._conn.execute("UPDATE owner SET failed_attempts = 0 WHERE id = 1")
            self._conn.commit()

    # -------------------------------------------------------- login log --
    def log_login_attempt(self, success: bool) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO login_attempts (success, attempted_at) VALUES (?, ?)",
                (int(success), datetime.datetime.now().isoformat()),
            )
            self._conn.commit()

    # ----------------------------------------------------------- vault --
    def add_entry(self, reason: str, ciphertext: str, strength_label: str,
                  strength_score: int) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO vault_entries (reason, ciphertext, strength_label, "
                "strength_score, created_at) VALUES (?, ?, ?, ?, ?)",
                (reason, ciphertext, strength_label, strength_score,
                 datetime.datetime.now().isoformat()),
            )
            self._conn.commit()
            return cur.lastrowid

    def list_entries(self, search: str = "") -> list[VaultEntry]:
        with self._lock:
            if search:
                # Escape LIKE's own wildcard characters so a reason like
                # "50% off" or "user_name" is matched literally instead of
                # being interpreted as a pattern.
                escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                rows = self._conn.execute(
                    "SELECT * FROM vault_entries WHERE reason LIKE ? ESCAPE '\\' "
                    "ORDER BY created_at DESC",
                    (f"%{escaped}%",),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM vault_entries ORDER BY created_at DESC"
                ).fetchall()
            return [
                VaultEntry(r["id"], r["reason"], r["ciphertext"],
                           r["strength_label"], r["strength_score"], r["created_at"])
                for r in rows
            ]

    def delete_entry(self, entry_id: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM vault_entries WHERE id = ?", (entry_id,))
            self._conn.commit()

    def update_entry(self, entry_id: int, reason: str, ciphertext: str,
                      strength_label: str, strength_score: int) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE vault_entries SET reason = ?, ciphertext = ?, strength_label = ?, "
                "strength_score = ? WHERE id = ?",
                (reason, ciphertext, strength_label, strength_score, entry_id),
            )
            self._conn.commit()

    def update_entry_ciphertext(self, entry_id: int, ciphertext: str) -> None:
        """Used when re-encrypting every entry after a master password change."""
        with self._lock:
            self._conn.execute(
                "UPDATE vault_entries SET ciphertext = ? WHERE id = ?",
                (ciphertext, entry_id),
            )
            self._conn.commit()
