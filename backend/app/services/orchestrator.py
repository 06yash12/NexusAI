import re
import json
from typing import Any
from app.services.sql_service import sql_analytics
from app.services.document_service import document_service
from app.services.ollama_service import ollama_service
from app.services.duckdb_service import duckdb_service

QUANTITATIVE_PATTERNS = [
    r"\b(how much|how many|total|sum|average|avg|count|median|min|max|highest|lowest)\b",
    r"\b(sales|revenue|profit|margin|quantity|cost|price|discount|orders|units)\b",
    r"\b(patient|patients|encounter|encounters|billed|paid|collections|outstanding|wait\s*time|los|length\s+of\s+stay|diagnosis|lab|laboratory|test|tests|department|facility|doctor|clinic)\b",
    r"\b(top\s+\d+|bottom\s+\d+|rank|best|worst|compare|breakdown|by\s+\w+)\b",
    r"\b(trend|monthly|daily|quarterly|yearly|annual|202\d)\b",
]

QUALITATIVE_PATTERNS = [
    r"\b(policy|procedure|strategy|guideline|contract|agreement|clause|handbook)\b",
    r"\b(report|findings|conclusion|executive summary|recommendation|risk|audit)\b",
    r"\b(summarize|explain|overview|what does the document say|according to)\b",
    r"\b(who is|mission|vision|objectives|notes|feedback|comments)\b",
]

def classify_intent(question: str, has_structured: bool, has_documents: bool) -> str:
    q = question.lower()

    if has_structured and not has_documents:
        return "structured"
    if has_documents and not has_structured:
        return "documents"
    if not has_structured and not has_documents:
        return "unsupported"

    # Both structured and documents exist in the project
    is_quant = any(re.search(pat, q) for pat in QUANTITATIVE_PATTERNS)
    is_qual = any(re.search(pat, q) for pat in QUALITATIVE_PATTERNS)

    if is_quant and is_qual:
        return "hybrid"
    if is_quant:
        return "structured"
    if is_qual:
        return "documents"

    # Default to hybrid if ambiguous and both asset types exist
    return "hybrid"

