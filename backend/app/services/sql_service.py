import re
import logging
import sqlglot
from sqlglot import exp
from app.core.config import settings
from app.services.ollama_service import ollama_service
from app.services.duckdb_service import duckdb_service
from app.services.domain_service import domain_service

logger = logging.getLogger("nexus.sql_service")

class UnsafeSQL(ValueError):
    pass

def clean_sql_output(raw_output: str) -> str:
    """Extract clean SQL string from LLM response, stripping markdown and chat commentary."""
    text = raw_output.strip()
    # Check for markdown code blocks ```sql ... ``` or ``` ... ```
    match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    else:
        # If the LLM included introductory text, find where SELECT begins
        select_match = re.search(r"\bSELECT\b[\s\S]*", text, re.IGNORECASE)
        if select_match:
            text = select_match.group(0).strip()
    
    # Remove trailing semicolons
    return text.rstrip(";").strip()

def validate_readonly_sql(sql: str, allowed_tables: set[str]) -> str:
    """
    Validate that the SQL query is strictly read-only, references only allowed tables,
    and append a safety limit clause.
    """
    cleaned = clean_sql_output(sql)
    if not cleaned:
        raise UnsafeSQL("The generated SQL statement was empty.")

    try:
        statements = sqlglot.parse(cleaned, read="duckdb")
    except sqlglot.errors.ParseError as exc:
        raise UnsafeSQL(f"SQL parsing error: {exc}") from exc

    if len(statements) != 1 or statements[0] is None:
        raise UnsafeSQL("Exactly one SQL query is allowed.")

    tree = statements[0]

    # Must be a SELECT or Set operation
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise UnsafeSQL("Only read-only SELECT queries are allowed.")

    # Strictly prohibit dangerous AST nodes
    forbidden_nodes = (
        exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter,
        exp.Command, exp.Copy, exp.Merge, exp.Transaction, exp.Pragma
    )
    for kind in forbidden_nodes:
        if tree.find(kind):
            raise UnsafeSQL(f"Prohibited SQL operation detected: {kind.__name__}")

    # Inspect all referenced table identifiers
    referenced_tables = {t.name.lower() for t in tree.find_all(exp.Table) if t.name}
    allowed_lower = {t.lower() for t in allowed_tables}

    if not referenced_tables:
        raise UnsafeSQL("Query must reference at least one existing dataset table.")

    unknown = referenced_tables - allowed_lower
    if unknown:
        raise UnsafeSQL(f"Query references unauthorized or non-existent tables: {', '.join(sorted(unknown))}")

    # Check for prohibited SQL functions (e.g. reading host files, executing system commands)
    prohibited_keywords = ("read_csv", "read_parquet", "scan", "system", "version", "current_setting", "readcsv", "readparquet")
    for node in tree.walk():
        # Check type name, key, and name attribute
        type_name = type(node).__name__.lower()
        key_name = str(getattr(node, "key", "") or "").lower()
        func_name = str(getattr(node, "sql_name", lambda: "")() or "").lower()
        candidate_names = (type_name, key_name, func_name)
        if any(bad in name for bad in prohibited_keywords for name in candidate_names if name):
            raise UnsafeSQL(f"Prohibited analytical function: {type_name}")

    # Enforce row limit
    bounded_query = tree.limit(settings.max_sql_rows, copy=True).sql(dialect="duckdb")
    return bounded_query

def detect_chart_recommendation(columns: list[str], rows: list[dict]) -> dict | None:
    """Detect if query results can be visualized naturally with Recharts."""
    if not rows or len(rows) < 2 or not columns:
        return None

    # Check data types of columns
    first_row = rows[0]
    numeric_cols = []
    string_or_date_cols = []

    for col in columns:
        val = first_row.get(col)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            numeric_cols.append(col)
        elif val is not None:
            string_or_date_cols.append(col)

    if not numeric_cols:
        return None

    # If there is a categorical/temporal column and 1-3 numeric metrics
    if string_or_date_cols:
        x_col = string_or_date_cols[0]
        # Check if date/month
        is_date = any(k in x_col.lower() for k in ("date", "month", "year", "day", "quarter"))
        chart_type = "line" if is_date else "bar"
        return {
            "type": chart_type,
            "x_key": x_col,
            "y_keys": numeric_cols[:3],
            "title": f"{', '.join(numeric_cols[:2])} by {x_col}"
        }

    return None

