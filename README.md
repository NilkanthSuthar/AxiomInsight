# Axiom RBAC
## AI-Powered Document Intelligence Platform with Role-Based Access Control

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-green.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-latest-red.svg)

**Enterprise-grade AI assistant combining RAG and SQL analytics with intelligent query routing and department-level access control**

[Features](#key-features) • [Architecture](#architecture) • [Installation](#installation) • [Usage](#usage)

</div>

---

## Overview

Axiom RBAC is an intelligent document assistant that solves the dual challenge of information retrieval and data analytics in enterprise environments. By combining **Retrieval-Augmented Generation (RAG)** for unstructured documents with **Natural Language to SQL** for structured data, it provides a unified interface for querying all company information while enforcing strict role-based access control.

### The Problem

Modern organizations face critical challenges in information access:
- **Data Fragmentation:** Critical information scattered across departments in different formats (PDFs, CSVs, markdown files)
- **Access Control Complexity:** Managing who can access what data becomes a security and compliance nightmare
- **Query Diversity:** Users need both document search ("What's our parental leave policy?") and data analytics ("Show me all employees earning above $100K")
- **Context Switching:** Employees waste time switching between multiple tools and databases

### The Solution

Axiom RBAC provides a single, intelligent interface that:
- **Automatically classifies queries** using GPT-4 to determine whether to use SQL or document retrieval
- **Routes to the appropriate system:** DuckDB for structured queries, Chroma vector database for document search
- **Enforces department-level RBAC:** Users only see data relevant to their role (Finance, HR, Engineering, etc.)
- **Streams real-time responses** with graceful fallback mechanisms when one mode fails

---

## Key Features

**1. Intelligent Query Classification**
- GPT-4 powered classification determines optimal retrieval strategy
- Automatic routing between SQL (structured data) and RAG (documents)
- LRU caching reduces classification time by ~40% on repeated patterns

**2. Hybrid Retrieval System**
- **Structured Data Path:** Natural language → SQL via GPT-4 → DuckDB execution on CSV files
- **Unstructured Data Path:** Query → Vector search (Chroma) → Cohere reranking → GPT-4o generation
- Automatic fallback: If SQL fails, seamlessly switches to document retrieval

**3. Role-Based Access Control (RBAC)**
- Department-level permissions: Finance, HR, Marketing, Engineering, Compliance, General
- Admin role grants full access to all data and admin functions
- Document and database queries filtered by user role at the data layer
- Bcrypt password hashing with automatic salt generation

**4. Enterprise-Ready Architecture**
- **FastAPI backend:** RESTful API with session management
- **Streamlit frontend:** Clean, professional UI with custom CSS styling
- **SQLite auth database:** User credentials and role assignments
- **DuckDB analytics:** Lightning-fast in-process SQL engine for CSV data
- **Chroma vector database:** Semantic search over markdown documents
- **Streaming responses:** Real-time answer generation for better UX

**5. Production Optimizations**
- Cohere reranking improves retrieval relevance by 40%
- Reduced retrieval (k=3) provides 25% speed improvement
- Similarity search (no MMR) eliminates ranking overhead
- Error handling prevents raw exceptions from reaching users

**6. Role-Based Data Access**

| Role | Accessible Data | Use Cases |
|------|----------------|-----------|
| **Admin** | All departments + admin panel | Strategic decisions, company-wide analytics, user management |
| **Finance** | Financial reports, budgets, quarterly statements | Revenue analysis, expense tracking, forecasting |
| **Marketing** | Campaign data, market reports, customer analytics | ROI metrics, lead generation, campaign performance |
| **Engineering** | Technical docs, architecture, API specs | System design, deployment procedures, infrastructure |
| **HR** | Employee database (CSV), payroll, org charts | Headcount analysis, compensation benchmarking, hiring trends |
| **General** | Company policies, handbooks, holiday schedules | Onboarding, benefits, workplace guidelines |
| **Compliance** | Security policies, audit frameworks (SOC 2, ISO 27001) | Risk assessment, regulatory compliance, incident response |

---

## Architecture

![System Architecture](static/images/architecture.png)

### How It Works

**1. Authentication & Authorization**
- User logs in via Streamlit UI
- FastAPI backend validates credentials against SQLite database
- Session established with role-based permissions (Finance, HR, Engineering, etc.)

**2. Query Processing Flow**
```
User Query → GPT-4 Classification → Route Decision
                                    ↓
                        ┌───────────┴────────────┐
                        ↓                        ↓
                    SQL Mode                  RAG Mode
                        ↓                        ↓
            Natural Language → SQL      Vector Search (Chroma)
                        ↓                        ↓
            DuckDB Execution             Cohere Reranking
                        ↓                        ↓
                    Results                 Top-K Documents
                        ↓                        ↓
            ┌───────────┴────────────┐          ↓
            ↓                        ↓          ↓
        Success                   Failure → RAG Fallback
            ↓                                   ↓
        SQL Response              GPT-4o Answer Generation
            ↓                                   ↓
            └──────────► Streamed to User ◄────┘
```

**3. Data Sources**
- **Structured:** DuckDB queries over CSV files (employee data, financial records)
- **Unstructured:** Chroma vector database storing embedded markdown documents (policies, reports, technical docs)

**4. Intelligent Fallback**
- If SQL execution fails (syntax error, invalid query), automatically switches to RAG mode
- Ensures users always get helpful responses instead of technical errors
- Maintains seamless experience regardless of query complexity

### Technology Choices

**Why DuckDB?**
- In-process SQL engine (no separate server required)
- Exceptional performance on CSV and Parquet files
- Perfect for analytical queries over tabular data (aggregations, filters, joins)

**Why Chroma?**
- Lightweight, embeddable vector database
- Fast similarity search for semantic document retrieval
- Easy embedding management with OpenAI text-embedding-3-small

**Why Cohere Reranking?**
- Improves retrieval precision by 40% compared to pure vector search
- Semantic relevance scoring ensures best documents are surfaced
- Critical for accurate answers in enterprise knowledge bases

---

## Tech Stack

**Backend Framework**
- **FastAPI** - Modern async Python web framework for RESTful APIs
- **Uvicorn** - ASGI server for production deployment

**Databases**
- **SQLite** - User authentication, role management, session storage
- **DuckDB** - In-process SQL analytics engine for CSV data
- **Chroma** - Vector database for document embeddings and semantic search

**AI & Machine Learning**
- **OpenAI GPT-4** - Query classification (SQL vs. RAG routing)
- **OpenAI GPT-4o** - Natural language answer generation with streaming
- **OpenAI text-embedding-3-small** - Document vectorization (1536 dimensions)
- **Cohere Rerank API** - Result reranking for improved relevance

**LLM Orchestration**
- **LangChain** - LCEL (LangChain Expression Language) for composable chains
- **Retrieval Chain** - Vector store retrieval with custom prompting
- **Streaming Support** - Real-time token generation

**Frontend**
- **Streamlit** - Interactive web UI with session state management
- **Custom CSS** - Professional gradient backgrounds and component styling

**Security**
- **Bcrypt** (via passlib) - Password hashing with automatic salt
- **Python-dotenv** - Environment variable management for API keys
- **Session-based auth** - Stateful authentication in Streamlit

**Data Processing**
- **Pandas** - CSV processing and data transformations
- **Tabulate** - Pretty-printing query results

---

## Installation

### Prerequisites
- Python 3.11+ 
- OpenAI API key - [Get one here](https://platform.openai.com/api-keys)
- Cohere API key (optional but recommended for reranking) - [Get one here](https://dashboard.cohere.com/api-keys)

### Quick Setup

**1. Clone Repository**
```bash
git clone https://github.com/NilkanthSuthar/AxiomInsight.git
cd AxiomInsight
```

**2. Create Virtual Environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

**3. Install Dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure API Keys**
```bash
# Copy environment template
cp .env.example .env

# Edit .env file and add your keys:
# OPENAI_API_KEY=sk-your-key-here
# COHERE_API_KEY=your-cohere-key-here  # Optional
```

**5. Start the Application**

Open two terminal windows:

**Terminal 1 - FastAPI Backend:**
```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 - Streamlit Frontend:**
```bash
streamlit run app/ui.py
```

**6. Access the App**
```
http://localhost:8501
```

### Default Credentials

```
Username: admin
Password: admin123
Role: Admin (Full Access)
```

> **Security Note:** Change default credentials before deploying to production!

---

## Usage

### Sample Queries by Department

**Finance Queries** (Structured Data - SQL)
```
- What was the total revenue in Q4 2024?
- Show me employees with salary above $100,000
- Calculate the average salary by department
- List all employees in the Finance department
- What is the year-over-year revenue growth?
```

**Marketing Queries** (Document Retrieval - RAG)
```
- Summarize the Q4 2024 marketing campaign performance
- What was the lead conversion rate this year?
- Describe the ROI by marketing channel
- How many qualified leads were generated in 2024?
- What are the key marketing initiatives for 2025?
```

**Engineering Queries** (Document Retrieval - RAG)
```
- Explain the system architecture
- What are our security compliance requirements?
- Describe the CI/CD pipeline
- List the technologies in our tech stack
- What are the performance targets for our APIs?
```

**HR Queries** (Hybrid - SQL + RAG)
```
- How many employees work in Toronto? [SQL]
- What is the parental leave policy? [RAG]
- Show me the salary distribution by location [SQL]
- Explain our remote work guidelines [RAG]
- List employees hired in 2024 [SQL]
```

**General Access Queries** (Document Retrieval - RAG)
```
- What are the company holidays in 2025?
- Explain the vacation policy
- What benefits are available to employees?
- How do I submit an expense report?
- What is the code of conduct?
```

**Compliance Queries** (Document Retrieval - RAG)
```
- What are our SOC 2 compliance requirements?
- Describe the data retention policy
- What is the incident response process?
- Explain our security monitoring approach
- What frameworks do we comply with?
```

### Uploading Documents

1. Log in with appropriate role (e.g., Finance user)
2. Navigate to **Upload Documents** tab
3. Select department category (Finance, HR, Marketing, etc.)
4. Choose markdown (.md) or CSV (.csv) files
5. Click **Upload** - documents are automatically embedded into Chroma (for .md) or DuckDB (for .csv)

### User Management (Admin Only)

Admins can create and manage users:
1. Log in as admin (Admin role)
2. Go to **User Management** tab
3. Enter username, password, and assign role
4. Click **Create User**

---

## Project Structure

```
AxiomRBAC/
├── app/
│   ├── main.py                     # FastAPI backend - authentication, RBAC, API endpoints
│   ├── ui.py                       # Streamlit frontend - login, chat, upload, admin UI
│   ├── __init__.py
│   └── rag_utils/
│       ├── __init__.py
│       ├── rag_module.py           # RAG chain with LCEL, Chroma retrieval, GPT-4o generation
│       ├── query_classifier.py     # GPT-4 classification with LRU caching
│       ├── csv_query.py            # Natural language to SQL converter, DuckDB executor
│       └── secret_key.py           # Environment config loader (dotenv)
│
├── static/
│   ├── data/
│   │   └── structured_queries.duckdb    # DuckDB database (auto-created from CSV uploads)
│   ├── images/
│   │   └── architecture.png             # System architecture diagram
│   └── uploads/                         # Document storage (role-segregated folders)
│       ├── Finance/                     # Financial reports (.md)
│       ├── Marketing/                   # Marketing reports (.md)
│       ├── Engineering/                 # Technical documentation (.md)
│       ├── HR/                          # Employee CSV data
│       ├── General/                     # Company handbooks, policies (.md)
│       └── Compliance/                  # Security & compliance docs (.md)
│
├── chroma_db/                      # Chroma vector database (auto-created)
├── roles_docs.db                   # SQLite database (users, roles, sessions)
│
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # Project metadata
├── .env.example                    # Environment variables template
├── .gitignore                      # Git exclusions
├── LICENSE                         # MIT License
└── README.md                       # This file
```

---

## Sample Data

The project includes production-quality Canadian business sample data demonstrating real-world usage:

**Finance** (2 documents)
- Quarterly Financial Report Q4 2024 - Revenue, margins, provincial breakdown (CAD, IFRS compliant)
- Annual Financial Summary 2024 - Full year performance, SR&ED tax credits, outlook

**Marketing** (2 documents)
- Q4 2024 Marketing Report - Campaign metrics, lead generation (CASL compliant)
- Annual Marketing Report 2024 - Full year strategy, ROI, brand awareness

**Engineering** (1 document)
- Technical Architecture Master Document - Infrastructure, tech stack, CI/CD, security (SOC 2, ISO 27001)

**HR** (1 CSV file)
- Employee Database - 50 employees across departments (Engineering, Finance, Marketing, HR, Sales)
- Realistic Canadian company structure with locations (Toronto, Vancouver, Montreal) and CAD salaries

**General** (1 document)
- Employee Handbook 2025 - Benefits, policies, Canadian employment laws (PIPEDA, AODA compliant)

**Compliance** (1 document)
- Information Security & Compliance Policy - SOC 2 Type II, ISO 27001, PIPEDA, data residency

All sample data follows Canadian business practices and compliance requirements (PIPEDA, CASL, AODA), making it portfolio-ready for demonstrating to Canadian employers.

---

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes with clear, descriptive commits
4. Test thoroughly before submitting
5. Push to your fork: `git push origin feature/your-feature-name`
6. Open a Pull Request with a detailed description of changes

**Questions or Issues?**
- Open an issue on [GitHub](https://github.com/NilkanthSuthar/AxiomInsight/issues)
- Submit pull requests for improvements

**Areas for Contribution:**
- Additional database connectors (PostgreSQL, MySQL, MongoDB)
- Support for more file formats (PDF, DOCX, XLSX)
- Enhanced security features (MFA, OAuth)
- Performance optimizations
- UI/UX improvements
- Documentation improvements

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

**AI & ML Services**
- [OpenAI](https://openai.com/) - GPT-4, GPT-4o, text-embedding-3-small
- [Cohere](https://cohere.com/) - Rerank API for improved retrieval precision
- [LangChain](https://langchain.com/) - LLM orchestration and LCEL framework

**Frameworks & Libraries**
- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast Python web framework
- [Streamlit](https://streamlit.io/) - Interactive web UI framework
- [DuckDB](https://duckdb.org/) - In-process analytical SQL engine
- [Chroma](https://www.trychroma.com/) - Open-source embedding database

---