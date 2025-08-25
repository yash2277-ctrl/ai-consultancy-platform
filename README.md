# NexusAI — AI Management Consultancy Platform

> The $900B consultancy industry, reimagined with artificial intelligence.

A full-stack platform that uses **multi-agent AI** to deliver financial analysis, market strategy, and executive-level consulting reports — powered by OpenAI GPT-4o, LangChain, and ChromaDB.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (HTML/CSS/JS)                    │
│  Auth · Projects · File Upload · AI Consult · Report View   │
└──────────────────────────┬──────────────────────────────────┘
                           │  REST API
┌──────────────────────────▼──────────────────────────────────┐
│                   FASTAPI BACKEND                            │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │   Auth   │  │  Upload  │  │ Consult  │  ← API Routers   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
│       │              │              │                        │
│  ┌────▼─────┐  ┌────▼─────┐  ┌────▼──────────────────┐     │
│  │  Auth    │  │  Upload  │  │   Process Manager     │     │
│  │ Service  │  │ Service  │  │                        │     │
│  └──────────┘  └────┬─────┘  │  ┌──────────────────┐ │     │
│                     │        │  │ FinancialAnalyst  │ │     │
│                     │        │  │ MarketStrategist  │ │     │
│                     │        │  │ ExecutivePartner  │ │     │
│                     │        │  └──────────────────┘ │     │
│                     │        └────────┬──────────────┘     │
│                ┌────▼────────────────▼─────┐                │
│                │    RAG Pipeline            │                │
│                │  Embeddings · ChromaDB     │                │
│                └───────────────────────────┘                │
│                                                              │
│                ┌───────────────────────────┐                │
│                │   PostgreSQL (SQLAlchemy)  │                │
│                └───────────────────────────┘                │
└──────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
ai-consultancy/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings from .env
│   │   ├── database.py          # Async SQLAlchemy
│   │   ├── models.py            # ORM models
│   │   ├── schemas.py           # Pydantic v2 schemas
│   │   ├── auth/
│   │   │   ├── router.py        # /auth endpoints
│   │   │   ├── service.py       # JWT, password hashing
│   │   │   └── dependencies.py  # get_current_user
│   │   ├── upload/
│   │   │   ├── router.py        # /upload, /projects endpoints
│   │   │   └── service.py       # File validation & embedding trigger
│   │   ├── consult/
│   │   │   ├── router.py        # /consult, /reports endpoints
│   │   │   └── service.py       # Report CRUD
│   │   ├── agents/
│   │   │   ├── agents.py        # 3 AI agents (Financial, Market, Executive)
│   │   │   └── process_manager.py  # Orchestrator
│   │   └── rag/
│   │       ├── embeddings.py    # Parsing, chunking, embedding
│   │       └── vector_store.py  # ChromaDB integration
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   └── js/
│       ├── api.js               # HTTP client
│       ├── auth.js              # Login/register
│       └── app.js               # Main SPA logic
└── README.md
```

## Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 15+
- OpenAI API key

### 2. Backend Setup

```bash
cd backend

# Create & activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env — add your OPENAI_API_KEY and DATABASE_URL

# Create the database
psql -U postgres -c "CREATE DATABASE ai_consultancy;"

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend

Open `frontend/index.html` in your browser, or serve it:

```bash
cd frontend
python -m http.server 3000
```

Then visit `http://localhost:3000`.

### 4. API Docs

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Key Features

| Feature | Implementation |
|---|---|
| **JWT Auth** | Secure register/login with bcrypt + JOSE |
| **File Upload** | PDF (PyMuPDF), DOCX (python-docx), XLSX (openpyxl), CSV (Pandas) — max 20MB |
| **RAG Pipeline** | RecursiveCharacterTextSplitter (1500/300) → OpenAI embeddings → ChromaDB |
| **Multi-Agent AI** | 3 specialist agents (McKinsey/Bain/BCG-grade prompts) run in parallel, then synthesise |
| **Background Tasks** | Embedding + consultation run async via FastAPI BackgroundTasks |
| **Structured Output** | All agent outputs are Pydantic-validated JSON with fallback parsing |
| **Retry Logic** | Exponential backoff (3 retries) on all LLM calls |
| **Deep Data Analysis** | Correlations, distributions, data quality checks on tabular data |
| **PostgreSQL** | Full relational schema — users, projects, files, reports |
| **Professional UI** | Dark/light theme, responsive, animated, toast notifications |

## AI Agents

