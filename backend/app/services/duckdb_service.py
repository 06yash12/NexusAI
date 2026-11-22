import re
import time
from pathlib import Path
import duckdb
from app.core.config import settings

def safe_identifier(value: str) -> str:
    # Retain alphanumeric characters and underscores
    clean = re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()
    if not clean or clean[0].isdigit():
        clean = f"dataset_{clean}"
    return clean[:48]

class DuckDBService:
    def db_path(self, project_id: str) -> Path:
        clean_project = "".join(c for c in project_id if c.isalnum() or c in ("-", "_"))
        return settings.duckdb_dir / f"{clean_project}.duckdb"

    def connect(self, project_id: str):
        path = str(self.db_path(project_id))
        con = duckdb.connect(path)
        # Apply safety resource limits
        try:
            con.execute(f"SET memory_limit = '{settings.duckdb_memory_limit}'")
            con.execute(f"SET threads = {settings.duckdb_threads}")
        except Exception:
            pass
        return con

    def list_tables(self, project_id: str) -> list[str]:
        with self.connect(project_id) as con:
            return [r[0] for r in con.execute("SHOW TABLES").fetchall()]

    def schema(self, project_id: str) -> dict[str, list[dict]]:
        result = {}
        with self.connect(project_id) as con:
            for table in self.list_tables(project_id):
                try:
                    rows = con.execute(f"DESCRIBE {self.quote(table)}").fetchall()
                    cols = []
                    for r in rows:
                        col_name = r[0]
                        col_type = r[1]
                        # Fetch a sample non-null value to enrich schema context
                        sample_val = None
                        try:
                            sample_row = con.execute(
                                f'SELECT "{col_name}" FROM {self.quote(table)} WHERE "{col_name}" IS NOT NULL LIMIT 1'
                            ).fetchone()
                            if sample_row and sample_row[0] is not None:
                                sample_val = str(sample_row[0])[:30]
                        except Exception:
                            pass
                        cols.append({
                            "name": col_name,
                            "type": col_type,
                            "sample": sample_val
                        })
                    result[table] = cols
                except Exception:
                    continue
        return result

    def execute_query(self, project_id: str, sql: str) -> dict:
        start_time = time.perf_counter()
        with self.connect(project_id) as con:
            cursor = con.execute(sql)
            columns = [d[0] for d in cursor.description] if cursor.description else []
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "execution_time_ms": elapsed_ms
        }

    def drop_table(self, project_id: str, table_name: str) -> bool:
        with self.connect(project_id) as con:
            tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
            if table_name in tables:
                con.execute(f"DROP TABLE IF EXISTS {self.quote(table_name)}")
                return True
        return False

    @staticmethod
    def quote(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

duckdb_service = DuckDBService()
