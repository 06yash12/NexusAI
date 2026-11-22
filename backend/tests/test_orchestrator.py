from app.services.orchestrator import classify_intent

def test_classify_intent_structured_only():
    # When workspace has only structured tables
    intent = classify_intent("What is the quarterly revenue?", has_structured=True, has_documents=False)
    assert intent == "structured"

def test_classify_intent_documents_only():
    # When workspace has only documents
    intent = classify_intent("Summarize company travel policy", has_structured=False, has_documents=True)
    assert intent == "documents"

def test_classify_intent_empty_workspace():
    # Workspace has neither
    intent = classify_intent("Any data available?", has_structured=False, has_documents=False)
    assert intent == "unsupported"

def test_classify_intent_both_assets():
    # Workspace has both structured data and document reports
    # Quantitative question -> structured
    quant = classify_intent("Which 5 products generated the highest sales?", has_structured=True, has_documents=True)
    assert quant == "structured"

    # Qualitative question -> documents
    qual = classify_intent("What are the strategic risk factors mentioned in the audit report?", has_structured=True, has_documents=True)
    assert qual == "documents"

    # Hybrid question -> hybrid
    hybrid = classify_intent("Compare the total revenue against the strategy targets in the executive report", has_structured=True, has_documents=True)
    assert hybrid == "hybrid"