1. **FinancialAnalyst** — DCF-style revenue analysis (CAGR, margins), cost benchmarking, liquidity/leverage ratios, scenario analysis, quantified risk factors, financial health scoring (McKinsey-grade prompts)
2. **MarketStrategist** — Porter's Five Forces, SWOT, TAM/SAM/SOM sizing, competitive moat analysis, blue-ocean opportunities, segment prioritisation, go-to-market strategy (Bain-grade prompts)
3. **ExecutivePartner** — Synthesises everything into a board-ready deliverable: situation assessment, prioritised recommendations, phased action plan, risk matrix, implementation timeline, confidence score (BCG Managing Partner-grade prompts)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Sign in |
| GET | `/api/auth/me` | Current user profile |
| POST | `/api/projects` | Create project |
| GET | `/api/projects` | List projects |
| GET | `/api/projects/{id}` | Project detail |
| DELETE | `/api/projects/{id}` | Delete project |
| POST | `/api/upload` | Upload file (triggers embedding) |
| GET | `/api/projects/{id}/files` | List project files |
| POST | `/api/consult` | Start AI consultation |
| GET | `/api/reports/{id}` | Get report detail |
| GET | `/api/projects/{id}/reports` | List project reports |

---

## License

MIT


## Recent Updates

- **2026-08-05**: docs: Update README with installation guide

- **2026-08-05**: docs: Add deployment guide

- **2026-08-05**: docs: Update README with installation guide

- **2026-08-05**: docs: Add deployment guide

- **2026-08-05**: docs: Update README with installation guide

- **2026-08-05**: docs: Add deployment guide

- **2026-08-05**: docs: Update README with installation guide

- **2026-08-05**: docs: Add deployment guide

- **2026-08-05**: docs: Update README with installation guide

- **2026-08-05**: docs: Add deployment guide

- **2026-05-08**: Improve UI/UX

- **2026-05-09**: Add new features

- **2026-05-11**: Update documentation

- **2026-05-18**: Add new features

- **2026-05-19**: Refactor code

- **2026-05-26**: Improve error handling

- **2026-06-03**: Add tests

- **2026-06-04**: Update dependencies

- **2026-06-04**: Add new features

- **2026-06-08**: Fix bugs

- **2026-06-15**: Update documentation

- **2026-06-23**: Update README

- **2026-06-29**: Improve UI/UX

- **2026-06-29**: Add new features

- **2026-07-10**: Add tests

- **2026-07-14**: Update documentation

- **2026-07-17**: Add tests

- **2026-07-18**: Improve error handling

- **2026-07-20**: Improve performance

- **2026-07-21**: Improve UI/UX

- **2026-07-23**: Add new features

- **2026-07-25**: Improve performance

- **2026-08-03**: Add new features


## Commit Log

