# AxiomInsight

A role-scoped question-answering service over a small set of internal company
documents. It routes each question to one of two backends — SQL over DuckDB for
tabular data, or vector retrieval over Chroma for prose — and restricts what a
user can see to their own department's documents plus anything marked general.

This is a personal project and a prototype. It is not production software; see
[Limitations](#limitations) for what that means concretely.

---

## What it actually does

1. **Classifies the question.** An LLM call decides whether the question is
   answerable from tabular data (`SQL`) or from documents (`RAG`). Results are
   memoised with `lru_cache`.
2. **Routes it.**
   - *SQL path:* the schema of the tables the user's role may read is put in a
     prompt, the model writes a `SELECT`, the query is validated and executed
     against DuckDB, and the rows come back as a Markdown table.
   - *RAG path:* the question is embedded and searched against Chroma with a
     role filter applied inside the query, optionally reranked by Cohere, and
     the retrieved chunks are passed to the answer model.
3. **Falls back.** If the SQL path errors or returns nothing, the question is
   retried against the document path.

Authentication is HTTP Basic against a SQLite user table, with bcrypt-hashed
passwords. The role used for filtering always comes from the authenticated
user, never from the request body.

---

## Architecture

![Architecture](static/images/architecture.png)

The role used for filtering is taken from the authenticated user at the FastAPI
layer and threaded through both paths. The final answer is returned as a
complete JSON response — it is not streamed.

**Storage**

| Store  | Holds                                          |
|--------|------------------------------------------------|
| SQLite | users, roles, document registry                |
| Chroma | embedded markdown chunks, tagged with a role   |
| DuckDB | tables loaded from uploaded CSVs, plus a `tables_metadata` role map |

---

## Role-based access control

Roles: `Admin`, `Finance`, `HR`, `Marketing`, `Engineering`, `Compliance`,
`General`. Admin sees everything; every other role sees its own documents plus
`General`.

**On the document path, the role filter is a pre-filter.** It is passed to
Chroma as a `where` clause on the query, so restricted chunks are never scored
and never enter the candidate set:

```python
# app/rag_utils/rag_module.py
search_kwargs = {"k": k, "filter": {"role": {"$in": [user_role, "general"]}}}
vectorstore.as_retriever(search_kwargs=search_kwargs, search_type="similarity")
```

The difference matters: a post-filter would fetch the global top-k and then
discard what the user may not see, which both leaks through ranking side
effects and silently shrinks the result set.

**On the SQL path**, the schema handed to the model is scoped to the role's
tables before the prompt is built, and the generated SQL is re-checked against
that same allowlist afterwards. The query is also rejected unless it begins
with `SELECT` and contains no DDL/DML keywords.

---

## Setup

Requires Python 3.11+ and an OpenAI API key.

```bash
git clone https://github.com/NilkanthSuthar/AxiomInsight.git
cd AxiomInsight

python3 -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # add your OPENAI_API_KEY
python -m scripts.seed      # creates roles, an admin user, loads + indexes sample docs
```

Then, in two terminals:

```bash
uvicorn app.main:app --port 8000     # API
streamlit run app/ui.py              # UI at http://localhost:8501
```

Default login is `admin` / `admin123` (override with `ADMIN_USERNAME` /
`ADMIN_PASSWORD` before seeding).

### Without an API key

The app starts, the UI loads, and you can log in. `GET /health` reports what is
configured:

```json
{"status":"ok","openai_key_configured":false,"cohere_reranking_enabled":false}
```

Asking a question returns HTTP 503 with instructions rather than a stack trace.
`python -m scripts.seed` still registers documents and loads CSVs into DuckDB;
re-run it after adding a key to build the vector index.

### Sample data

`static/uploads/` contains eight synthetic documents across the six
departments — financial and marketing reports, an engineering architecture
document, an employee handbook, a compliance policy (all `.md`), and one HR
CSV of 49 fictional employees. `scripts/seed.py` registers and indexes them.
None of it is real company data.

---

## API

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /health` | none | Readiness and which integrations are configured |
| `GET /login` | any user | Verify credentials, return role |
| `GET /roles` | any user | List roles |
| `POST /chat` | any user | Ask a question |
| `POST /create-user` | Admin | Create a user |
| `POST /create-role` | Admin | Create a role |
| `POST /upload-docs` | Admin | Upload and index a `.md` or `.csv` |

```bash
curl -u admin:admin123 -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is the parental leave policy?"}'
```

---

## Tech stack

| | |
|---|---|
| API | FastAPI, Uvicorn |
| UI | Streamlit |
| Orchestration | LangChain (LCEL), pinned to the 0.3 line |
| Vector store | Chroma, `text-embedding-3-small` |
| Analytics | DuckDB |
| Auth store | SQLite, bcrypt |
| Models | OpenAI `gpt-4o-mini` (routing, NL→SQL), `gpt-4o` (answers) |
| Reranking | Cohere `rerank-english-v3.0` (optional) |

Every dependency in `requirements.txt` is pinned.

---

## Limitations

Things this project does **not** do, listed because the gap between a README
and its code is worth being explicit about.

- **No streaming.** `/chat` returns a complete JSON response. The answer model
  is constructed with `streaming=True`, but the chain is awaited to completion,
  so nothing is streamed to the client.
- **Retrieval is dense-only.** Chroma vector similarity, optionally reranked.
  There is no BM25 or other sparse retriever, and therefore no hybrid search.
- **No retrieval evaluation.** There is no benchmark, golden set, or measured
  recall/MRR figure in this repository, so no accuracy claim is made anywhere
  in this README. Adding one is the obvious next step.
- **No tests yet.**
- **One vector store.** Chroma, chosen because it is embeddable and needs no
  server. There is no swappable vector-store interface and no Pinecone support.
- **No experiment tracking.** No MLflow. LangSmith tracing can be switched on
  via `LANGCHAIN_TRACING_V2=true` with a key, and is off by default.
- **Auth is minimal.** HTTP Basic, re-validated per request. No sessions, no
  tokens, no refresh, no rate limiting, no MFA.
- **Single-process assumptions.** SQLite and an embedded DuckDB file; fine for
  one local process, not for concurrent deployment.
- **The NL→SQL path trusts the model within a sandbox.** Generated SQL is
  restricted to `SELECT` and to the role's allowed tables, but the guard is a
  keyword and regex check, not a parser. Treat it as a prototype control.
- **Uploads are Admin-only** and limited to `.md` and `.csv`.

---

## Project layout

```
app/
  config.py              env-based settings, paths, credential checks
  main.py                FastAPI app: auth, RBAC, routes
  ui.py                  Streamlit client
  rag_utils/
    rag_module.py        indexing, role-filtered retriever, LCEL chain
    rag_chain.py         async wrapper over the chain
    query_classifier.py  SQL-vs-RAG routing
    csv_query.py         NL→SQL, validation, DuckDB execution
scripts/
  seed.py                bootstrap roles, admin user, sample documents
static/uploads/          sample documents, one directory per role
```

`roles_docs.db`, `chroma_db/` and `static/data/` are generated at runtime and
are not tracked.

---

## License

MIT — see [LICENSE](LICENSE).