class SQLAnalytics:
    def generate_sql(
        self, 
        question: str, 
        schema: dict, 
        domain_info: dict | None = None,
        error_feedback: str | None = None
    ) -> str:
        domain = domain_info.get("domain", "general") if domain_info else "general"
        table_groups = domain_info.get("table_groups", {}) if domain_info else {}

        domain_instructions = []
        if domain == "healthcare":
            domain_instructions.append(
                "HEALTHCARE DOMAIN RULES:\n"
                "- Core Entities: Encounter_ID, Patient_ID, Encounter_Date, Department, Facility, City, Provider_ID, Diagnosis, Visit_Type, Encounter_Status.\n"
                "- Financial Measures: Billed_Amount_INR, Paid_Amount_INR, Outstanding_Amount_INR. Always distinguish billed revenue from paid collections and outstanding balances.\n"
                "- Operational Measures: Wait_Time_Minutes, Length_of_Stay_Days.\n"
                "- Laboratory Measures: Test_Name, Result_Value, Result_Flag, Demo_Reference_Low, Demo_Reference_High.\n"
                "- CRITICAL ANTI-INFLATION JOIN RULE: Encounters and Lab Results have a 1-to-many relationship (one encounter can have multiple lab tests).\n"
                "  DO NOT compute SUM(encounters.billed_amount_inr) or COUNT(encounters.encounter_id) across raw joined lab test records, as that causes duplicate rows and falsely inflates revenue!\n"
                "  To analyze encounters with lab results, pre-aggregate lab records by encounter_id in a CTE or subquery first, or compute encounter financials separately.\n"
                "- MULTI-PART DATASETS: When encounters are split into multiple parts (e.g. part_1, part_2, part_3, part_4, part_5), UNION ALL them in a CTE:\n"
                "  WITH all_encounters AS (SELECT * FROM \"part_1\" UNION ALL SELECT * FROM \"part_2\" ...)"
            )
        elif domain == "retail":
            domain_instructions.append(
                "RETAIL / SALES DOMAIN RULES:\n"
                "- Core Measures: Net_Revenue_INR, Gross_Sales_INR, Profit_INR, Quantity_Sold, Units_Sold.\n"
                "- Core Dimensions: Product_Name, Product_ID, Category, Region, City, Sales_Channel, Order_Date.\n"
                "- For inventory questions: Opening_Stock, Closing_Stock, Stock_Movement, Replenishment."
            )
        else:
            domain_instructions.append(
                "GENERAL BI RULES:\n"
                "- Discover available metrics and dimensions from the provided table schemas.\n"
                "- Do not assume retail or healthcare metrics if their columns do not exist."
            )

        # Multi-part table awareness
        multipart_notes = []
        for base, tbls in table_groups.items():
            if len(tbls) > 1:
                quoted_tbls = ", ".join([f'"{t}"' for t in tbls])
                multipart_notes.append(f'The entity "{base}" is split across {len(tbls)} chunked tables: {quoted_tbls}. Union them with UNION ALL when analyzing all data.')
        if multipart_notes:
            domain_instructions.append("MULTI-PART TABLES DETECTED:\n" + "\n".join(multipart_notes))

        domain_section = "\n\n".join(domain_instructions)

        system = (
            "You are an expert DuckDB SQL engineer for business intelligence. "
            "Write exactly ONE valid, executable DuckDB SQL query to answer the user's question.\n\n"
            "STRICT RULES:\n"
            "1. Output ONLY the raw SQL statement. Do not include markdown ticks, explanations, or quotes.\n"
            "2. Only query the tables and exact column names defined in the schema below.\n"
            "3. Always wrap table names in double quotes, e.g. \"healthcare_encounters_part_1_...\".\n"
            "4. For aggregations, use meaningful column aliases (e.g. total_billed, encounter_count, patient_count).\n"
            "5. Never use INSERT, UPDATE, DELETE, DROP, ALTER, PRAGMA, or external file readers.\n"
            "6. To aggregate monthly trends, use strftime(cast(order_date as date), '%Y-%m') or date_trunc('month', ...).\n"
            "7. Answer with accurate calculations, never inventing values.\n\n"
            f"{domain_section}"
        )

        formatted_schema = []
        for tbl, cols in schema.items():
            col_desc = []
            for c in cols:
                sample_str = f" (sample: {c['sample']})" if c.get('sample') else ""
                col_desc.append(f"  - {c['name']} ({c['type']}){sample_str}")
            formatted_schema.append(f'Table: "{tbl}"\n' + "\n".join(col_desc))

        prompt = f"Available Database Schema:\n" + "\n\n".join(formatted_schema) + f"\n\nQuestion: {question}\n"
        if error_feedback:
            prompt += f"\nPrevious attempt failed with error:\n{error_feedback}\nPlease correct the query.\n"
        prompt += "SQL Query:"

        raw_sql = ollama_service.chat(system, prompt)
        return clean_sql_output(raw_sql)

    def run(self, question: str, project_id: str, allowed_table_subset: set[str] | None = None) -> dict:
        schema = duckdb_service.schema(project_id)
        if not schema:
            raise ValueError("No structured datasets found. Please upload a CSV or Excel file first.")

        # Filter schema to user-selected tables if provided
        if allowed_table_subset:
            schema = {tbl: cols for tbl, cols in schema.items() if tbl in allowed_table_subset}
            if not schema:
                raise ValueError("None of the selected datasets contain structured tables.")

        allowed_tables = set(schema.keys())
        domain_info = domain_service.detect_domain(schema)
        max_retries = 2
        last_error = None
        current_sql = None

        for attempt in range(max_retries + 1):
            try:
                # Generate query with domain context & multi-part table discovery
                feedback = str(last_error) if last_error else None
                current_sql = self.generate_sql(question, schema, domain_info=domain_info, error_feedback=feedback)
                
                # Validate query safety with SQLGlot AST
                safe_sql = validate_readonly_sql(current_sql, allowed_tables)
                
                # Execute query in DuckDB
                exec_result = duckdb_service.execute_query(project_id, safe_sql)
                
                # Check for chart recommendation
                chart = detect_chart_recommendation(exec_result["columns"], exec_result["rows"])

                return {
                    "sql": safe_sql,
                    "columns": exec_result["columns"],
                    "rows": exec_result["rows"],
                    "row_count": exec_result["row_count"],
                    "execution_time_ms": exec_result["execution_time_ms"],
                    "chart_suggestion": chart,
                    "domain": domain_info["domain"],
                    "domain_label": domain_info["domain_label"]
                }
            except Exception as exc:
                logger.warning("SQL attempt %d failed: %s (SQL: %s)", attempt + 1, exc, current_sql)
                last_error = exc
                if attempt == max_retries:
                    raise ValueError(f"Could not construct a valid analytical query after {max_retries + 1} attempts. Error: {last_error}") from exc

sql_analytics = SQLAnalytics()
