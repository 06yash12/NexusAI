# NEXUS AI — Enterprise Intelligence Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev/)
[![DuckDB](https://img.shields.io/badge/DuckDB-OLAP-FFF000.svg)](https://duckdb.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_Inference-white.svg)](https://ollama.ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A local-first enterprise analytics platform. Ask questions in plain English over your CSV/Excel data and PDF/DOCX documents. All AI inference, vector embeddings, and SQL execution run on your machine — **zero data leakage**.

## How It Works

```
"Show me revenue by region for last quarter"
        │
        ▼
NL-to-SQL ──▶ SQLGlot AST validation ──▶ DuckDB execution ──▶ verified numbers
                                                                    │
Documents ──▶ Vector search (ChromaDB) + BM25 (lexical) ──▶ RRF fusion ──▶ cited excerpts
                                                                    │
                                                    Evidence-grounded LLM synthesis
```

The LLM **never calculates numbers**. All math runs in DuckDB. The LLM only translates intent and narrates verified results — eliminating mathematical hallucinations.

## Key Features

- **NL-to-SQL with self-healing** — Qwen3:4b generates SQL, SQLGlot validates (SELECT-only, table allowlist, function blacklist), auto-retries on failure
- **Hybrid Document RAG** — Dense vector search (nomic-embed-text) + lexical BM25 + Reciprocal Rank Fusion for 40-60% better retrieval precision
- **Zero data leakage** — Ollama, ChromaDB, DuckDB all run locally. No external API calls
- **Auto domain detection** — Healthcare, Retail, or General BI from column names
- **Anti-inflation joins** — Prevents double-counting in 1-to-many relationships
- **Interactive dashboard** — KPIs, multi-dimensional filters, 7 chart types
- **Automated insights** — MoM trends, regional disparities, collection rates, anomaly flags
- **Report export** — One-click Excel (OpenPyXL) and PDF (ReportLab) with verified numbers

## Quick Start

### Prerequisites
- Python 3.11+ ([python.org](https://www.python.org/downloads/))
- Node.js 18+ ([nodejs.org](https://nodejs.org/))
- Ollama ([ollama.com](https://ollama.com/)) with models:
  ```bash
  ollama pull qwen3:4b
  ollama pull nomic-embed-text
  ```

### Run

```bash
# Terminal 1 — Ollama
ollama serve

# Terminal 2 — Backend
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate  |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 3 — Frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 → create a workspace → upload your data → start asking questions.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, Tailwind CSS, Recharts |
| Backend | FastAPI, Python 3.11+, Pydantic v2 |
| OLAP | DuckDB (in-process columnar engine) |
| Metadata | PostgreSQL / SQLite fallback |
| Vector DB | ChromaDB (HNSW cosine index) |
| LLM | Qwen3:4b via Ollama |
| Embeddings | nomic-embed-text (768-dim) via Ollama |
| Retrieval | BM25Okapi + Reciprocal Rank Fusion |
| SQL Safety | SQLGlot AST validation |
| Documents | PyMuPDF (PDF), python-docx (DOCX) |
| Reports | OpenPyXL (Excel), ReportLab (PDF) |

## Testing

```bash
cd backend
pytest tests -v
```

25 tests covering SQL guard safety, ingestion validation, dashboard math, report generation, API lifecycle, intent routing, and chunking.

## Documentation

For ML pipeline details, RAG architecture, model configuration, and future enhancements, see **[PROJECT_DOCS.md](PROJECT_DOCS.md)**.

## Roadmap

- **Voice-Based Analytics** — Real-time STT via Web Speech API, voice-driven chart drill-downs, local TTS for audible debriefs
- **Multilingual Intelligence** — Hindi, Kannada, Marathi support with cross-lingual NL-to-SQL and localized dashboards
- **Agentic Query Planning** — Multi-step question decomposition with sequential DuckDB execution and tool-use patterns

## License

MIT — see [LICENSE](LICENSE).
