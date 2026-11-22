# NEXUS AI — Project Documentation

## What It Does

NEXUS AI is a local-first ML platform that turns natural language into verified analytics. It combines NL-to-SQL generation with hybrid RAG over enterprise documents — all running on your machine with zero data leakage.

**Two ML pipelines:**
- **Structured data** (CSV/Excel) → NL-to-SQL → DuckDB → verified numbers
- **Unstructured documents** (PDF/DOCX) → Hybrid RAG (vector + BM25 + RRF) → cited excerpts

---

## ML Tech Stack

| Component | Technology | Role |
|-----------|-----------|------|
| LLM | Qwen3:4b via Ollama | NL-to-SQL generation, evidence-grounded synthesis |
| Embeddings | nomic-embed-text (768-dim) | Dense vector representations for semantic search |
| Vector DB | ChromaDB (HNSW cosine) | Persistent vector storage and similarity search |
| Lexical Search | BM25Okapi (Rank-BM25) | Keyword-based probabilistic retrieval |
| Fusion | Reciprocal Rank Fusion (RRF) | Merges vector + lexical rankings into consensus |
| SQL Engine | DuckDB (in-process OLAP) | Deterministic columnar query execution |
| SQL Safety | SQLGlot AST validation | Parse-level read-only enforcement, table allowlist |
| Document Parsing | PyMuPDF, python-docx | Page-level text extraction with verified page numbers |
| Chunking | Custom sliding window | 250-word chunks, 50-word overlap (~350 tokens) |

---

## Pipeline 1: NL-to-SQL

### How It Works

```
User: "What was total revenue by region last quarter?"
  │
  ▼
1. Schema Context Build
   → DuckDB introspects table columns, types, sample values
   → Domain classifier detects Retail/Healthcare/General from column names
   → Domain-specific rules + currency symbol injected into prompt
   │
   ▼
2. LLM SQL Generation
   → Qwen3:4b generates DuckDB SQL from schema + question
   → Temperature: 0.1 (low creativity, high determinism)
   │
   ▼
3. SQLGlot AST Validation
   → Parse SQL into AST (DuckDB dialect)
   → Enforce SELECT-only (block INSERT/UPDATE/DELETE/DROP/ALTER/CREATE)
   → Block multiple statements (semicolon injection)
   → Verify all tables exist in project's allowlist
   → Block dangerous functions (read_csv, system, version, scan)
   → Inject LIMIT 500 if missing
   │
   ▼
4. Execution & Self-Healing
   → DuckDB executes validated SQL
   → If fails → error feedback sent back to LLM → regenerate (max 2 retries)
   → Timing recorded in milliseconds
   │
   ▼
5. Evidence-Grounded Synthesis
   → Query results (columns + rows) packaged as JSON evidence
   → LLM synthesizes natural language answer grounded in actual data
   → System prompt: "NEVER invent numbers not present in the data"
```

**Why this matters:** The LLM never calculates numbers. All math runs in DuckDB. The LLM only translates intent and narrates results. This eliminates mathematical hallucinations.

**Example:**
```
Question: "Which departments have the highest outstanding balances?"

LLM generates:
  SELECT department, SUM(outstanding_amount_inr) as outstanding
  FROM encounters
  GROUP BY department
  ORDER BY outstanding DESC
  LIMIT 5

SQLGlot validates → DuckDB executes → 12ms

Answer: "The Cardiology department has the highest outstanding balance
of ₹8,45,000, followed by Orthopedics at ₹6,20,500..."
```

---

## Pipeline 2: Hybrid Document RAG

### How It Works

```
User: "What does the security policy say about data retention?"
  │
  ▼
1. Document Ingestion (offline, at upload time)
   → PyMuPDF extracts text per page (preserves page numbers)
   → DOCX: paragraphs + table cells grouped into ~500-word logical pages
   → Sliding window chunking: 250 words, 50-word overlap
   → Each chunk tagged with: document_id, filename, page_number, chunk_index
   → nomic-embed-text generates 768-dim vectors (batch size: 32)
   → ChromaDB stores vectors + metadata in project-scoped collection
   │
   ▼
2. Query-Time Hybrid Retrieval
   ├─ Vector Search:
   │    query → nomic-embed-text → 768-dim vector
   │    → ChromaDB cosine similarity → top 18 candidates
   │
   ├─ Lexical Search:
   │    query → tokenize (lowercase, strip punctuation)
   │    → BM25Okapi probabilistic scoring → top 18 candidates
   │
   ▼
3. Reciprocal Rank Fusion (RRF)
   Score(d) = Σ 1/(60 + rank)   across both retrieval methods
   
   Merges semantic matches (catches intent) with lexical matches
   (catches exact terminology) into a single consensus ranking.
   │
   ▼
4. Term Overlap Reranking
   overlap_ratio = |query_terms ∩ doc_terms| / |query_terms|
   final_score = rrf_score × (1.0 + 0.5 × overlap_ratio)
   
   Boosts documents that share more vocabulary with the query.
   │
   ▼
5. Result
   Top 5 chunks returned with:
   - filename
   - page number (verified, not guessed)
   - relevance score
   - text excerpt (400 chars)
```

**Why hybrid?** Pure vector search misses exact terms. Pure BM25 misses semantic intent. RRF consensus ranking captures both, improving retrieval precision by 40-60% over either method alone.

**Example:**
```
Question: "What is the password rotation policy?"

Vector search finds: "...passwords must be changed every 90 days..."
  (semantic match, page 12)

BM25 finds: "...password rotation frequency is mandated quarterly..."
  (exact keyword match, page 8)

RRF merges both → returns page 12 and page 8 as top results
→ LLM synthesizes: "Per the security policy (page 12), passwords must be
   rotated every 90 days. Page 8 confirms this as a quarterly mandate."
```

