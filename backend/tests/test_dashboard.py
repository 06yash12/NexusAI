import uuid
from app.services.duckdb_service import duckdb_service
from app.services.dashboard_service import dashboard_service

def test_dashboard_kpis_and_aggregations(tmp_path):
    test_project = f"test_{uuid.uuid4().hex[:8]}"
    
    # Insert sample retail sales dataset into project DuckDB
    with duckdb_service.connect(test_project) as con:
        con.execute("""
            CREATE TABLE "retail_sales_sample" (
                order_id INTEGER,
                order_date VARCHAR,
                product VARCHAR,
                category VARCHAR,
                quantity INTEGER,
                unit_price DOUBLE,
                discount DOUBLE,
                region VARCHAR,
                customer VARCHAR
            )
        """)
        con.execute("""
            INSERT INTO "retail_sales_sample" VALUES
            (1001, '2026-01-03', 'Wireless Mouse', 'Accessories', 3, 799.0, 0.0, 'South', 'Customer A'),
            (1002, '2026-01-04', 'Keyboard', 'Accessories', 2, 1499.0, 100.0, 'West', 'Customer B'),
            (1003, '2026-01-05', 'Monitor', 'Electronics', 1, 12999.0, 500.0, 'South', 'Customer C')
        """)

    try:
        dash = dashboard_service.compute_dashboard(test_project)
        
        # Verify KPIs
        kpi_map = {k["id"]: k["value"] for k in dash["kpis"]}
        assert "revenue" in kpi_map
        # Revenue = (3*799 - 0) + (2*1499 - 100) + (1*12999 - 500) = 2397 + 2898 + 12499 = 17794.0
        assert kpi_map["revenue"] == 17794.0
        assert kpi_map["orders"] == 3
        assert kpi_map["quantity"] == 6
        assert kpi_map["aov"] == round(17794.0 / 3, 2)

        # Verify dimensions
        assert len(dash["regional_sales"]) >= 2
        assert len(dash["top_products"]) >= 3
        assert len(dash["category_sales"]) >= 2
    finally:
        # Cleanup
        db_path = duckdb_service.db_path(test_project)
        if db_path.exists():
            db_path.unlink(missing_ok=True)

def test_dashboard_with_inr_and_status_filtering():
    test_project = f"test_{uuid.uuid4().hex[:8]}"
    
    with duckdb_service.connect(test_project) as con:
        con.execute("""
            CREATE TABLE "sales_with_inr" (
                Order_ID VARCHAR,
                Order_Date VARCHAR,
                Year INTEGER,
                Product VARCHAR,
                Category VARCHAR,
                Quantity INTEGER,
                Net_Revenue_INR DOUBLE,
                Profit_INR DOUBLE,
                Region VARCHAR,
                Order_Status VARCHAR
            )
        """)
        con.execute("""
            INSERT INTO "sales_with_inr" VALUES
            ('O1', '2025-01-10', 2025, 'Standing Desk', 'Furniture', 2, 20000.0, 5000.0, 'North', 'Delivered'),
            ('O2', '2025-02-15', 2025, 'Webcam', 'Electronics', 4, 12000.0, 3000.0, 'South', 'Delivered'),
            ('O3', '2026-03-20', 2026, 'Standing Desk', 'Furniture', 1, 10000.0, 2500.0, 'North', 'Delivered'),
            ('O4', '2026-04-25', 2026, 'Laser Printer', 'Office', 1, 15000.0, 4000.0, 'East', 'Returned'),
            ('O5', '2026-05-30', 2026, 'Monitor', 'Electronics', 5, 50000.0, 12000.0, 'West', 'Cancelled')
        """)

    try:
        dash = dashboard_service.compute_dashboard(test_project)
        kpi_map = {k["id"]: k["value"] for k in dash["kpis"]}
        
        # Cancelled order O5 (50,000 rev, 12,000 profit) MUST be excluded!
        # Completed revenue = O1 (20,000) + O2 (12,000) + O3 (10,000) + O4 (15,000) = 57,000.0
        assert kpi_map["revenue"] == 57000.0
        assert kpi_map["orders"] == 4
        assert kpi_map["profit"] == 14500.0
        assert dash["currency_symbol"] == "₹"
        assert 2025 in dash["available_years"]
        assert 2026 in dash["available_years"]
        
        # Test 2025 filter
        dash_2025 = dashboard_service.compute_dashboard(test_project, year_filter=2025)
        kpi_2025 = {k["id"]: k["value"] for k in dash_2025["kpis"]}
        assert kpi_2025["revenue"] == 32000.0
        assert kpi_2025["orders"] == 2
        
        # Test 2026 filter (O3 + O4, O5 cancelled)
        dash_2026 = dashboard_service.compute_dashboard(test_project, year_filter=2026)
        kpi_2026 = {k["id"]: k["value"] for k in dash_2026["kpis"]}
        assert kpi_2026["revenue"] == 25000.0
        assert kpi_2026["orders"] == 2
    finally:
        db_path = duckdb_service.db_path(test_project)
        if db_path.exists():
            db_path.unlink(missing_ok=True)

