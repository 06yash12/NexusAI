import pytest
from app.services.sql_service import validate_readonly_sql, UnsafeSQL, clean_sql_output

def test_select_is_allowed():
    sql = validate_readonly_sql(
        'SELECT product, SUM(revenue) AS total FROM "sales" GROUP BY product',
        {"sales"}
    )
    assert "SELECT" in sql.upper()
    assert "LIMIT" in sql.upper()

def test_unknown_table_is_rejected():
    with pytest.raises(UnsafeSQL, match="unauthorized or non-existent"):
        validate_readonly_sql("SELECT * FROM payroll", {"sales"})

def test_mutation_is_rejected():
    with pytest.raises(UnsafeSQL, match="(Only read-only SELECT queries are allowed|Prohibited SQL operation)"):
        validate_readonly_sql("DELETE FROM sales", {"sales"})

def test_drop_table_is_rejected():
    with pytest.raises(UnsafeSQL, match="(Only read-only SELECT queries are allowed|Prohibited SQL operation)"):
        validate_readonly_sql("DROP TABLE sales", {"sales"})

def test_multiple_statements_are_rejected():
    with pytest.raises(UnsafeSQL, match="Exactly one SQL query"):
        validate_readonly_sql("SELECT * FROM sales; DROP TABLE sales", {"sales"})

def test_prohibited_function_is_rejected():
    with pytest.raises(UnsafeSQL, match="Prohibited analytical function"):
        validate_readonly_sql("SELECT revenue, read_csv('secret.csv') FROM sales", {"sales"})

def test_clean_sql_output_strips_markdown():
    raw = "```sql\nSELECT product, revenue FROM sales\n```"
    cleaned = clean_sql_output(raw)
    assert cleaned == "SELECT product, revenue FROM sales"

def test_clean_sql_output_strips_commentary():
    raw = "Here is the query you requested:\nSELECT region, SUM(amount) FROM sales GROUP BY region;"
    cleaned = clean_sql_output(raw)
    assert cleaned == "SELECT region, SUM(amount) FROM sales GROUP BY region"
