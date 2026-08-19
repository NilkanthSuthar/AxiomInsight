"""Bootstrap a usable database from the sample documents in static/uploads/.

A fresh clone has no roles, no users and an empty index: the sample documents
sit on disk but nothing registers them. This script wires them up.

    python -m scripts.seed

Safe to re-run. Embedding requires OPENAI_API_KEY; without it everything else
is still set up and the embedding step is skipped with a message.
"""

import os
import sqlite3
import sys
from pathlib import Path

import bcrypt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.main import init_db, safe_table_name  # noqa: E402
from app.rag_utils.csv_query import get_duck_conn  # noqa: E402

ROLES = ["Admin", "Finance", "HR", "Marketing", "Engineering", "Compliance", "General"]

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


def seed_roles(conn):
    for role in ROLES:
        conn.execute("INSERT OR IGNORE INTO roles (role_name) VALUES (?)", (role,))
    conn.commit()
    print(f"Roles ready: {', '.join(ROLES)}")


def seed_admin(conn):
    existing = conn.execute(
        "SELECT 1 FROM users WHERE username = ?", (ADMIN_USERNAME,)
    ).fetchone()
    if existing:
        print(f"User '{ADMIN_USERNAME}' already exists, leaving it alone.")
        return

    hashed = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
    conn.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        (ADMIN_USERNAME, hashed, "Admin"),
    )
    conn.commit()
    print(f"Created user '{ADMIN_USERNAME}' with role Admin.")
    if ADMIN_PASSWORD == "admin123":
        print("  (default demo password — set ADMIN_PASSWORD to override)")


def register_documents(conn):
    """Register every sample file under static/uploads/<Role>/."""
    registered = 0
    for role_dir in sorted(config.UPLOAD_DIR.iterdir()):
        if not role_dir.is_dir():
            continue
        role = role_dir.name

        for path in sorted(role_dir.iterdir()):
            if path.suffix.lower() not in (".csv", ".md"):
                continue

            already = conn.execute(
                "SELECT 1 FROM documents WHERE filepath = ?", (str(path),)
            ).fetchone()
            if already:
                continue

            headers_str = None
            if path.suffix.lower() == ".csv":
                frame = pd.read_csv(path)
                headers_str = ",".join(frame.columns.tolist())

                table_name = safe_table_name(path.name)
                duck = get_duck_conn()
                duck.register("incoming_csv", frame)
                duck.execute(
                    f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM incoming_csv'
                )
                duck.unregister("incoming_csv")
                duck.execute(
                    "DELETE FROM tables_metadata WHERE table_name = ?", (table_name,)
                )
                duck.execute(
                    "INSERT INTO tables_metadata (table_name, role) VALUES (?, ?)",
                    (table_name, role),
                )
                print(f"  DuckDB table '{table_name}' <- {path.name} (role: {role})")

            conn.execute(
                "INSERT INTO documents (filename, role, filepath, headers_str, embedded) "
                "VALUES (?, ?, ?, ?, 0)",
                (path.name, role, str(path), headers_str),
            )
            registered += 1

    conn.commit()
    print(f"Registered {registered} new document(s).")
    return registered


def main():
    config.ensure_directories()
    init_db()

    conn = sqlite3.connect(config.SQLITE_PATH)
    try:
        seed_roles(conn)
        seed_admin(conn)
        register_documents(conn)
    finally:
        conn.close()

    if not config.OPENAI_API_KEY:
        print(
            "\nOPENAI_API_KEY is not set, so documents were registered but not embedded.\n"
            "Add your key to .env and re-run this script to build the vector index.\n"
            "The SQL path over DuckDB works without it."
        )
        return

    print("\nEmbedding documents into the vector store...")
    from app.rag_utils.rag_module import run_indexer

    run_indexer()
    print("\nSeeding complete.")


if __name__ == "__main__":
    main()