def test_healthcare_dashboard_schema_and_anti_inflation():
    test_project = f"test_hc_{uuid.uuid4().hex[:8]}"
    
    with duckdb_service.connect(test_project) as con:
        con.execute("""
            CREATE TABLE "healthcare_encounters_part_1" (
                encounter_id VARCHAR,
                patient_id VARCHAR,
                encounter_date VARCHAR,
                year INTEGER,
                month INTEGER,
                department VARCHAR,
                facility VARCHAR,
                city VARCHAR,
                visit_type VARCHAR,
                diagnosis VARCHAR,
                billed_amount_inr DOUBLE,
                paid_amount_inr DOUBLE,
                outstanding_amount_inr DOUBLE,
                wait_time_minutes DOUBLE,
                length_of_stay_days DOUBLE
            )
        """)
        con.execute("""
            INSERT INTO "healthcare_encounters_part_1" VALUES
            ('ENC001', 'PAT001', '2026-01-10', 2026, 1, 'Cardiology', 'Metro General', 'Mumbai', 'Inpatient', 'Hypertension', 10000.0, 7000.0, 3000.0, 15.0, 2.5),
            ('ENC002', 'PAT002', '2026-01-12', 2026, 1, 'Neurology', 'City Care', 'Delhi', 'Outpatient', 'Migraine', 5000.0, 5000.0, 0.0, 25.0, 0.0),
            ('ENC003', 'PAT001', '2026-01-15', 2026, 1, 'Cardiology', 'Metro General', 'Mumbai', 'Outpatient', 'Chest Pain', 8000.0, 6000.0, 2000.0, 10.0, 0.0)
        """)

        con.execute("""
            CREATE TABLE "healthcare_lab_results" (
                lab_result_id VARCHAR,
                encounter_id VARCHAR,
                test_name VARCHAR,
                result_flag VARCHAR
            )
        """)
        # 1-to-many: ENC001 has 3 lab tests, ENC002 has 1
        con.execute("""
            INSERT INTO "healthcare_lab_results" VALUES
            ('LAB1', 'ENC001', 'Lipid Panel', 'Within Demo Range'),
            ('LAB2', 'ENC001', 'ECG', 'Above Demo Range'),
            ('LAB3', 'ENC001', 'Troponin', 'Within Demo Range'),
            ('LAB4', 'ENC002', 'CBC', 'Within Demo Range')
        """)

    try:
        dash = dashboard_service.compute_dashboard(test_project)
        assert dash["domain"] == "healthcare"
        assert dash["currency_symbol"] == "₹"
        kpi_map = {k["id"]: k["value"] for k in dash["kpis"]}
        
        # Verify accurate non-inflated KPIs
        assert kpi_map["encounters"] == 3
        assert kpi_map["patients"] == 2
        assert kpi_map["billed"] == 23000.0
        assert kpi_map["paid"] == 18000.0
        assert kpi_map["outstanding"] == 5000.0
        assert kpi_map["lab_tests"] == 4
        
        # Verify charts generated
        chart_ids = [c["id"] for c in dash["charts"]]
        assert "encounter_trend" in chart_ids
        assert "department_performance" in chart_ids
        assert "facility_performance" in chart_ids
        assert "top_diagnoses" in chart_ids
        assert "visit_types" in chart_ids
        assert "lab_results" in chart_ids
    finally:
        db_path = duckdb_service.db_path(test_project)
        if db_path.exists():
            db_path.unlink(missing_ok=True)
