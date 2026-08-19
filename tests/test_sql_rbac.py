"""Access control on the NL-to-SQL path.

Covers the SQL-side counterpart to the vector-store pre-filter: the schema
handed to the model is scoped to the role before the prompt is built, and the
generated SQL is re-checked against the same allowlist afterwards.
"""

import sqlite3

import duckdb
import pytest

from app.rag_utils import csv_query


@pytest.fixture
def wired(tmp_path, monkeypatch):
    """A DuckDB with per-role tables and a matching SQLite document registry."""
    duck = duckdb.connect(str(tmp_path / "d.duckdb"))
    duck.execute("CREATE TABLE tables_metadata (table_name TEXT, role TEXT)")
    for table, role in [
        ("hr_data", "HR"),
        ("finance_ledger", "Finance"),
        ("holidays", "General"),
    ]:
        duck.execute(f"CREATE TABLE {table} (id INTEGER, secret TEXT)")
        duck.execute("INSERT INTO tables_metadata VALUES (?, ?)", (table, role))
    duck.execute("INSERT INTO hr_data VALUES (1, 'hr-only')")
    duck.execute("INSERT INTO finance_ledger VALUES (1, 'finance-only')")

    sqlite_path = tmp_path / "roles.db"
    conn = sqlite3.connect(sqlite_path)
    conn.execute(
        "CREATE TABLE documents (filename TEXT, headers_str TEXT, embedded INTEGER)"
    )
    conn.executemany(
        "INSERT INTO documents VALUES (?, ?, 1)",
        [
            ("hr_data.csv", "id,secret"),
            ("finance_ledger.csv", "id,secret"),
            ("holidays.csv", "id,secret"),
        ],
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(csv_query, "_duck_conn", duck)
    monkeypatch.setattr(csv_query.config, "SQLITE_PATH", sqlite_path)
    return duck


# --- which tables a role may touch -----------------------------------------
def test_admin_sees_every_table(wired):
    assert set(csv_query.get_allowed_tables_for_role("Admin")) == {
        "hr_data", "finance_ledger", "holidays"
    }


def test_department_sees_own_plus_general(wired):
    assert set(csv_query.get_allowed_tables_for_role("HR")) == {"hr_data", "holidays"}


def test_department_cannot_see_another_department(wired):
    assert "finance_ledger" not in csv_query.get_allowed_tables_for_role("HR")


def test_general_sees_only_general(wired):
    assert csv_query.get_allowed_tables_for_role("General") == ["holidays"]


def test_role_matching_is_case_insensitive(wired):
    assert csv_query.get_allowed_tables_for_role("hr") == csv_query.get_allowed_tables_for_role("HR")


def test_unknown_role_gets_only_general(wired):
    assert csv_query.get_allowed_tables_for_role("Nonexistent") == ["holidays"]


# --- the pre-filter: schema is scoped before the model sees it -------------
def test_schema_block_excludes_other_departments(wired):
    """The point of Phase 3c on the SQL side.

    An HR user's prompt must not contain Finance table or column names. If it
    did, access control would be happening after the model had already been
    shown what it may not use.
    """
    block = csv_query.build_schema_block(csv_query.get_allowed_tables_for_role("HR"))
    assert "hr_data" in block
    assert "finance_ledger" not in block


def test_schema_block_is_empty_when_role_has_no_tables(wired):
    assert csv_query.build_schema_block([]) == ""


# --- the post-check: second layer ------------------------------------------
@pytest.mark.parametrize(
    "sql,safe",
    [
        ("SELECT * FROM hr_data", True),
        ("select id from hr_data;", True),
        ("DROP TABLE hr_data", False),
        ("DELETE FROM hr_data", False),
        ("INSERT INTO hr_data VALUES (2,'x')", False),
        ("UPDATE hr_data SET secret='x'", False),
        ("SELECT * FROM hr_data; DROP TABLE hr_data", False),
        ("ATTACH 'other.db'", False),
        ("COPY hr_data TO 'out.csv'", False),
    ],
)
def test_only_read_only_queries_pass(sql, safe):
    assert csv_query.is_safe_query(sql) is safe


@pytest.mark.parametrize(
    "sql,tables",
    [
        ("SELECT * FROM hr_data", ["hr_data"]),
        ("SELECT * FROM a JOIN b ON a.id=b.id", ["a", "b"]),
        ("select x from Holidays", ["Holidays"]),
    ],
)
def test_referenced_tables_are_extracted(sql, tables):
    assert csv_query.extract_tables_from_sql(sql) == tables


@pytest.mark.asyncio
async def test_cross_role_query_is_refused(wired, monkeypatch):
    """Even if the model produced SQL against a forbidden table, it is denied."""
    monkeypatch.setattr(
        csv_query, "translate_nl_to_sql", lambda q, t: "SELECT * FROM finance_ledger"
    )
    result = await csv_query.ask_csv("show me the ledger", "HR", "hruser")
    assert result["error"] is True
    assert "finance_ledger" in result["answer"]


@pytest.mark.asyncio
async def test_permitted_query_returns_rows(wired, monkeypatch):
    monkeypatch.setattr(
        csv_query, "translate_nl_to_sql", lambda q, t: "SELECT * FROM hr_data"
    )
    result = await csv_query.ask_csv("show hr data", "HR", "hruser")
    assert "error" not in result
    assert "hr-only" in result["answer"]


@pytest.mark.asyncio
async def test_role_with_no_tables_is_told_so(wired, monkeypatch):
    monkeypatch.setattr(csv_query, "get_allowed_tables_for_role", lambda r: [])
    result = await csv_query.ask_csv("anything", "Ghost", "ghost")
    assert result["error"] is True
