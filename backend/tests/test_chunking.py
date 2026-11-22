from app.services.document_service import DocumentService, normalize_text, tokenize_for_bm25

def test_chunk_page_text_preserves_page_and_overlap():
    words = " ".join(f"token{i}" for i in range(500))
    chunks = DocumentService.chunk_page_text(page_num=3, text=words, chunk_size=200, overlap=50)
    
    assert len(chunks) == 3
    assert all(c["page"] == 3 for c in chunks)
    
    first = chunks[0]["text"].split()
    second = chunks[1]["text"].split()
    assert first[-50:] == second[:50]

def test_normalize_text():
    raw = "  Quarterly   Financial\n\tReport   \r\n2026   "
    clean = normalize_text(raw)
    assert clean == "Quarterly Financial Report 2026"

def test_tokenize_for_bm25():
    text = "NEXUS AI: Enterprise Platform, Q1 Sales & Revenue!"
    tokens = tokenize_for_bm25(text)
    assert "nexus" in tokens
    assert "enterprise" in tokens
    assert "revenue" in tokens
    assert ":" not in tokens
