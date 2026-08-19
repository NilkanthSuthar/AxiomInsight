"""Natural-language questions answered as SQL over DuckDB tables."""

import re
import sqlite3

import duckdb
import tabulate
from openai import OpenAI

from .. import config

_duck_conn = None
_client = None


def get_duck_conn():
    """Open the DuckDB file on first use.

    Previously this ran at import time against a relative path whose parent
    directory did not exist yet, so importing the module raised an IOException
    on a fresh clone.
    """
    global _duck_conn
    if _duck_conn is None:
        config.ensure_directories()
        _duck_conn = duckdb.connect(str(config.DUCKDB_PATH))
        _duck_conn.execute(
            "CREATE TABLE IF NOT EXISTS tables_metadata (table_name TEXT, role TEXT)"
        )
    return _duck_conn


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.require_openai_key())
    return _client


def get_allowed_tables_for_role(role: str) -> list[str]:
    """Tables this role may query: its own, plus anything marked general."""
    conn = get_duck_conn()
    role = role.lower()
    if role == "admin":
        rows = conn.execute("SELECT table_name FROM tables_metadata").fetchall()
    elif role == "general":
        rows = conn.execute(
            "SELECT table_name FROM tables_metadata WHERE lower(role) = 'general'"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT table_name FROM tables_metadata "
            "WHERE lower(role) = ? OR lower(role) = 'general'",
            [role],
        ).fetchall()
    return [r[0] for r in rows]


def extract_tables_from_sql(sql: str) -> list[str]:
    matches = re.findall(r"FROM\s+(\w+)|JOIN\s+(\w+)", sql, flags=re.IGNORECASE)
    return [item for tup in matches for item in tup if item]


FORBIDDEN = ["insert", "update", "delete", "drop", "alter", "create", "attach", "copy"]


def is_safe_query(sql: str) -> bool:
    lowered = sql.strip().lower().rstrip(";")
    return lowered.startswith("select") and all(w not in lowered for w in FORBIDDEN)


def build_schema_block(allowed_tables: list[str]) -> str:
    """Describe only the tables this role may read.

    The schema is scoped before it reaches the model. Previously every user's
    prompt was built from all indexed documents regardless of role, which put
    other departments' table and column names in front of the model and left
    access control to a check applied after the SQL had been written.
    """
    if not allowed_tables:
        return ""

    conn = sqlite3.connect(config.SQLITE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT filename, headers_str FROM documents "
        "WHERE embedded = 1 AND headers_str IS NOT NULL"
    )
    rows = cursor.fetchall()
    conn.close()

    schemas = []
    for filename, headers_str in rows:
        table_name = filename.rsplit(".", 1)[0].replace("-", "_")
        if table_name not in allowed_tables:
            continue
        schemas.append(f"Table: {table_name}\nColumns: {headers_str}")

    return "\n\n".join(schemas)


def translate_nl_to_sql(question: str, allowed_tables: list[str]) -> str:
    schema_block = build_schema_block(allowed_tables)
    if not schema_block:
        return ""

    prompt = f"""\
You are an assistant that converts natural language questions into safe SQL SELECT queries.

Use only the following schemas:
{schema_block}

Constraints:
- Use only the tables listed above.
- Use the exact column names as-is (including hyphens, underscores, casing).
- Return only a SELECT query (no INSERT/UPDATE/DELETE).
- If asked about 'employee name', consider alternatives like 'full-name', 'last-name'.
- If asked about 'position', consider synonyms like 'role', 'designation'.
- Do not mix aggregate functions (like COUNT(*)) with *.
- Return the SQL only, with no explanation and no markdown fences.

Natural Language Question: "{question}"

SQL:"""

    response = _get_client().chat.completions.create(
        model=config.CLASSIFIER_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    sql = response.choices[0].message.content.strip()
    # Models often wrap SQL in a fenced block despite being asked not to.
    if sql.startswith("```"):
        sql = re.sub(r"^```(?:sql)?\s*|\s*```$", "", sql, flags=re.IGNORECASE).strip()
    return sql


async def ask_csv(question: str, role: str, username: str, return_sql: bool = False) -> dict:
    allowed_tables = get_allowed_tables_for_role(role)
    if not allowed_tables:
        return {"answer": "No tabular data is available for your role.", "error": True}

    try:
        sql = translate_nl_to_sql(question, allowed_tables)
        if not sql:
            return {"answer": "No queryable tables are available.", "error": True}

        if not is_safe_query(sql):
            return {"answer": "Only SELECT queries are allowed.", "error": True}

        # Defence in depth: the schema handed to the model is already scoped to
        # this role, but re-check the tables it actually referenced.
        for table in extract_tables_from_sql(sql):
            if table not in allowed_tables:
                return {"answer": f"Access denied to table: {table}", "error": True}

        conn = get_duck_conn()
        rows = conn.execute(sql).fetchall()
        columns = [desc[0] for desc in conn.description]

        answer = (
            tabulate.tabulate([list(r) for r in rows], headers=columns, tablefmt="github")
            if rows
            else "Query executed, but no results found."
        )

        result = {"answer": answer}
        if return_sql:
            result["sql"] = sql
        return result

    except config.MissingCredentialError:
        raise
    except Exception as exc:
        return {"answer": f"Error: {exc}", "error": True}
