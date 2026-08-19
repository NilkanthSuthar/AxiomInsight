import re
import sqlite3
from io import BytesIO
from pathlib import Path

import bcrypt
import pandas as pd
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from . import config
from .rag_utils.csv_query import get_duck_conn
from .rag_utils.query_classifier import detect_query_type_llm
from .rag_utils.rag_chain import ask_rag
from .rag_utils.rag_module import run_indexer

app = FastAPI(title="AxiomInsight")
security = HTTPBasic()

config.ensure_directories()


@app.exception_handler(config.MissingCredentialError)
async def missing_credential_handler(request: Request, exc: config.MissingCredentialError):
    """Answer with an actionable message instead of a 500 stack trace."""
    return JSONResponse(status_code=503, content={"detail": str(exc)})


# -------------------------
# === SQLITE DATABASE SETUP ===
# -------------------------
def get_db():
    """One SQLite connection per call.

    A single module-level connection with check_same_thread=False was
    previously shared across all request threads.
    """
    conn = sqlite3.connect(config.SQLITE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        );

        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_name TEXT UNIQUE
        );

        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            role TEXT,
            filepath TEXT NOT NULL,
            headers_str TEXT,
            embedded INTEGER DEFAULT 0
        );
        """
    )
    conn.commit()
    conn.close()


init_db()


# -------------------------
# === AUTHENTICATION ===
# -------------------------
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    conn = get_db()
    row = conn.execute(
        "SELECT password, role FROM users WHERE username = ?", (credentials.username,)
    ).fetchone()
    conn.close()

    if not row or not bcrypt.checkpw(
        credentials.password.encode("utf-8"), row[0].encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"username": credentials.username, "role": row[1]}


def require_admin(user=Depends(authenticate)):
    if user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin role required.")
    return user


# === MODELS ===
class ChatRequest(BaseModel):
    question: str


# -------------------------
# === ROUTES ===
# -------------------------
@app.get("/health")
def health():
    """Readiness, including whether the app is actually usable."""
    return {
        "status": "ok",
        "openai_key_configured": bool(config.OPENAI_API_KEY),
        "cohere_reranking_enabled": bool(config.COHERE_API_KEY),
        "vector_store": config.VECTOR_STORE,
        "langsmith_tracing": config.tracing_status(),
    }


@app.get("/login")
def login(user=Depends(authenticate)):
    return {"message": f"Welcome {user['username']}!", "role": user["role"]}


@app.get("/roles")
def get_roles(user=Depends(authenticate)):
    conn = get_db()
    roles = [r[0] for r in conn.execute("SELECT role_name FROM roles").fetchall()]
    conn.close()
    return {"roles": roles}


@app.post("/create-user")
def create_user(
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    user=Depends(require_admin),
):
    conn = get_db()
    if not conn.execute("SELECT 1 FROM roles WHERE role_name = ?", (role,)).fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid role")

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    try:
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, hashed, role),
        )
        conn.commit()
        return {"message": f"User '{username}' added with role '{role}'"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="User already exists")
    finally:
        conn.close()


@app.post("/create-role")
def create_role(role_name: str = Form(...), user=Depends(require_admin)):
    conn = get_db()
    try:
        conn.execute("INSERT INTO roles (role_name) VALUES (?)", (role_name,))
        conn.commit()
        return {"message": f"Role '{role_name}' created"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Role already exists")
    finally:
        conn.close()


def safe_table_name(filename: str) -> str:
    """Derive a SQL identifier from a filename, rejecting anything unexpected.

    The table name reaches DuckDB as an identifier and cannot be parameterised,
    so it is whitelisted rather than interpolated as-is.
    """
    stem = Path(filename).stem.replace("-", "_").replace(" ", "_")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", stem):
        raise HTTPException(
            status_code=400,
            detail="Filename must start with a letter and contain only letters, "
            "digits, underscores or hyphens.",
        )
    return stem


@app.post("/upload-docs")
async def upload_docs(
    file: UploadFile = File(...),
    role: str = Form(...),
    user=Depends(require_admin),
):
    """Store a document, register it, and index it.

    This endpoint previously had no authentication dependency at all, so any
    caller could upload a document and assign it to any role.
    """
    filename = Path(file.filename).name
    extension = Path(filename).suffix.lower()
    if extension not in (".csv", ".md"):
        raise HTTPException(status_code=400, detail="Only .csv and .md files are supported.")

    conn = get_db()
    if not conn.execute("SELECT 1 FROM roles WHERE role_name = ?", (role,)).fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail=f"Unknown role: {role}")
    conn.close()

    try:
        role_dir = config.UPLOAD_DIR / role
        role_dir.mkdir(parents=True, exist_ok=True)
        filepath = role_dir / filename

        data = await file.read()
        filepath.write_bytes(data)

        headers_str = None
        if extension == ".csv":
            frame = pd.read_csv(BytesIO(data))
            headers_str = ",".join(frame.columns.tolist())
            table_name = safe_table_name(filename)

            duck = get_duck_conn()
            duck.register("incoming_csv", frame)
            duck.execute(f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM incoming_csv')
            duck.unregister("incoming_csv")
            duck.execute("DELETE FROM tables_metadata WHERE table_name = ?", (table_name,))
            duck.execute(
                "INSERT INTO tables_metadata (table_name, role) VALUES (?, ?)",
                (table_name, role),
            )

        conn = get_db()
        conn.execute(
            "INSERT INTO documents (filename, role, filepath, headers_str, embedded) "
            "VALUES (?, ?, ?, ?, 0)",
            (filename, role, str(filepath), headers_str),
        )
        conn.commit()
        conn.close()

        # The file is stored and registered regardless; only the embedding step
        # needs an API key, so a missing key degrades rather than losing the upload.
        try:
            run_indexer()
            indexed = True
            note = ""
        except config.MissingCredentialError as exc:
            indexed = False
            note = f" Not indexed yet: {exc.args[0].splitlines()[0]}"

        return JSONResponse(
            content={
                "message": f"{filename} uploaded successfully for role '{role}'.{note}",
                "indexed": indexed,
            }
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}")


@app.post("/chat")
async def chat(req: ChatRequest, user=Depends(authenticate)):
    """Route the question to SQL or document retrieval, then answer it.

    The role is taken from the authenticated user, never from the request body.
    """
    role = user["role"]
    mode = detect_query_type_llm(req.question)
    fallback_used = False

    if mode == "SQL":
        from .rag_utils.csv_query import ask_csv

        result = await ask_csv(req.question, role, user["username"], return_sql=True)
        if result.get("error") or not result.get("answer", "").strip():
            # SQL could not answer it; documents are the better bet.
            result = await ask_rag(req.question, role)
            fallback_used = True
            mode = "SQL -> fallback to RAG"
    else:
        result = await ask_rag(req.question, role)

    return {
        "user": user["username"],
        "role": role,
        "mode": mode,
        "fallback": fallback_used,
        "answer": result["answer"],
        **({"sql": result["sql"]} if "sql" in result else {}),
    }
