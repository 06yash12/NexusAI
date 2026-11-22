import uuid
import re
import json
from pathlib import Path
import pandas as pd
from fastapi import UploadFile, HTTPException
from app.core.config import settings
from app.services.duckdb_service import duckdb_service, safe_identifier
from app.services.document_service import document_service

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".pdf", ".docx"}

def validate_magic_bytes(content: bytes, suffix: str) -> bool:
    """Validate header/magic bytes to ensure file content matches extension."""
    if suffix == ".pdf":
        return content.startswith(b"%PDF-")
    if suffix in {".xlsx", ".docx"}:
        # ZIP file signature used by OOXML documents (.xlsx, .docx)
        return content.startswith(b"PK\x03\x04") or content.startswith(b"PK\x05\x06")
    if suffix == ".csv":
        # CSV should be valid UTF-8/Latin-1 text with comma, semicolon, tab or newline
        try:
            sample = content[:4096].decode("utf-8", errors="replace")
            # Must not be mostly null bytes or binary
            if "\x00" in sample:
                return False
            return True
        except Exception:
            return False
    return False

def clean_column_names(columns: list) -> list[str]:
    """Ensure column names are clean and valid for DuckDB SQL without confusing quotes."""
    cleaned = []
    seen = {}
    for col in columns:
        c = str(col).strip()
        # Replace problematic punctuation with underscore
        c = re.sub(r"[^\w\s]", "_", c)
        c = re.sub(r"\s+", "_", c)
        c = c.lower().strip("_")
        if not c or c[0].isdigit():
            c = f"col_{c}"
        if c in seen:
            seen[c] += 1
            c = f"{c}_{seen[c]}"
        else:
            seen[c] = 0
        cleaned.append(c)
    return cleaned

class IngestionService:
    async def ingest(self, project_id: str, upload: UploadFile) -> dict:
        filename = Path(upload.filename or "upload").name
        suffix = Path(filename).suffix.lower()
        
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported format '{suffix}'. Allowed formats: CSV, XLSX, PDF, DOCX."
            )

        content = await upload.read()
        file_size = len(content)

        if file_size == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty (0 bytes).")
        
        max_bytes = settings.max_upload_mb * 1024 * 1024
        if file_size > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum allowed size of {settings.max_upload_mb} MB."
            )

        # Magic byte verification
        if not validate_magic_bytes(content, suffix):
            raise HTTPException(
                status_code=400,
                detail=f"File header mismatch: The file content does not match the '{suffix}' format. It may be corrupted or disguised."
            )

        dataset_id = str(uuid.uuid4())
        project_dir = settings.upload_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Safe storage path
        destination = project_dir / f"{dataset_id}{suffix}"
        destination.write_bytes(content)

        # 1. Tabular Ingestion (CSV / XLSX)
        if suffix in {".csv", ".xlsx"}:
            try:
                if suffix == ".csv":
                    # Attempt reading with various encodings
                    try:
                        frame = pd.read_csv(destination, encoding="utf-8")
                    except UnicodeDecodeError:
                        frame = pd.read_csv(destination, encoding="latin1")
                else:
                    frame = pd.read_excel(destination)
            except Exception as exc:
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail=f"Corrupted or invalid spreadsheet: {exc}") from exc

            if frame.empty or len(frame.columns) == 0:
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail="The dataset has no rows or columns.")

            # Sanitize column names for seamless SQL querying
            frame.columns = clean_column_names(frame.columns)
            
            # Clean base name and append short dataset uuid to prevent table name collisions
            base_name = safe_identifier(Path(filename).stem)
            table_name = f"{base_name}_{dataset_id.replace('-', '')[:8]}"

            try:
                with duckdb_service.connect(project_id) as con:
                    con.register("incoming_data_stream", frame)
                    con.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM incoming_data_stream')
                    con.unregister("incoming_data_stream")
            except Exception as exc:
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=500, detail=f"Failed to register table in DuckDB: {exc}") from exc

            metadata = {
                "columns": list(frame.columns),
                "shape": frame.shape,
                "original_filename": filename
            }

            return {
                "id": dataset_id,
                "filename": filename,
                "original_filename": filename,
                "file_path": str(destination),
                "file_type": suffix[1:],
                "file_size": file_size,
                "mime_type": upload.content_type or "application/octet-stream",
                "table_name": table_name,
                "row_count": int(len(frame)),
                "status": "processed",
                "metadata_json": json.dumps(metadata)
            }

        # 2. Document Ingestion (PDF / DOCX)
        try:
            pages_data = document_service.extract_with_pages(destination, suffix)
            if not pages_data:
                # Document has no extractable text
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=400,
                    detail="No readable text or tables could be extracted from this document."
                )

            chunk_count = document_service.index_document(project_id, dataset_id, filename, pages_data)
        except HTTPException:
            raise
        except Exception as exc:
            destination.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail=f"Document indexing failed: {exc}") from exc

        metadata = {
            "page_count": len(pages_data),
            "chunk_count": chunk_count,
            "original_filename": filename
        }

        return {
            "id": dataset_id,
            "filename": filename,
            "original_filename": filename,
            "file_path": str(destination),
            "file_type": suffix[1:],
            "file_size": file_size,
            "mime_type": upload.content_type or "application/octet-stream",
            "table_name": None,
            "row_count": chunk_count,
            "status": "indexed",
            "metadata_json": json.dumps(metadata)
        }

ingestion_service = IngestionService()
