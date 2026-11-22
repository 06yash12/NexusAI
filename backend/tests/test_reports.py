import io
from fastapi.testclient import TestClient
from app.main import app
from app.services.report_service import report_service

client = TestClient(app)

def test_report_service_excel_generation():
    # Create project
    proj_res = client.post("/api/projects", json={"name": "Report Test Proj", "description": ""})
    assert proj_res.status_code == 200
    project_id = proj_res.json()["id"]

    # Ingest structured CSV
    csv_content = (
        "Order_ID,Order_Date,Region,Category,Product,Quantity,Net_Revenue_INR,Profit_INR,Order_Status\n"
        "ORD001,2025-01-15,North,Electronics,Laptop,2,100000,25000,Delivered\n"
        "ORD002,2025-02-10,South,Furniture,Chair,4,20000,5000,Delivered\n"
        "ORD003,2026-01-12,East,Electronics,Phone,1,50000,12000,Delivered\n"
        "ORD004,2026-03-05,West,Office Supplies,Pen,10,1000,200,Cancelled\n"
    ).encode("utf-8")

    upload_res = client.post(
        f"/api/projects/{project_id}/files",
        files={"file": ("test_sales.csv", io.BytesIO(csv_content), "text/csv")}
    )
    assert upload_res.status_code == 200

    # Test Excel generation
    excel_bytes = report_service.generate_excel(project_id)
    assert len(excel_bytes) > 1000
    assert excel_bytes.startswith(b"PK")  # Zip file signature for .xlsx

    # Test PDF generation
    pdf_bytes = report_service.generate_pdf(project_id)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")

    # Test Report Download API endpoints
    res_excel = client.get(f"/api/projects/{project_id}/reports/excel")
    assert res_excel.status_code == 200
    assert res_excel.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "attachment; filename=" in res_excel.headers["content-disposition"]

    res_pdf = client.get(f"/api/projects/{project_id}/reports/pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in res_pdf.headers["content-disposition"]

    # Test Original File Download API
    dataset_id = upload_res.json()["id"]
    res_dl = client.get(f"/api/projects/{project_id}/datasets/{dataset_id}/download")
    assert res_dl.status_code == 200
    assert b"ORD001" in res_dl.content

    # Clean up project
    client.delete(f"/api/projects/{project_id}")
