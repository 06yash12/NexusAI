from app.services.ingestion_service import validate_magic_bytes, clean_column_names

def test_validate_magic_bytes_pdf():
    valid_pdf = b"%PDF-1.4\n%some content"
    invalid_pdf = b"NOT A PDF FILE"
    assert validate_magic_bytes(valid_pdf, ".pdf") is True
    assert validate_magic_bytes(invalid_pdf, ".pdf") is False

def test_validate_magic_bytes_ooxml():
    zip_header = b"PK\x03\x04\x14\x00\x06\x00"
    garbage = b"RANDOM BYTES"
    assert validate_magic_bytes(zip_header, ".xlsx") is True
    assert validate_magic_bytes(zip_header, ".docx") is True
    assert validate_magic_bytes(garbage, ".xlsx") is False

def test_validate_magic_bytes_csv():
    valid_csv = b"order_id,date,amount\n1,2026-01-01,100"
    binary_data = b"\x00\x00\x01\x02\xff\xfe"
    assert validate_magic_bytes(valid_csv, ".csv") is True
    assert validate_magic_bytes(binary_data, ".csv") is False

def test_clean_column_names():
    raw_cols = ["Order ID", "Total Revenue ($)", "1st Quarter", "Category & Dept", "Order ID"]
    cleaned = clean_column_names(raw_cols)
    assert cleaned[0] == "order_id"
    assert "total_revenue" in cleaned[1]
    assert cleaned[2].startswith("col_")  # starts with digit
    assert "category" in cleaned[3]
    assert cleaned[4] == "order_id_1"  # deduplicated
