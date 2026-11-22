import uuid
import json
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from app.core.database import get_db
from app.models import Project, Dataset, Conversation
from app.schemas import (
    ProjectCreate, ProjectOut, DatasetOut, DatasetPreviewOut,
    ChatRequest, ChatResponse, ConversationOut, DashboardOut, InsightsOut
)
from app.services.ingestion_service import ingestion_service
from app.services.duckdb_service import duckdb_service
from app.services.document_service import document_service
from app.services.orchestrator import query_orchestrator
from app.services.dashboard_service import dashboard_service
from app.services.insights_service import insights_service
from app.services.report_service import report_service

router = APIRouter()

def get_project_or_404(project_id: str, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project workspace not found.")
    return project

# --- Project Endpoints ---

@router.post("/projects", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(
        id=str(uuid.uuid4()),
        name=payload.name.strip(),
        description=payload.description.strip()
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.scalars(select(Project).order_by(Project.created_at.desc())).all()

@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    return get_project_or_404(project_id, db)

@router.delete("/projects/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = get_project_or_404(project_id, db)
    
    # Clean up local DuckDB file
    db_file = duckdb_service.db_path(project_id)
    if db_file.exists():
        try:
            db_file.unlink(missing_ok=True)
        except Exception:
            pass

    # Clean up Chroma collection
    try:
        col = document_service.collection(project_id)
        document_service.client.delete_collection(col.name)
    except Exception:
        pass

    db.delete(project)
    db.commit()
    return {"status": "deleted", "project_id": project_id}

# --- File Ingestion & Datasets ---

@router.post("/projects/{project_id}/files", response_model=DatasetOut)
async def upload_file(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    get_project_or_404(project_id, db)
    result = await ingestion_service.ingest(project_id, file)
    dataset = Dataset(
        id=result["id"],
        project_id=project_id,
        filename=result["filename"],
        original_filename=result["original_filename"],
        file_path=result["file_path"],
        file_type=result["file_type"],
        file_size=result["file_size"],
        mime_type=result["mime_type"],
        table_name=result["table_name"],
        row_count=result["row_count"],
        status=result["status"],
        metadata_json=result["metadata_json"]
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset

@router.get("/projects/{project_id}/datasets", response_model=list[DatasetOut])
def list_datasets(project_id: str, db: Session = Depends(get_db)):
    get_project_or_404(project_id, db)
    return db.scalars(
        select(Dataset).where(Dataset.project_id == project_id).order_by(Dataset.created_at.desc())
    ).all()

@router.delete("/projects/{project_id}/datasets/{dataset_id}")
def delete_dataset(project_id: str, dataset_id: str, db: Session = Depends(get_db)):
    get_project_or_404(project_id, db)
    dataset = db.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.project_id == project_id))
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    # Drop DuckDB table if structured
    if dataset.table_name:
        duckdb_service.drop_table(project_id, dataset.table_name)
    else:
        # Remove document chunks from Chroma
        document_service.delete_document(project_id, dataset_id)

    # Delete local file
    if dataset.file_path and Path(dataset.file_path).exists():
        try:
            Path(dataset.file_path).unlink(missing_ok=True)
        except Exception:
            pass

    db.delete(dataset)
    db.commit()
    return {"status": "deleted", "dataset_id": dataset_id}

@router.get("/projects/{project_id}/datasets/{dataset_id}/preview", response_model=DatasetPreviewOut)
def preview_dataset(
    project_id: str,
    dataset_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    get_project_or_404(project_id, db)
    dataset = db.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.project_id == project_id))
    if not dataset or not dataset.table_name:
        raise HTTPException(status_code=404, detail="Structured tabular dataset not found.")

    res = duckdb_service.execute_query(
        project_id,
        f'SELECT * FROM {duckdb_service.quote(dataset.table_name)} LIMIT {limit}'
    )
    return {
        "columns": res["columns"],
        "rows": res["rows"],
        "total_rows": dataset.row_count,
        "table_name": dataset.table_name
    }

# --- Business Intelligence Dashboard & Insights ---

@router.get("/projects/{project_id}/dashboard", response_model=DashboardOut)
def get_dashboard(
    project_id: str,
    table: str | None = None,
    year: int | None = None,
    region: str | None = None,
    category: str | None = None,
    department: str | None = None,
    facility: str | None = None,
    city: str | None = None,
    visit_type: str | None = None,
    db: Session = Depends(get_db)
):
    get_project_or_404(project_id, db)
    datasets = db.scalars(select(Dataset).where(Dataset.project_id == project_id)).all()
    dash_data = dashboard_service.compute_dashboard(
        project_id,
        table_filter=table,
        year_filter=year,
        region_filter=region,
        category_filter=category,
        department_filter=department,
        facility_filter=facility,
        city_filter=city,
        visit_type_filter=visit_type
    )
    
    return {
        "dataset_count": len(datasets),
        "structured_dataset_count": sum(1 for d in datasets if d.table_name),
        "document_count": sum(1 for d in datasets if not d.table_name),
        "total_rows": sum(d.row_count for d in datasets if d.table_name),
        "tables": dash_data["tables"],
        "domain": dash_data.get("domain", "general"),
        "domain_label": dash_data.get("domain_label", "General Business Intelligence"),
        "kpis": dash_data["kpis"],
        "charts": dash_data.get("charts", []),
        "monthly_sales": dash_data["monthly_sales"],
        "yearly_comparison": dash_data.get("yearly_comparison", []),
        "regional_sales": dash_data["regional_sales"],
        "category_sales": dash_data["category_sales"],
        "top_products": dash_data["top_products"],
        "available_years": dash_data.get("available_years", []),
        "selected_year": dash_data.get("selected_year"),
        "currency_symbol": dash_data.get("currency_symbol", "$"),
        "column_mapping": dash_data.get("column_mapping", {}),
        "unavailable_explanations": dash_data.get("unavailable_explanations", {}),
        "data_freshness": dash_data["data_freshness"],
        "source_datasets": dash_data["source_datasets"],
        "available_dimensions": dash_data.get("available_dimensions", {})
    }

@router.get("/projects/{project_id}/insights", response_model=InsightsOut)
def get_insights(project_id: str, db: Session = Depends(get_db)):
    get_project_or_404(project_id, db)
    return insights_service.generate_insights(project_id)

# --- Chat & Conversations ---

@router.post("/projects/{project_id}/chat", response_model=ChatResponse)
def chat(project_id: str, payload: ChatRequest, db: Session = Depends(get_db)):
    get_project_or_404(project_id, db)
    
    # Retrieve recent conversation turns for context-awareness
    recent_convs = db.scalars(
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.created_at.desc())
        .limit(4)
    ).all()
    history = [{"question": c.question, "answer": c.answer} for c in reversed(recent_convs)]

    # Determine table subset if user selected specific datasets
    allowed_tables = None
    if payload.selected_dataset_ids:
        datasets = db.scalars(
            select(Dataset).where(
                Dataset.project_id == project_id,
                Dataset.id.in_(payload.selected_dataset_ids)
            )
        ).all()
        allowed_tables = {d.table_name for d in datasets if d.table_name}

    try:
        result = query_orchestrator.answer(
            project_id=project_id,
            question=payload.question,
            requested_mode=payload.mode,
            history=history,
            allowed_tables=allowed_tables
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Query orchestration failed: {exc}") from exc

    # Persist conversation
    sources_serialized = json.dumps(result.get("sources", []))
    conv = Conversation(
        id=str(uuid.uuid4()),
        project_id=project_id,
        question=payload.question,
        answer=result["answer"],
        mode=result["mode"],
        sql_query=result.get("sql"),
        execution_time_ms=result.get("execution_time_ms", 0),
        sources_json=sources_serialized
    )
    db.add(conv)
    db.commit()

    return result

@router.get("/projects/{project_id}/conversations", response_model=list[ConversationOut])
def get_conversations(project_id: str, db: Session = Depends(get_db)):
    get_project_or_404(project_id, db)
    convs = db.scalars(
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.created_at.asc())
    ).all()
    
    output = []
    for c in convs:
        sources_list = []
        if c.sources_json:
            try:
                sources_list = json.loads(c.sources_json)
            except Exception:
                pass
        output.append({
            "id": c.id,
            "project_id": c.project_id,
            "question": c.question,
            "answer": c.answer,
            "mode": c.mode,
            "sql_query": c.sql_query,
            "execution_time_ms": c.execution_time_ms,
            "sources": sources_list,
            "created_at": c.created_at
        })
    return output

@router.delete("/projects/{project_id}/conversations")
def clear_conversations(project_id: str, db: Session = Depends(get_db)):
    get_project_or_404(project_id, db)
    db.execute(delete(Conversation).where(Conversation.project_id == project_id))
    db.commit()
    return {"status": "cleared", "project_id": project_id}

# --- File Download ---

@router.get("/projects/{project_id}/datasets/{dataset_id}/download")
def download_dataset(project_id: str, dataset_id: str, db: Session = Depends(get_db)):
    """Download the original uploaded file for a dataset."""
    get_project_or_404(project_id, db)
    dataset = db.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.project_id == project_id))
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    file_path = Path(dataset.file_path) if dataset.file_path else None
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Original file not found on disk.")
    return FileResponse(
        path=str(file_path),
        filename=dataset.original_filename or dataset.filename,
        media_type="application/octet-stream"
    )

# --- Report Generation ---

@router.get("/projects/{project_id}/reports/excel")
def download_excel_report(
    project_id: str,
    report_type: str = Query(default="full"),
    db: Session = Depends(get_db)
):
    """Generate and download a comprehensive Excel business intelligence report."""
    get_project_or_404(project_id, db)
    try:
        excel_bytes = report_service.generate_excel(project_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel report generation failed: {exc}") from exc

    filename = f"nexus_report_{project_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/projects/{project_id}/reports/pdf")
def download_pdf_report(
    project_id: str,
    report_type: str = Query(default="full"),
    db: Session = Depends(get_db)
):
    """Generate and download a comprehensive PDF business intelligence report."""
    get_project_or_404(project_id, db)
    try:
        pdf_bytes = report_service.generate_pdf(project_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF report generation failed: {exc}") from exc

    filename = f"nexus_report_{project_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