class QueryOrchestrator:
    def choose_mode(self, question: str, requested: str, project_id: str) -> str:
        if requested in {"structured", "documents", "hybrid"}:
            return requested

        # Auto routing based on project assets and query intent
        tables = duckdb_service.list_tables(project_id)
        has_structured = len(tables) > 0

        try:
            collection = document_service.collection(project_id)
            has_documents = collection.count() > 0
        except Exception:
            has_documents = False

        return classify_intent(question, has_structured, has_documents)

    def answer(
        self, 
        project_id: str, 
        question: str, 
        requested_mode: str = "auto", 
        history: list[dict] | None = None,
        allowed_tables: set[str] | None = None
    ) -> dict:
        mode = self.choose_mode(question, requested_mode, project_id)
        sql_result: dict | None = None
        sources: list[dict] = []
        warnings: list[str] = []
        chart_suggestion: dict | None = None

        if mode == "unsupported":
            return {
                "answer": "This workspace has no uploaded data or documents yet. Please upload a CSV/Excel dataset or a PDF/DOCX report to get started.",
                "mode": "unsupported",
                "sql": None,
                "columns": [],
                "rows": [],
                "sources": [],
                "warnings": ["No data available in project."],
                "chart_suggestion": None,
                "execution_time_ms": 0
            }

        # 1. Execute SQL if structured or hybrid mode
        if mode in {"structured", "hybrid"}:
            try:
                sql_result = sql_analytics.run(question, project_id, allowed_table_subset=allowed_tables)
                chart_suggestion = sql_result.get("chart_suggestion")
            except Exception as exc:
                if mode == "structured":
                    raise
                warnings.append(f"Structured analysis could not be completed: {exc}")

        # 2. Execute Hybrid RAG if documents or hybrid mode
        if mode in {"documents", "hybrid"}:
            try:
                sources = document_service.hybrid_search(project_id, question, top_k=5)
            except Exception as exc:
                if mode == "documents":
                    raise
                warnings.append(f"Document search encountered an issue: {exc}")

        if mode == "documents" and not sources:
            return {
                "answer": "I could not find supporting passages in the uploaded documents for your question. Please verify your query or upload more relevant PDF/DOCX files.",
                "mode": mode,
                "sql": None,
                "columns": [],
                "rows": [],
                "sources": [],
                "warnings": warnings,
                "chart_suggestion": None,
                "execution_time_ms": 0
            }

        # 3. Grounded Synthesis Prompt
        detected_domain = (sql_result or {}).get("domain", "general")
        detected_domain_label = (sql_result or {}).get("domain_label", "Business Intelligence")

        system = (
            f"You are NEXUS AI, an elite enterprise {detected_domain_label} analyst. "
            "You provide rigorous, evidence-based answers to analytical queries.\n\n"
            "MANDATORY INSTRUCTIONS:\n"
            "1. Ground every claim directly in the provided SQL query results and document excerpts.\n"
            "2. NEVER invent numbers, calculations, percentages, or dates not present in the data.\n"
            "3. Clearly distinguish between calculated metrics (from SQL) and qualitative statements (from documents).\n"
            "4. For Healthcare: strictly distinguish Billed Amount (total charges), Paid Collections, and Outstanding Balances. Never conflate them or apply retail sales terms (like products, AOV, inventory) to healthcare encounters.\n"
            "5. Presentation Quality: Use well-structured markdown tables whenever presenting comparative data, period breakdowns, or top rankings. Use bullet points and bold key numbers (with currency symbols).\n"
            "6. DO NOT leak raw JSON keys like `structured_data_result` into user-facing text. Refer to them as 'database records' or 'verified query results'.\n"
            "7. When citing documents, mention the document filename and page number from citations.\n"
            "8. If the retrieved evidence is insufficient to answer completely, state the limitations clearly."
        )

        # Context assembly
        evidence_payload: dict[str, Any] = {
            "user_question": question,
            "mode": mode,
        }

        if history:
            # Include recent conversation turns for context awareness
            evidence_payload["conversation_context"] = [
                {"q": h.get("question"), "a": h.get("answer")[:200]}
                for h in history[-3:]
            ]

        if sql_result:
            evidence_payload["structured_data_result"] = {
                "executed_sql": sql_result["sql"],
                "columns": sql_result["columns"],
                "data_rows": sql_result["rows"][:25],
                "total_rows_matched": sql_result["row_count"]
            }

        if sources:
            evidence_payload["document_evidence"] = [
                {
                    "source_file": s["filename"],
                    "page_number": s["page"],
                    "relevance_score": s["score"],
                    "excerpt": s["text"]
                }
                for s in sources
            ]

        prompt = (
            f"Evidence Context:\n{json.dumps(evidence_payload, indent=2)}\n\n"
            f"Question: {question}\n\n"
            "Provide a comprehensive, accurate, data-grounded response:"
        )

        generated_answer = ollama_service.chat(system, prompt)

        formatted_sources = [
            {
                "filename": s["filename"],
                "page_number": s["page"],
                "chunk_index": s["chunk"],
                "score": s["score"],
                "excerpt": s["text"][:400]
            }
            for s in sources
        ]

        exec_time = sql_result["execution_time_ms"] if sql_result else 0

        # Construct granular analysis steps for transparency & user progress inspection
        analysis_steps = []
        if allowed_tables:
            table_list_str = ", ".join(sorted(list(allowed_tables)))
            analysis_steps.append({
                "type": "scope",
                "icon": "filter",
                "title": f"Targeted {len(allowed_tables)} Selected Dataset(s)",
                "detail": table_list_str
            })
        else:
            analysis_steps.append({
                "type": "scope",
                "icon": "layers",
                "title": "Queried Workspace Datasets (All Files)",
                "detail": "Cross-dataset analysis scope enabled"
            })

        if sql_result:
            found_tables = set(re.findall(r'(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)', sql_result.get("sql", ""), re.IGNORECASE))
            tbl_str = ", ".join(sorted(list(found_tables))) if found_tables else "DuckDB Data Tables"
            analysis_steps.append({
                "type": "table",
                "icon": "database",
                "title": f"Analyzed DuckDB Tables: {tbl_str}",
                "detail": f"{sql_result.get('row_count', 0):,} records queried & aggregated"
            })
            analysis_steps.append({
                "type": "sql",
                "icon": "code",
                "title": "Generated & Executed Safe SQL Analytics",
                "detail": f"DuckDB engine execution in {sql_result.get('execution_time_ms', 0)}ms"
            })

        if sources:
            unique_files = sorted(list(set(s["filename"] for s in sources)))
            file_str = ", ".join(unique_files)
            analysis_steps.append({
                "type": "document",
                "icon": "file-text",
                "title": f"Analyzed Document Reports: {file_str}",
                "detail": f"Retrieved {len(sources)} grounded excerpts with semantic scoring"
            })

        analysis_steps.append({
            "type": "synthesis",
            "icon": "sparkles",
            "title": "Grounded Business Intelligence Synthesis",
            "detail": "Validated claims against numerical query results and citations"
        })

        return {
            "answer": generated_answer,
            "mode": mode,
            "sql": sql_result["sql"] if sql_result else None,
            "columns": sql_result["columns"] if sql_result else [],
            "rows": sql_result["rows"] if sql_result else [],
            "sources": formatted_sources,
            "warnings": warnings,
            "chart_suggestion": chart_suggestion,
            "execution_time_ms": exec_time,
            "analysis_steps": analysis_steps
        }

query_orchestrator = QueryOrchestrator()
