"""Authentication and authorisation at the HTTP layer."""

import sqlite3

import bcrypt
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "SQLITE_PATH", tmp_path / "roles.db")
    monkeypatch.setattr(config, "DUCKDB_PATH", tmp_path / "d.duckdb")
    monkeypatch.setattr(config, "CHROMA_PATH", tmp_path / "chroma")
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")

    import app.main as main

    main.init_db()
    conn = sqlite3.connect(config.SQLITE_PATH)
    for role in ("Admin", "HR", "Finance"):
        conn.execute("INSERT OR IGNORE INTO roles (role_name) VALUES (?)", (role,))
    for user, pw, role in [("admin", "adminpw", "Admin"), ("hruser", "hrpw", "HR")]:
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (user, bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode(), role),
        )
    conn.commit()
    conn.close()
    return TestClient(main.app)


ADMIN = ("admin", "adminpw")
HR = ("hruser", "hrpw")


# --- authentication --------------------------------------------------------
def test_health_needs_no_credentials(client):
    assert client.get("/health").status_code == 200


def test_login_rejects_a_wrong_password(client):
    assert client.get("/login", auth=("admin", "wrong")).status_code == 401


def test_login_rejects_an_unknown_user(client):
    assert client.get("/login", auth=("nobody", "x")).status_code == 401


def test_login_returns_the_role(client):
    assert client.get("/login", auth=HR).json()["role"] == "HR"


def test_protected_routes_reject_anonymous_callers(client):
    for method, path in [("get", "/roles"), ("post", "/chat")]:
        assert getattr(client, method)(path).status_code == 401


# --- authorisation ---------------------------------------------------------
def test_upload_requires_authentication(client):
    """This endpoint previously had no auth dependency at all."""
    r = client.post("/upload-docs", files={"file": ("x.md", b"hi")}, data={"role": "HR"})
    assert r.status_code == 401


def test_upload_requires_admin(client):
    r = client.post(
        "/upload-docs", files={"file": ("x.md", b"hi")}, data={"role": "HR"}, auth=HR
    )
    assert r.status_code == 403


def test_non_admin_cannot_create_users(client):
    r = client.post(
        "/create-user",
        data={"username": "x", "password": "y", "role": "HR"},
        auth=HR,
    )
    assert r.status_code == 403


def test_non_admin_cannot_create_roles(client):
    assert client.post("/create-role", data={"role_name": "X"}, auth=HR).status_code == 403


def test_admin_can_create_a_user(client):
    r = client.post(
        "/create-user",
        data={"username": "newbie", "password": "pw", "role": "Finance"},
        auth=ADMIN,
    )
    assert r.status_code == 200


def test_creating_a_user_with_an_unknown_role_is_rejected(client):
    r = client.post(
        "/create-user",
        data={"username": "x", "password": "y", "role": "Nope"},
        auth=ADMIN,
    )
    assert r.status_code == 400


# --- input handling --------------------------------------------------------
def test_upload_rejects_unsupported_file_types(client):
    r = client.post(
        "/upload-docs", files={"file": ("x.exe", b"MZ")}, data={"role": "HR"}, auth=ADMIN
    )
    assert r.status_code == 400


def test_upload_rejects_an_unknown_role(client):
    r = client.post(
        "/upload-docs", files={"file": ("x.md", b"hi")}, data={"role": "Ghost"}, auth=ADMIN
    )
    assert r.status_code == 400


def test_upload_strips_directory_traversal_from_filenames(client):
    from app import config

    client.post(
        "/upload-docs",
        files={"file": ("../../escaped.md", b"hi")},
        data={"role": "HR"},
        auth=ADMIN,
    )
    # The file must land inside the role directory, not above it.
    assert not (config.UPLOAD_DIR.parent / "escaped.md").exists()
    assert (config.UPLOAD_DIR / "HR" / "escaped.md").exists()


def test_table_name_whitelist_rejects_odd_filenames(client):
    from fastapi import HTTPException

    from app.main import safe_table_name

    assert safe_table_name("hr-data.csv") == "hr_data"
    assert safe_table_name("my data.csv") == "my_data"

    # Path traversal is neutralised rather than rejected: taking the stem
    # discards the directory part, so "../x.csv" becomes the table "x".
    assert safe_table_name("../../x.csv") == "x"

    # Anything that would not be a valid SQL identifier is refused outright,
    # because the table name cannot be parameterised.
    # Hyphens are legal once mapped to underscores, so "drop--table.csv"
    # becomes the harmless identifier "drop__table" rather than being refused.
    assert safe_table_name("drop--table.csv") == "drop__table"

    for bad in ("1bad.csv", "we;ird.csv", ".csv", "table name!.csv"):
        with pytest.raises(HTTPException):
            safe_table_name(bad)


# --- the role used for filtering comes from auth, not the request ----------
def test_chat_ignores_a_role_supplied_in_the_body(client, monkeypatch):
    """A caller must not be able to widen their own access by asking."""
    seen = {}

    async def fake_rag(question, role, cohere_api_key=None):
        seen["role"] = role
        return {"answer": "ok"}

    import app.main as main

    monkeypatch.setattr(main, "detect_query_type_llm", lambda q: "RAG")
    monkeypatch.setattr(main, "ask_rag", fake_rag)

    r = client.post("/chat", json={"question": "hi", "role": "Admin"}, auth=HR)
    assert r.status_code == 200
    assert seen["role"] == "HR"
