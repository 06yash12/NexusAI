import io
import re
import logging
from pathlib import Path
from typing import Any
import pymupdf  # type: ignore[import-untyped]
from docx import Document  # type: ignore[import-untyped]
from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]
import chromadb  # type: ignore[import-untyped]
from chromadb.config import Settings as ChromaSettings  # type: ignore[import-untyped]

try:
    from app.core.config import settings
    from app.services.ollama_service import ollama_service
except ImportError:
    from ..core.config import settings
    from .ollama_service import ollama_service

logger = logging.getLogger("nexus.document_service")

def normalize_text(text: str) -> str:
    """Normalize whitespace and control characters."""
    if not text:
        return ""
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

def tokenize_for_bm25(text: str) -> list[str]:
    """Lowercase tokenization suitable for lexical matching."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return [token for token in cleaned.split() if len(token) > 1]

class DocumentService:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=str(settings.chroma_dir),
            settings=ChromaSettings(anonymized_telemetry=False)
        )

    def collection(self, project_id: str):
        clean_project = "".join(c for c in project_id.lower() if c.isalnum())[:40]
        name = f"nexus_{clean_project}"
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )

    def extract_with_pages(self, path: Path, suffix: str) -> list[dict[str, Any]]:
        """
        Extract text organized by pages or structured sections.
        Returns a list of dicts: [{"page": int, "text": str}]
        """
        pages_data = []
        if suffix == ".pdf":
            try:
                with pymupdf.open(path) as doc:
                    for idx, page in enumerate(doc):
                        page_num = idx + 1
                        page_text = page.get_text("text").strip()
                        
                        # Handle scanned or empty pages
                        if not page_text:
                            # Attempt OCR if pytesseract and Pillow are available
                            try:
                                import importlib
                                pytesseract = importlib.import_module("pytesseract")
                                pil_image = importlib.import_module("PIL.Image")
                                pix = page.get_pixmap()
                                img = pil_image.open(io.BytesIO(pix.tobytes("png")))
                                ocr_text = pytesseract.image_to_string(img).strip()
                                if ocr_text:
                                    page_text = f"[OCR Extracted] {ocr_text}"
                            except Exception as ocr_err:
                                logger.debug("OCR processing skipped for page %d: %s", page_num, ocr_err)
                        
                        if page_text:
                            pages_data.append({"page": page_num, "text": page_text})
                    
                    if not pages_data:
                        # If completely empty or image-only without OCR
                        logger.warning("No readable text found in PDF: %s", path.name)
            except Exception as exc:
                raise ValueError(f"Failed to extract PDF contents: {exc}") from exc

        elif suffix == ".docx":
            try:
                doc = Document(path)
                paragraphs = []
                for p in doc.paragraphs:
                    t = p.text.strip()
                    if t:
                        paragraphs.append(t)
                
                # Extract structured table contents
                for t_idx, table in enumerate(doc.tables, 1):
                    table_rows = []
                    for row in table.rows:
                        row_vals = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                        if row_vals:
                            table_rows.append(" | ".join(row_vals))
                    if table_rows:
                        paragraphs.append(f"[Table {t_idx}]\n" + "\n".join(table_rows))
                
                # Group docx into logical pages (approx 500 words per logical page)
                accumulated = []
                current_word_count = 0
                page_idx = 1
                
                for p in paragraphs:
                    words = p.split()
                    accumulated.append(p)
                    current_word_count += len(words)
                    if current_word_count >= 500:
                        pages_data.append({"page": page_idx, "text": "\n".join(accumulated)})
                        accumulated = []
                        current_word_count = 0
                        page_idx += 1
                        
                if accumulated:
                    pages_data.append({"page": page_idx, "text": "\n".join(accumulated)})
            except Exception as exc:
                raise ValueError(f"Failed to extract DOCX contents: {exc}") from exc
        else:
            raise ValueError(f"Unsupported document format: {suffix}")

        return pages_data

    @staticmethod
    def chunk_page_text(page_num: int, text: str, chunk_size: int = 250, overlap: int = 50) -> list[dict[str, Any]]:
        """
        Splits page text into overlapping word chunks while maintaining page number reference.
        chunk_size: ~250 words (~350 tokens, optimal for nomic-embed-text)
        """
        words = text.split()
        if not words:
            return []
        
        chunks = []
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_str = " ".join(words[start:end])
            chunks.append({
                "page": page_num,
                "text": chunk_str
            })
            if end == len(words):
                break
            start = end - overlap
        return chunks

    def index_document(self, project_id: str, document_id: str, filename: str, pages_data: list[dict[str, Any]]) -> int:
        """
        Extracts, chunks, embeds and persists document chunks in ChromaDB.
        """
        all_chunks = []
        for p in pages_data:
            p_num = p["page"]
            raw_text = p["text"]
            chunks = self.chunk_page_text(p_num, raw_text)
            all_chunks.extend(chunks)

        if not all_chunks:
            return 0

        # Batch embed chunks with nomic-embed-text
        chunk_texts = [c["text"] for c in all_chunks]
        
        # Batching embeddings to prevent payload size limits
        batch_size = 32
        embeddings = []
        for i in range(0, len(chunk_texts), batch_size):
            batch = chunk_texts[i:i + batch_size]
            emb_batch = ollama_service.embed(batch)
            embeddings.extend(emb_batch)

        ids = [f"{document_id}_{i}" for i in range(len(all_chunks))]
        metadatas = [
            {
                "document_id": document_id,
                "filename": filename,
                "page": all_chunks[i]["page"],
                "chunk": i
            }
            for i in range(len(all_chunks))
        ]

        collection = self.collection(project_id)
        collection.add(
            ids=ids,
            documents=chunk_texts,
            embeddings=embeddings,
            metadatas=metadatas
        )
        return len(all_chunks)

    def delete_document(self, project_id: str, document_id: str) -> None:
        """Removes all indexed chunks associated with document_id."""
        try:
            collection = self.collection(project_id)
            collection.delete(where={"document_id": document_id})
        except Exception as exc:
            logger.warning("Could not delete document chunks for %s: %s", document_id, exc)

    def hybrid_search(self, project_id: str, question: str, top_k: int = 6) -> list[dict[str, Any]]:
        """
        Hybrid retrieval combining:
        1. Semantic Vector Search (ChromaDB cosine similarity)
        2. Lexical Keyword Retrieval (BM25Okapi)
        3. Reciprocal Rank Fusion (RRF)
        4. Re-ranking by term overlap and score density
        """
        collection = self.collection(project_id)
        total_count = collection.count()
        if total_count == 0:
            return []

        # 1. Semantic vector retrieval
        query_embedding = ollama_service.embed([question])[0]
        n_query = min(top_k * 3, total_count)
        vector_res = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_query,
            include=["documents", "metadatas", "distances"]
        )
        vector_docs = vector_res.get("documents", [[]])[0]
        vector_meta = vector_res.get("metadatas", [[]])[0]
        vector_ids = vector_res.get("ids", [[]])[0]
        vector_distances = vector_res.get("distances", [[]])[0]

        # 2. Lexical BM25 retrieval over project corpus
        all_data = collection.get(include=["documents", "metadatas"])
        corpus_docs = all_data.get("documents", [])
        corpus_metas = all_data.get("metadatas", [])
        corpus_ids = all_data.get("ids", [])

        tokenized_corpus = [tokenize_for_bm25(doc) for doc in corpus_docs]
        query_tokens = tokenize_for_bm25(question)

        bm25_scores = {}
        if query_tokens and any(tokenized_corpus):
            bm25 = BM25Okapi(tokenized_corpus)
            doc_scores = bm25.get_scores(query_tokens)
            for idx, score in enumerate(doc_scores):
                if score > 0:
                    bm25_scores[corpus_ids[idx]] = float(score)

        lexical_sorted = sorted(bm25_scores.keys(), key=lambda x: bm25_scores[x], reverse=True)[:n_query]

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF formula: Score(d) = sum(1 / (k + rank))
        K = 60.0
        rrf_scores: dict[str, float] = {}
        doc_registry: dict[str, dict[str, Any]] = {}

        # Vector rankings
        for rank, (doc_id, doc, meta) in enumerate(zip(vector_ids, vector_docs, vector_meta), start=1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (K + rank))
            doc_registry[doc_id] = {"text": doc, "metadata": meta}

        # BM25 rankings
        for rank, doc_id in enumerate(lexical_sorted, start=1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (K + rank))
            if doc_id not in doc_registry:
                idx = corpus_ids.index(doc_id)
                doc_registry[doc_id] = {"text": corpus_docs[idx], "metadata": corpus_metas[idx]}

        if not rrf_scores:
            return []

        # 4. Reranking step: Combine RRF with query term coverage
        final_scores = []
        query_set = set(query_tokens)
        for doc_id, rrf_score in rrf_scores.items():
            entry = doc_registry[doc_id]
            doc_text = entry["text"]
            # Calculate term overlap bonus
            doc_tokens = set(tokenize_for_bm25(doc_text))
            overlap_ratio = len(query_set & doc_tokens) / max(len(query_set), 1)
            
            # Composite rerank score
            rerank_score = rrf_score * (1.0 + 0.5 * overlap_ratio)
            final_scores.append((doc_id, rerank_score, entry))

        final_scores.sort(key=lambda x: x[1], reverse=True)
        top_results = final_scores[:top_k]

        return [
            {
                "text": item[2]["text"],
                "metadata": item[2]["metadata"],
                "score": round(item[1], 4),
                "page": item[2]["metadata"].get("page", 1),
                "filename": item[2]["metadata"].get("filename", "document"),
                "chunk": item[2]["metadata"].get("chunk", 0)
            }
            for item in top_results
        ]

document_service = DocumentService()
