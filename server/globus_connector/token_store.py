import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet


@dataclass
class StoredTokenRecord:
    clearml_user_id: str
    email: str
    encrypted_tokens: str
    updated_at: str


class TokenStore:
    def __init__(self, db_path: str, fernet_key: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.fernet = Fernet(fernet_key.encode("utf-8"))
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_globus_tokens (
                    clearml_user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    encrypted_tokens TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def put_token_bundle(self, clearml_user_id: str, email: str, token_bundle: Dict[str, Any]) -> None:
        plaintext = json.dumps(token_bundle).encode("utf-8")
        encrypted = self.fernet.encrypt(plaintext).decode("utf-8")
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_globus_tokens(clearml_user_id, email, encrypted_tokens, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(clearml_user_id) DO UPDATE SET
                    email=excluded.email,
                    encrypted_tokens=excluded.encrypted_tokens,
                    updated_at=excluded.updated_at
                """,
                (clearml_user_id, email, encrypted, now),
            )
            conn.commit()

    def get_token_bundle(self, clearml_user_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT clearml_user_id, email, encrypted_tokens, updated_at FROM user_globus_tokens WHERE clearml_user_id=?",
                (clearml_user_id,),
            ).fetchone()

        if not row:
            return None

        decrypted = self.fernet.decrypt(row["encrypted_tokens"].encode("utf-8"))
        return json.loads(decrypted.decode("utf-8"))

    def get_record(self, clearml_user_id: str) -> Optional[StoredTokenRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT clearml_user_id, email, encrypted_tokens, updated_at FROM user_globus_tokens WHERE clearml_user_id=?",
                (clearml_user_id,),
            ).fetchone()

        if not row:
            return None

        return StoredTokenRecord(
            clearml_user_id=row["clearml_user_id"],
            email=row["email"],
            encrypted_tokens=row["encrypted_tokens"],
            updated_at=row["updated_at"],
        )