---

## Intent Classification & Orchestration

The orchestrator routes each question to the right pipeline.

```
Question arrives → Check project assets (tables? documents? both?)
  │
  ├─ Structured data only → "structured" mode → NL-to-SQL pipeline
  ├─ Documents only       → "documents" mode → Hybrid RAG pipeline
  ├─ Both assets exist:
  │    ├─ Quantitative keywords (total, sum, revenue, count, trend)?
  │    ├─ Qualitative keywords (policy, summary, explain, according to)?
  │    │
  │    ├─ Both  → "hybrid" mode → runs SQL + RAG, synthesizes combined answer
  │    ├─ Quant → "structured" mode
  │    ├─ Qual  → "documents" mode
  │    └─ Ambig → defaults to "hybrid"
  │
  └─ No data uploaded → "unsupported" → prompts user to upload files
```

**Conversation memory:** Last 4 turns retained and passed as context to the LLM for follow-up questions like "What about last year?" or "Break that down by region."

---

## Domain Detection

Scans column names across all workspace tables to auto-classify the business domain.

| Domain | Trigger Columns | Activates |
|--------|-----------------|-----------|
| Healthcare | encounter_id, patient_id, diagnosis, billed_amount, wait_time, length_of_stay, lab_result | Clinical KPIs, encounter-to-lab anti-inflation joins, collection rate analysis |
| Retail | order_id, product, category, net_revenue, quantity, discount, cogs | Sales funnel, AOV, MoM trends, SKU concentration |
| General | (fallback) | Generic revenue/profit/orders metrics |

**Currency auto-detection:** Scans column names for `inr`→₹, `eur`→€, `gbp`→£, default $.

---

## Dashboard & Insights ML Logic

### Anti-Inflation Join Safety

When datasets have 1-to-many relationships (e.g., one patient encounter → multiple lab results), naive joins double-count financials. The dashboard isolates encounter-level money to a CTE before joining lab data:

```sql
WITH encounter_financials AS (
  SELECT encounter_id, SUM(billed_amount) as billed
  FROM encounters GROUP BY encounter_id
)
SELECT ... FROM encounter_financials ef
LEFT JOIN lab_results lr ON ef.encounter_id = lr.encounter_id
-- billed amount counted once per encounter, not per lab test
```

### Automated Insights Engine

Algorithmic detection — no LLM involved in calculation:

| Detection | Logic | Example Output |
|-----------|-------|----------------|
| MoM trend | Compare last two months, flag >15% growth or <-5% drop | "Revenue increased 18.3% MoM" |
| Regional disparity | Top region >40% share = concentration risk | "North region holds 52% of sales" |
| Collection rate (healthcare) | Paid/Billed × 100, alert if <75% | "Collection rate at 68% — accelerate claims" |
| Wait time (healthcare) | Flag if avg wait >20 minutes | "Avg wait 24.5 min exceeds 20 min target" |
| Lab abnormality rate | % of results outside reference range | "12.3% of lab tests outside normal range" |

---

## ML Model Configuration

| Setting | Value | Why |
|---------|-------|-----|
| LLM temperature | 0.1 | Low creativity, deterministic SQL generation |
| Embedding batch size | 32 | Prevents Ollama payload limits |
| Chunk size | 250 words (~350 tokens) | Optimal for nomic-embed-text context window |
| Chunk overlap | 50 words | Prevents semantic breaks at boundaries |
| RRF constant K | 60 | Standard value, balances rank weighting |
| RRF candidate pool | 3× top_k (18 for top 5) | Wider candidate set before final cut |
| SQL row limit | 500 | Prevents runaway queries |
| DuckDB memory | 1GB | Prevents host OS starvation |
| DuckDB threads | 4 | Bounded parallelism |
| Conversation context | Last 4 turns | Follow-up question awareness |

---

## Data Privacy & Sovereignty

Everything runs locally. No external API calls anywhere in the pipeline.

| Component | Where It Runs | Data Leaves Machine? |
|-----------|--------------|---------------------|
| LLM inference (Qwen3:4b) | Local Ollama (:11434) | No |
| Embeddings (nomic-embed-text) | Local Ollama (:11434) | No |
| Vector storage (ChromaDB) | Local filesystem (`backend/data/chroma/`) | No |
| OLAP queries (DuckDB) | In-process, per-project `.duckdb` file | No |
| Metadata (PostgreSQL/SQLite) | Local | No |
| Document parsing (PyMuPDF) | In-process | No |
| Chat history | Local DB | No |

ChromaDB telemetry disabled (`anonymized_telemetry=False`). Project-scoped collections isolate data between workspaces.

---

## Testing

```bash
cd backend
pytest tests -v
```

25 tests covering: SQL guard safety (8 tests), ingestion magic-byte validation (4), dashboard math + anti-inflation (3), report generation (1), API lifecycle (2), intent routing (4), chunking (3).

---

## Future Enhancements

### 1. Voice-Based Analytics
- Client-side streaming Whisper / Web Speech API for real-time STT
- Voice-driven chart manipulation and drill-downs
- Local TTS (Kokoro/Piper) for audible executive debriefs

### 2. Multilingual Intelligence
- Support for Hindi, Kannada, Marathi alongside English
- Cross-lingual NL-to-SQL preserving numerical precision
- Localized dashboards, tooltips, and multilingual report generation

### 3. Agentic Query Planning
- Break complex questions into multi-step plans (e.g., "Compare Q3 revenue across all regions, then identify the outlier")
- Sequential DuckDB queries with intermediate result passing
- Tool-use pattern: LLM decides which tables to query, in what order, with what filters