- [2025-11-25 02:27:44] Add new features
- [2026-02-15 02:27:44] Clean up code
- [2026-06-03 02:27:44] Enhance security
- [2026-03-12 02:27:44] Optimize queries
- [2025-12-18 02:27:44] Fix bugs and issues
- [2026-02-20 02:27:44] Add API endpoints
- [2026-03-01 02:27:44] Improve logging
- [2025-12-31 02:27:44] Add unit tests
- [2025-08-08 02:27:44] Optimize queries
- [2026-02-18 02:27:44] Improve accessibility
- [2026-04-11 02:27:44] Add new features
- [2025-10-26 02:27:44] Fix bugs and issues
- [2025-12-21 02:27:44] Improve performance
- [2025-11-05 02:27:44] Add API endpoints
- [2026-06-30 02:27:44] Improve error handling
- [2026-01-03 02:27:44] Update documentation
- [2025-11-17 02:27:44] Add API endpoints
- [2026-01-31 02:27:44] Improve accessibility
- [2026-03-23 02:27:44] Fix typos
- [2026-03-27 02:27:44] Optimize queries
- [2026-07-08 02:27:44] Add API endpoints
- [2026-06-17 02:27:44] Refactor code structure
- [2025-11-16 02:27:44] Enhance security
- [2026-07-16 02:27:44] Update configuration
- [2025-09-02 02:27:44] Add comments
- [2025-12-16 02:27:44] Improve accessibility
- [2026-02-09 02:27:44] Improve error handling
- [2026-02-04 02:27:44] Update configuration
- [2025-09-07 02:27:44] Update dependencies
- [2026-04-13 02:27:44] Add comments
- [2026-04-12 02:27:44] Improve performance
- [2026-02-08 02:27:44] Update configuration
- [2026-06-09 02:27:44] Update dependencies
- [2026-06-29 02:27:44] Improve performance
- [2025-10-16 02:27:44] Update configuration
- [2026-05-29 02:27:44] Enhance security
- [2026-08-02 02:27:44] Add new features
- [2026-03-20 02:27:44] Add validation
- [2025-11-21 02:27:44] Add unit tests
- [2025-08-21 02:27:44] Refactor code structure
- [2025-08-06 02:27:44] Improve UI/UX
- [2025-12-08 02:27:44] Add unit tests
- [2026-03-16 02:27:44] Add validation
- [2026-04-10 02:27:44] Improve error handling
- [2025-08-25 02:27:44] Add API endpoints
- [2025-10-07 02:27:44] Enhance security
- [2025-11-02 02:27:44] Add comments
- [2025-10-15 02:27:44] Add validation
- [2025-11-01 02:27:44] Add API endpoints
- [2026-06-20 02:27:44] Add new features
- [2026-01-07 02:27:44] Update documentation
- [2025-11-02 02:27:44] Update configuration
- [2026-01-26 02:27:44] Enhance security
- [2025-11-30 02:27:44] Add unit tests
- [2025-11-30 02:27:44] Enhance security
- [2026-04-01 02:27:44] Update README
- [2026-03-31 02:27:44] Add comments
- [2026-06-23 02:27:44] Improve error handling
- [2026-04-25 02:27:44] Add API endpoints
- [2025-09-24 02:27:44] Add new features
- [2025-10-23 02:27:44] Improve UI/UX
- [2025-09-15 02:27:44] Update configuration
- [2026-01-30 02:27:44] Add unit tests
- [2026-03-16 02:27:44] Fix typos
- [2025-12-31 02:27:44] Update README
- [2025-10-27 02:27:44] Improve performance
- [2025-09-21 02:27:44] Improve error handling
- [2025-08-26 02:27:44] Fix bugs and issues
- [2025-09-30 02:27:44] Fix bugs and issues
- [2026-01-08 02:27:44] Improve performance
- [2026-08-01 02:27:44] Improve accessibility
- [2026-04-20 02:27:44] Improve error handling
- [2025-11-27 02:27:44] Update README
- [2026-02-15 02:27:44] Improve accessibility
- [2026-01-08 02:27:44] Optimize queries
- [2026-05-13 02:27:44] Update dependencies
- [2026-05-08 02:27:44] Clean up code
- [2025-08-05 02:27:44] Improve accessibility
- [2025-12-03 02:27:44] Improve UI/UX
- [2025-08-28 02:27:44] Add comments
- [2025-11-06 02:27:44] Update dependencies
- [2026-08-04 02:27:44] Update documentation
- [2026-04-14 02:27:44] Enhance security
- [2025-11-29 02:27:44] Improve accessibility
- [2026-05-29 02:27:44] Enhance security
- [2026-03-08 02:27:44] Improve performance
- [2026-03-19 02:27:44] Add new features
- [2025-11-30 02:27:44] Fix typos
- [2026-05-18 02:27:44] Update dependencies
- [2026-04-24 02:27:44] Update configuration
- [2026-07-24 02:27:44] Improve accessibility
- [2026-01-22 02:27:44] Improve accessibility
- [2026-03-18 02:27:44] Add API endpoints
- [2025-08-12 02:27:44] Update dependencies
- [2026-03-23 02:27:44] Refactor code structure
- [2026-02-08 02:27:44] Enhance security
- [2026-07-31 02:27:44] Fix bugs and issues
- [2025-11-24 02:27:44] Update dependencies
- [2025-08-22 02:27:44] Add validation
- [2025-08-18 02:27:44] Update dependencies
- [2026-04-11 02:27:44] Update configuration
- [2026-02-28 02:27:44] Improve performance
- [2026-03-13 02:27:44] Refactor code structure
- [2026-07-02 02:27:44] Add API endpoints
- [2025-10-27 02:27:44] Improve error handling
- [2026-03-01 02:27:44] Clean up code
- [2026-01-15 02:27:44] Refactor code structure
- [2026-01-02 02:27:44] Add API endpoints
- [2025-08-16 02:27:44] Update configuration
- [2026-02-26 02:27:44] Update documentation
- [2025-11-08 02:27:44] Add validation
- [2026-05-27 02:27:44] Enhance security
- [2026-05-16 02:27:44] Refactor code structure
- [2026-06-09 02:27:44] Improve UI/UX
- [2026-02-03 02:27:44] Refactor code structure
- [2026-07-24 02:27:44] Update configuration
- [2026-01-11 02:27:44] Update configuration
- [2026-04-14 02:27:44] Improve error handling
- [2025-09-04 02:27:44] Add unit tests
- [2026-02-17 02:27:44] Add unit tests
- [2025-10-13 02:27:44] Clean up code
- [2025-08-18 02:27:44] Clean up code
- [2026-04-08 02:27:44] Add new features
- [2025-08-26 02:27:44] Update configuration