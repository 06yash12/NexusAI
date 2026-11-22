import logging
from typing import Any
from app.services.duckdb_service import duckdb_service
from app.services.domain_service import domain_service

logger = logging.getLogger("nexus.dashboard")

def resolve_column(columns: list[str], candidates: list[str]) -> str | None:
    """
    Intelligently match column names by:
    1. Exact case-insensitive match
    2. Substring matching in order of candidate priority
    """
    col_map = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in col_map:
            return col_map[cand.lower()]
    for cand in candidates:
        c_low = cand.lower()
        for k_low, original in col_map.items():
            if c_low in k_low or k_low in c_low:
                return original
    return None

def detect_currency(rev_col: str | None, profit_col: str | None, cols: list[str] | None = None) -> str:
    """Detect whether currency is INR (₹), USD ($), EUR (€), GBP (£)."""
    text = f"{rev_col or ''} {profit_col or ''} {' '.join(cols or [])}".lower()
    if "inr" in text or "rupee" in text or "rs" in text:
        return "₹"
    if "eur" in text or "euro" in text:
        return "€"
    if "gbp" in text or "pound" in text:
        return "£"
    return "$"

def format_currency(value: float, symbol: str) -> str:
    """Format numeric values with detected currency symbol."""
    if abs(value) >= 10_000_000:
        return f"{symbol}{value / 10_000_000:.2f} Cr" if symbol == "₹" else f"{symbol}{value / 1_000_000:.2f}M"
    if abs(value) >= 100_000 and symbol == "₹":
        return f"{symbol}{value / 100_000:.2f} L"
    if abs(value) >= 1_000_000:
        return f"{symbol}{value / 1_000_000:.2f}M"
    return f"{symbol}{value:,.2f}"

class DashboardService:
    def compute_dashboard(
        self, 
        project_id: str, 
        table_filter: str | None = None,
        year_filter: int | None = None,
        region_filter: str | None = None,
        category_filter: str | None = None,
        department_filter: str | None = None,
        facility_filter: str | None = None,
        city_filter: str | None = None,
        visit_type_filter: str | None = None
    ) -> dict[str, Any]:
        tables = duckdb_service.list_tables(project_id)
        if not tables:
            return {
                "tables": {},
                "domain": "general",
                "domain_label": "No Data Available",
                "kpis": [],
                "charts": [],
                "monthly_sales": [],
                "yearly_comparison": [],
                "regional_sales": [],
                "category_sales": [],
                "top_products": [],
                "available_years": [],
                "selected_year": year_filter,
                "currency_symbol": "$",
                "column_mapping": {},
                "unavailable_explanations": {
                    "general": "No structured datasets found. Upload a CSV or Excel spreadsheet to compute business analytics."
                },
                "data_freshness": "No structured data available",
                "source_datasets": [],
                "available_dimensions": {}
            }

        schema = duckdb_service.schema(project_id)
        target_tables = [table_filter] if table_filter and table_filter in tables else tables

        # Detect the domain dynamically from the actual table columns
        domain_info = domain_service.detect_domain(schema)
        domain = domain_info["domain"]
        domain_label = domain_info["domain_label"]
        currency_symbol = domain_info["currency_symbol"]

        if domain == "healthcare":
            return self._compute_healthcare_dashboard(
                project_id=project_id,
                schema=schema,
                target_tables=target_tables,
                domain_info=domain_info,
                year_filter=year_filter,
                department_filter=department_filter,
                facility_filter=facility_filter,
                city_filter=city_filter,
                visit_type_filter=visit_type_filter
            )
        elif domain == "retail":
            return self._compute_retail_dashboard(
                project_id=project_id,
                schema=schema,
                target_tables=target_tables,
                domain_info=domain_info,
                year_filter=year_filter,
                region_filter=region_filter,
                category_filter=category_filter,
                city_filter=city_filter
            )
        else:
            return self._compute_general_dashboard(
                project_id=project_id,
                schema=schema,
                target_tables=target_tables,
                domain_info=domain_info,
                year_filter=year_filter
            )

    def _compute_healthcare_dashboard(
        self,
        project_id: str,
        schema: dict[str, list[dict]],
        target_tables: list[str],
        domain_info: dict[str, Any],
        year_filter: int | None = None,
        department_filter: str | None = None,
        facility_filter: str | None = None,
        city_filter: str | None = None,
        visit_type_filter: str | None = None
    ) -> dict[str, Any]:
        """Compute Healthcare & Clinical Intelligence Dashboard using actual DuckDB records."""
        currency_sym = domain_info.get("currency_symbol", "₹")

        # Separate encounter tables and lab tables
        enc_tables = []
        lab_table = None

        for tbl in target_tables:
            tbl_low = tbl.lower()
            cols = [c["name"].lower() for c in schema.get(tbl, [])]
            if "encounter_id" in cols and any(k in cols for k in ("billed_amount_inr", "billed_amount", "department", "diagnosis")):
                enc_tables.append(tbl)
            elif "lab_result_id" in cols or "test_name" in cols or "lab" in tbl_low:
                lab_table = tbl
            elif "encounter" in tbl_low:
                enc_tables.append(tbl)

        if not enc_tables:
            # Fallback to all target tables
            enc_tables = target_tables

        # Construct union query across all encounter parts
        union_enc = " UNION ALL ".join([f'SELECT * FROM "{t}"' for t in enc_tables])
        enc_source = f"({union_enc}) AS enc"

        # Discover available dimensions and years
        available_years: set[int] = set()
        available_departments: set[str] = set()
        available_facilities: set[str] = set()
        available_cities: set[str] = set()
        available_visit_types: set[str] = set()
        available_diagnoses: set[str] = set()

        with duckdb_service.connect(project_id) as con:
            try:
                # Discover years
                for yr_row in con.execute(f"SELECT DISTINCT year FROM ({union_enc}) WHERE year IS NOT NULL ORDER BY 1").fetchall():
                    if yr_row[0]:
                        available_years.add(int(yr_row[0]))
            except Exception:
                pass

            try:
                # Discover departments
                for d_row in con.execute(f"SELECT DISTINCT department FROM ({union_enc}) WHERE department IS NOT NULL ORDER BY 1").fetchall():
                    if d_row[0]:
                        available_departments.add(str(d_row[0]))
            except Exception:
                pass

            try:
                # Discover facilities
                for f_row in con.execute(f"SELECT DISTINCT facility FROM ({union_enc}) WHERE facility IS NOT NULL ORDER BY 1").fetchall():
                    if f_row[0]:
                        available_facilities.add(str(f_row[0]))
            except Exception:
                pass

            try:
                # Discover cities
                for c_row in con.execute(f"SELECT DISTINCT city FROM ({union_enc}) WHERE city IS NOT NULL ORDER BY 1").fetchall():
                    if c_row[0]:
                        available_cities.add(str(c_row[0]))
            except Exception:
                pass

            try:
                # Discover visit types
                for v_row in con.execute(f"SELECT DISTINCT visit_type FROM ({union_enc}) WHERE visit_type IS NOT NULL ORDER BY 1").fetchall():
                    if v_row[0]:
                        available_visit_types.add(str(v_row[0]))
            except Exception:
                pass

            # Build where clause for filters
            filter_clauses = []
            if year_filter is not None:
                filter_clauses.append(f"year = {year_filter}")
            if department_filter:
                escaped_d = department_filter.replace("'", "''")
                filter_clauses.append(f"department = '{escaped_d}'")
            if facility_filter:
                escaped_f = facility_filter.replace("'", "''")
                filter_clauses.append(f"facility = '{escaped_f}'")
            if city_filter:
                escaped_c = city_filter.replace("'", "''")
                filter_clauses.append(f"city = '{escaped_c}'")
            if visit_type_filter:
                escaped_v = visit_type_filter.replace("'", "''")
                filter_clauses.append(f"visit_type = '{escaped_v}'")

            where_sql = f"WHERE {' AND '.join(filter_clauses)}" if filter_clauses else ""

            # 1. Compute Executive Healthcare KPIs
            kpi_sql = f"""
                SELECT 
                    COUNT(*) as total_encounters,
                    COUNT(DISTINCT patient_id) as unique_patients,
                    ROUND(SUM(COALESCE(billed_amount_inr, 0)), 2) as total_billed,
                    ROUND(SUM(COALESCE(paid_amount_inr, 0)), 2) as total_paid,
                    ROUND(SUM(COALESCE(outstanding_amount_inr, 0)), 2) as total_outstanding,
                    ROUND(AVG(COALESCE(wait_time_minutes, 0)), 1) as avg_wait,
                    ROUND(AVG(COALESCE(length_of_stay_days, 0)), 2) as avg_los
                FROM ({union_enc})
                {where_sql}
            """
            kpi_row = con.execute(kpi_sql).fetchone()
            total_enc = int(kpi_row[0] or 0)
            unique_pts = int(kpi_row[1] or 0)
            total_billed = float(kpi_row[2] or 0.0)
            total_paid = float(kpi_row[3] or 0.0)
            total_outstanding = float(kpi_row[4] or 0.0)
            avg_wait = float(kpi_row[5] or 0.0)
            avg_los = float(kpi_row[6] or 0.0)

            collection_rate = (total_paid / total_billed * 100) if total_billed > 0 else 0.0

            total_lab_tests = 0
            if lab_table:
                try:
                    lab_cnt_row = con.execute(f'SELECT count(*) FROM "{lab_table}"').fetchone()
                    total_lab_tests = int(lab_cnt_row[0] or 0)
                except Exception:
                    pass

            kpis = [
                {
                    "id": "encounters",
                    "label": "Total Encounters",
                    "value": total_enc,
                    "formatted": f"{total_enc:,}",
                    "subtext": "Completed clinical encounters",
                    "is_available": True
                },
                {
                    "id": "patients",
                    "label": "Unique Patients",
                    "value": unique_pts,
                    "formatted": f"{unique_pts:,}",
                    "subtext": "Individual patients served",
                    "is_available": True
                },
                {
                    "id": "billed",
                    "label": "Billed Revenue",
                    "value": total_billed,
                    "formatted": format_currency(total_billed, currency_sym),
                    "subtext": "Total gross clinical billings",
                    "is_available": True
                },
                {
                    "id": "paid",
                    "label": "Collections (Paid)",
                    "value": total_paid,
                    "formatted": format_currency(total_paid, currency_sym),
                    "subtext": f"Realized payments ({collection_rate:.1f}% rate)",
                    "is_available": True
                },
                {
                    "id": "outstanding",
                    "label": "Outstanding Amount",
                    "value": total_outstanding,
                    "formatted": format_currency(total_outstanding, currency_sym),
                    "subtext": "Uncollected patient balance",
                    "is_available": True
                },
                {
                    "id": "wait_time",
                    "label": "Avg Wait Time",
                    "value": avg_wait,
                    "formatted": f"{avg_wait:.1f} mins",
                    "subtext": "Triage to provider time",
                    "is_available": True
                },
                {
                    "id": "length_of_stay",
                    "label": "Avg Length of Stay",
                    "value": avg_los,
                    "formatted": f"{avg_los:.2f} days",
                    "subtext": "Inpatient duration",
                    "is_available": True
                }
            ]

            if total_lab_tests > 0:
                kpis.append({
                    "id": "lab_tests",
                    "label": "Laboratory Tests",
                    "value": total_lab_tests,
                    "formatted": f"{total_lab_tests:,}",
                    "subtext": "Diagnostic test records",
                    "is_available": True
                })

            charts = []

            # 2. Patient Encounters & Billed Volume Trend (Monthly)
            monthly_trend = []
            try:
                m_sql = f"""
                    SELECT 
                        year,
                        month,
                        count(*) as encounters,
                        round(sum(billed_amount_inr), 2) as billed_amount,
                        round(sum(paid_amount_inr), 2) as paid_amount
                    FROM ({union_enc})
                    {where_sql}
                    GROUP BY year, month
                    ORDER BY year, month
                """
                for m_r in con.execute(m_sql).fetchall():
                    monthly_trend.append({
                        "period": f"{m_r[0]}-{int(m_r[1]):02d}",
                        "year": m_r[0],
                        "month": m_r[1],
                        "encounters": int(m_r[2]),
                        "billed_amount": float(m_r[3]),
                        "paid_amount": float(m_r[4])
                    })
            except Exception as exc:
                logger.warning("Healthcare monthly trend error: %s", exc)

            if monthly_trend:
                charts.append({
                    "id": "encounter_trend",
                    "title": "Patient Encounters & Billed Volume Trend",
                    "subtitle": "TIME-SERIES ANALYSIS",
                    "type": "line",
                    "available_metrics": ["encounters", "billed_amount", "paid_amount"],
                    "default_metric": "encounters",
                    "available_dimensions": ["period"],
                    "default_dimension": "period",
                    "x_key": "period",
                    "y_keys": ["encounters", "billed_amount"],
                    "data": monthly_trend,
                    "description": "Monthly clinical encounter volume and associated billed amounts",
                    "recommended_types": ["line", "area", "bar"]
                })

            # 3. Department Performance (Revenue & Volume)
            dept_data = []
            try:
                dept_sql = f"""
                    SELECT 
                        department,
                        count(*) as encounters,
                        round(sum(billed_amount_inr), 2) as billed_amount,
                        round(sum(paid_amount_inr), 2) as paid_amount,
                        round(avg(wait_time_minutes), 1) as avg_wait
                    FROM ({union_enc})
                    {where_sql}
                    GROUP BY department
                    ORDER BY billed_amount DESC
                """
                for d_r in con.execute(dept_sql).fetchall():
                    if d_r[0]:
                        dept_data.append({
                            "department": str(d_r[0]),
                            "encounters": int(d_r[1]),
                            "billed_amount": float(d_r[2]),
                            "paid_amount": float(d_r[3]),
                            "avg_wait": float(d_r[4])
                        })
            except Exception as exc:
                logger.warning("Healthcare department query error: %s", exc)

            if dept_data:
                charts.append({
                    "id": "department_performance",
                    "title": "Department Performance & Billings",
                    "subtitle": "CLINICAL SPECIALTY BREAKDOWN",
                    "type": "bar",
                    "available_metrics": ["billed_amount", "paid_amount", "encounters", "avg_wait"],
                    "default_metric": "billed_amount",
                    "available_dimensions": ["department"],
                    "default_dimension": "department",
                    "x_key": "department",
                    "y_keys": ["billed_amount", "paid_amount"],
                    "data": dept_data,
                    "description": "Billed revenue and collections across clinical departments",
                    "recommended_types": ["bar", "horizontal_bar", "line"]
                })

            # 4. Facility Performance & City Distribution
            facility_data = []
            try:
                fac_sql = f"""
                    SELECT 
                        facility,
                        city,
                        count(*) as encounters,
                        round(sum(billed_amount_inr), 2) as billed_amount
                    FROM ({union_enc})
                    {where_sql}
                    GROUP BY facility, city
                    ORDER BY billed_amount DESC
                    LIMIT 8
                """
                for f_r in con.execute(fac_sql).fetchall():
                    if f_r[0]:
                        facility_data.append({
                            "facility": f"{f_r[0]} ({f_r[1]})",
                            "encounters": int(f_r[2]),
                            "billed_amount": float(f_r[3])
                        })
            except Exception as exc:
                logger.warning("Healthcare facility query error: %s", exc)

            if facility_data:
                charts.append({
                    "id": "facility_performance",
                    "title": "Facility Encounters & Regional Volume",
                    "subtitle": "GEOGRAPHIC & FACILITY REACH",
                    "type": "bar",
                    "available_metrics": ["billed_amount", "encounters"],
                    "default_metric": "billed_amount",
                    "available_dimensions": ["facility"],
                    "default_dimension": "facility",
                    "x_key": "facility",
                    "y_keys": ["billed_amount", "encounters"],
                    "data": facility_data,
                    "description": "Top healthcare facilities ranked by clinical billings and patient volume",
                    "recommended_types": ["bar", "horizontal_bar"]
                })

            # 5. Top Diagnoses Breakdown
            diagnosis_data = []
            try:
                diag_sql = f"""
                    SELECT 
                        diagnosis,
                        count(*) as encounters,
                        round(sum(billed_amount_inr), 2) as billed_amount
                    FROM ({union_enc})
                    {where_sql}
                    GROUP BY diagnosis
                    ORDER BY encounters DESC
                    LIMIT 8
                """
                for diag_r in con.execute(diag_sql).fetchall():
                    if diag_r[0]:
                        diagnosis_data.append({
                            "diagnosis": str(diag_r[0]),
                            "encounters": int(diag_r[1]),
                            "billed_amount": float(diag_r[2])
                        })
            except Exception as exc:
                logger.warning("Healthcare diagnosis query error: %s", exc)

            if diagnosis_data:
                charts.append({
                    "id": "top_diagnoses",
                    "title": "Top Diagnoses Breakdown",
                    "subtitle": "CLINICAL EPIDEMIOLOGY",
                    "type": "bar",
                    "available_metrics": ["encounters", "billed_amount"],
                    "default_metric": "encounters",
                    "available_dimensions": ["diagnosis"],
                    "default_dimension": "diagnosis",
                    "x_key": "diagnosis",
                    "y_keys": ["encounters"],
                    "data": diagnosis_data,
                    "description": "Most prevalent patient diagnoses ranked by encounter frequency",
                    "recommended_types": ["bar", "horizontal_bar"]
                })

            # 6. Visit Type Distribution
            visit_data = []
            try:
                visit_sql = f"""
                    SELECT 
                        visit_type,
                        count(*) as encounters,
                        round(sum(billed_amount_inr), 2) as billed_amount
                    FROM ({union_enc})
                    {where_sql}
                    GROUP BY visit_type
                    ORDER BY encounters DESC
                """
                for v_r in con.execute(visit_sql).fetchall():
                    if v_r[0]:
                        visit_data.append({
                            "visit_type": str(v_r[0]),
                            "encounters": int(v_r[1]),
                            "billed_amount": float(v_r[2])
                        })
            except Exception as exc:
                logger.warning("Healthcare visit type query error: %s", exc)

            if visit_data:
                charts.append({
                    "id": "visit_types",
                    "title": "Visit Type Distribution",
                    "subtitle": "CARE DELIVERY MODALITIES",
                    "type": "donut",
                    "available_metrics": ["encounters", "billed_amount"],
                    "default_metric": "encounters",
                    "available_dimensions": ["visit_type"],
                    "default_dimension": "visit_type",
                    "x_key": "visit_type",
                    "y_keys": ["encounters"],
                    "data": visit_data,
                    "description": "Care delivery modalities: Outpatient, Inpatient, Emergency, Day Care",
                    "recommended_types": ["donut", "pie", "bar"]
                })

            # 7. Laboratory Test Flags & Distribution
            if lab_table:
                lab_flags_data = []
                try:
                    flag_sql = f"""
                        SELECT 
                            COALESCE(result_flag, 'Unknown') as result_flag,
                            count(*) as test_count
                        FROM "{lab_table}"
                        GROUP BY 1
                        ORDER BY test_count DESC
                    """
                    for flg_r in con.execute(flag_sql).fetchall():
                        if flg_r[0]:
                            lab_flags_data.append({
                                "result_flag": str(flg_r[0]),
                                "test_count": int(flg_r[1])
                            })
                except Exception as exc:
                    logger.warning("Healthcare lab flags error: %s", exc)

                if lab_flags_data:
                    charts.append({
                        "id": "lab_results",
                        "title": "Laboratory Diagnostic Flags Distribution",
                        "subtitle": "DIAGNOSTIC TEST RANGES",
                        "type": "donut",
                        "available_metrics": ["test_count"],
                        "default_metric": "test_count",
                        "available_dimensions": ["result_flag"],
                        "default_dimension": "result_flag",
                        "x_key": "result_flag",
                        "y_keys": ["test_count"],
                        "data": lab_flags_data,
                        "description": "Distribution of patient lab results within vs outside reference ranges",
                        "recommended_types": ["donut", "pie", "bar"]
                    })

        return {
            "tables": schema,
            "domain": "healthcare",
            "domain_label": "Healthcare & Clinical Intelligence",
            "kpis": kpis,
            "charts": charts,
            "monthly_sales": [],
            "yearly_comparison": [],
            "regional_sales": [],
            "category_sales": [],
            "top_products": [],
            "available_years": sorted(list(available_years)),
            "selected_year": year_filter,
            "currency_symbol": currency_sym,
            "column_mapping": {
                "encounter_id": "encounter_id",
                "patient_id": "patient_id",
                "department": "department",
                "facility": "facility",
                "city": "city",
                "diagnosis": "diagnosis",
                "billed_amount": "billed_amount_inr",
                "paid_amount": "paid_amount_inr",
                "outstanding_amount": "outstanding_amount_inr"
            },
            "unavailable_explanations": {},
            "data_freshness": "Real-time DuckDB calculations across ingested healthcare records",
            "source_datasets": enc_tables + ([lab_table] if lab_table else []),
            "available_dimensions": {
                "departments": sorted(list(available_departments)),
                "facilities": sorted(list(available_facilities)),
                "cities": sorted(list(available_cities)),
                "visit_types": sorted(list(available_visit_types)),
                "diagnoses": sorted(list(available_diagnoses))
            }
        }

    def _compute_retail_dashboard(
        self,
        project_id: str,
        schema: dict[str, list[dict]],
        target_tables: list[str],
        domain_info: dict[str, Any],
        year_filter: int | None = None,
        region_filter: str | None = None,
        category_filter: str | None = None,
        city_filter: str | None = None
    ) -> dict[str, Any]:
        """Compute Retail & E-Commerce Dashboard using actual DuckDB records."""
        # Metrics accumulators
        total_revenue = 0.0
        total_profit = 0.0
        total_orders = 0
        total_quantity = 0
        total_cancelled_orders = 0
        total_returned_orders = 0

        has_revenue = False
        has_profit = False
        has_orders = False
        has_quantity = False

        available_regions_set: set[str] = set()
        available_categories_set: set[str] = set()
        available_cities_set: set[str] = set()
        available_channels_set: set[str] = set()

        monthly_sales: list[dict[str, Any]] = []
        yearly_comparison: list[dict[str, Any]] = []
        regional_sales: list[dict[str, Any]] = []
        category_sales: list[dict[str, Any]] = []
        top_products: list[dict[str, Any]] = []
        available_years_set: set[int] = set()

        unavailable_explanations: dict[str, str] = {}
        active_column_mapping: dict[str, str | None] = {}
        currency_symbol = domain_info.get("currency_symbol", "₹")

        with duckdb_service.connect(project_id) as con:
            for tbl in target_tables:
                quoted = duckdb_service.quote(tbl)
                cols_info = schema.get(tbl, [])
                cols = [c["name"] for c in cols_info]

                rev_col = resolve_column(cols, [
                    "net_revenue_inr", "net_revenue", "net_sales_inr", "net_sales",
                    "revenue_inr", "sales_inr", "gross_sales_inr", "gross_sales",
                    "total_revenue", "revenue", "sales", "total_amount", "amount"
                ])
                profit_col = resolve_column(cols, [
                    "profit_inr", "net_profit_inr", "net_profit", "profit",
                    "gross_profit_inr", "gross_profit", "margin_inr", "earnings"
                ])
                qty_col = resolve_column(cols, [
                    "quantity", "quantity_sold", "qty", "units", "items_sold", "units_sold"
                ])
                order_col = resolve_column(cols, [
                    "sales_order_id", "order_id", "orderid", "transaction_id", "invoice_id", "id"
                ])
                price_col = resolve_column(cols, [
                    "unit_price_inr", "unit_price", "price", "unitprice"
                ])
                cost_col = resolve_column(cols, [
                    "unit_cost_inr", "unit_cost", "total_cost_inr", "total_cost", "cogs_inr", "cogs", "cost"
                ])
                disc_col = resolve_column(cols, [
                    "discount_amount_inr", "discount_amount", "discount", "discount_val"
                ])
                date_col = resolve_column(cols, [
                    "order_date", "orderdate", "transaction_date", "invoice_date",
                    "date", "created_at", "timestamp"
                ])
                year_col = resolve_column(cols, ["year", "order_year"])
                region_col = resolve_column(cols, [
                    "region", "territory", "zone", "location", "state"
                ])
                cat_col = resolve_column(cols, [
                    "category", "product_category", "segment", "department"
                ])
                prod_col = resolve_column(cols, [
                    "product", "product_name", "item", "item_name", "sku"
                ])
                status_col = resolve_column(cols, [
                    "order_status", "status", "delivery_status", "fulfillment_status"
                ])
                channel_col = resolve_column(cols, [
                    "sales_channel", "channel", "platform"
                ])
                city_col = resolve_column(cols, ["city", "town"])

                # Determine currency
                if not currency_symbol or currency_symbol == "$":
                    currency_symbol = detect_currency(rev_col, profit_col, cols)

                active_column_mapping = {
                    "revenue": rev_col,
                    "profit": profit_col,
                    "order_date": date_col,
                    "quantity": qty_col,
                    "order_id": order_col,
                    "region": region_col,
                    "category": cat_col,
                    "product": prod_col,
                    "order_status": status_col,
                    "year": year_col
                }

                rev_expr = None
                if rev_col:
                    rev_expr = f'"{rev_col}"'
                elif price_col and qty_col:
                    if disc_col:
                        rev_expr = f'(("{price_col}" * "{qty_col}") - COALESCE("{disc_col}", 0))'
                    else:
                        rev_expr = f'("{price_col}" * "{qty_col}")'

                profit_expr = None
                if profit_col:
                    profit_expr = f'"{profit_col}"'
                elif rev_expr and cost_col:
                    if "total_cost" in cost_col.lower() or "cogs" in cost_col.lower():
                        profit_expr = f'({rev_expr} - COALESCE("{cost_col}", 0))'
                    elif qty_col:
                        profit_expr = f'({rev_expr} - (COALESCE("{cost_col}", 0) * "{qty_col}"))'

                # Discover available years
                try:
                    if year_col:
                        for yr_r in con.execute(f'SELECT DISTINCT "{year_col}" FROM {quoted} WHERE "{year_col}" IS NOT NULL ORDER BY 1').fetchall():
                            if yr_r[0] is not None:
                                try:
                                    available_years_set.add(int(yr_r[0]))
                                except Exception:
                                    pass
                    elif date_col:
                        for yr_r in con.execute(f'SELECT DISTINCT CAST(strftime(TRY_CAST("{date_col}" AS DATE), \'%Y\') AS INTEGER) FROM {quoted} WHERE "{date_col}" IS NOT NULL ORDER BY 1').fetchall():
                            if yr_r[0] is not None:
                                available_years_set.add(int(yr_r[0]))
                except Exception:
                    pass

                # Discover dimensions
                try:
                    if region_col:
                        for r_r in con.execute(f'SELECT DISTINCT "{region_col}" FROM {quoted} WHERE "{region_col}" IS NOT NULL ORDER BY 1').fetchall():
                            if r_r[0]:
                                available_regions_set.add(str(r_r[0]))
                    if cat_col:
                        for c_r in con.execute(f'SELECT DISTINCT "{cat_col}" FROM {quoted} WHERE "{cat_col}" IS NOT NULL ORDER BY 1').fetchall():
                            if c_r[0]:
                                available_categories_set.add(str(c_r[0]))
                    if city_col:
                        for ct_r in con.execute(f'SELECT DISTINCT "{city_col}" FROM {quoted} WHERE "{city_col}" IS NOT NULL ORDER BY 1').fetchall():
                            if ct_r[0]:
                                available_cities_set.add(str(ct_r[0]))
                    if channel_col:
                        for ch_r in con.execute(f'SELECT DISTINCT "{channel_col}" FROM {quoted} WHERE "{channel_col}" IS NOT NULL ORDER BY 1').fetchall():
                            if ch_r[0]:
                                available_channels_set.add(str(ch_r[0]))
                except Exception:
                    pass

                # Base filtering: Exclude cancelled orders from completed sales
                filter_clauses = []
                if status_col:
                    filter_clauses.append(f'("{status_col}" IS NULL OR LOWER("{status_col}") NOT IN (\'cancelled\', \'canceled\'))')

                if year_filter is not None:
                    if year_col:
                        filter_clauses.append(f'"{year_col}" = {year_filter}')
                    elif date_col:
                        filter_clauses.append(f"CAST(strftime(TRY_CAST(\"{date_col}\" AS DATE), '%Y') AS INTEGER) = {year_filter}")

                if region_filter and region_col:
                    escaped_reg = region_filter.replace("'", "''")
                    filter_clauses.append(f'"{region_col}" = \'{escaped_reg}\'')

                if category_filter and cat_col:
                    escaped_cat = category_filter.replace("'", "''")
                    filter_clauses.append(f'"{cat_col}" = \'{escaped_cat}\'')

                where_sql = f"WHERE {' AND '.join(filter_clauses)}" if filter_clauses else ""

                if status_col:
                    try:
                        st_row = con.execute(f"""
                            SELECT 
                                COUNT(CASE WHEN LOWER("{status_col}") IN ('cancelled', 'canceled') THEN 1 END),
                                COUNT(CASE WHEN LOWER("{status_col}") = 'returned' THEN 1 END)
                            FROM {quoted}
                        """).fetchone()
                        if st_row:
                            total_cancelled_orders += int(st_row[0] or 0)
                            total_returned_orders += int(st_row[1] or 0)
                    except Exception:
                        pass

                # KPIs
                select_kpis = ["COUNT(*) as total_rows"]
                if rev_expr:
                    select_kpis.append(f"SUM(COALESCE({rev_expr}, 0)) as sum_revenue")
                if profit_expr:
                    select_kpis.append(f"SUM(COALESCE({profit_expr}, 0)) as sum_profit")
                if qty_col:
                    select_kpis.append(f'SUM(COALESCE("{qty_col}", 0)) as sum_qty')
                if order_col:
                    select_kpis.append(f'COUNT(DISTINCT "{order_col}") as dist_orders')

                try:
                    kpi_row = con.execute(f"SELECT {', '.join(select_kpis)} FROM {quoted} {where_sql}").fetchone()
                    if kpi_row:
                        desc = [d[0] for d in con.description]
                        res = dict(zip(desc, kpi_row))
                        if "sum_revenue" in res and res["sum_revenue"] is not None:
                            total_revenue += float(res["sum_revenue"])
                            has_revenue = True
                        if "sum_profit" in res and res["sum_profit"] is not None:
                            total_profit += float(res["sum_profit"])
                            has_profit = True
                        if "sum_qty" in res and res["sum_qty"] is not None:
                            total_quantity += int(res["sum_qty"])
                            has_quantity = True
                        if "dist_orders" in res and res["dist_orders"] is not None:
                            total_orders += int(res["dist_orders"])
                            has_orders = True
                        elif "total_rows" in res:
                            total_orders += int(res["total_rows"])
                            has_orders = True
                except Exception as exc:
                    logger.warning("KPI aggregation error on %s: %s", tbl, exc)

                # Monthly Sales Trend
                if date_col and rev_expr:
                    try:
                        profit_select = f"ROUND(SUM(COALESCE({profit_expr}, 0)), 2) as profit," if profit_expr else ""
                        m_sql = f"""
                            SELECT 
                                strftime(TRY_CAST("{date_col}" AS DATE), '%Y-%m') as month,
                                CAST(strftime(TRY_CAST("{date_col}" AS DATE), '%Y') AS INTEGER) as year,
                                ROUND(SUM(COALESCE({rev_expr}, 0)), 2) as revenue,
                                {profit_select}
                                COUNT(*) as orders
                            FROM {quoted}
                            {where_sql}
                            GROUP BY 1, 2
                            ORDER BY 1 ASC
                        """
                        for m_row in con.execute(m_sql).fetchall():
                            if m_row[0]:
                                item = {
                                    "month": m_row[0],
                                    "year": m_row[1],
                                    "revenue": float(m_row[2]),
                                    "orders": int(m_row[4] if profit_expr else m_row[3])
                                }
                                if profit_expr:
                                    item["profit"] = float(m_row[3])
                                monthly_sales.append(item)
                    except Exception as exc:
                        logger.warning("Monthly query error: %s", exc)

                # Regional Sales
                if region_col and rev_expr:
                    try:
                        pft_reg = f"ROUND(SUM(COALESCE({profit_expr}, 0)), 2) as profit," if profit_expr else ""
                        reg_sql = f"""
                            SELECT 
                                "{region_col}" as region,
                                ROUND(SUM(COALESCE({rev_expr}, 0)), 2) as revenue,
                                {pft_reg}
                                COUNT(*) as orders
                            FROM {quoted}
                            {where_sql}
                            GROUP BY 1
                            ORDER BY revenue DESC
                            LIMIT 10
                        """
                        for r_row in con.execute(reg_sql).fetchall():
                            if r_row[0]:
                                item = {
                                    "region": str(r_row[0]),
                                    "revenue": float(r_row[1]),
                                    "orders": int(r_row[3] if profit_expr else r_row[2])
                                }
                                if profit_expr:
                                    item["profit"] = float(r_row[2])
                                regional_sales.append(item)
                    except Exception as exc:
                        logger.warning("Regional query error: %s", exc)

                # Category Sales
                if cat_col and rev_expr:
                    try:
                        pft_cat = f"ROUND(SUM(COALESCE({profit_expr}, 0)), 2) as profit," if profit_expr else ""
                        cat_sql = f"""
                            SELECT 
                                "{cat_col}" as category,
                                ROUND(SUM(COALESCE({rev_expr}, 0)), 2) as revenue,
                                {pft_cat}
                                COUNT(*) as orders
                            FROM {quoted}
                            {where_sql}
                            GROUP BY 1
                            ORDER BY revenue DESC
                            LIMIT 10
                        """
                        for c_row in con.execute(cat_sql).fetchall():
                            if c_row[0]:
                                item = {
                                    "category": str(c_row[0]),
                                    "revenue": float(c_row[1]),
                                    "orders": int(c_row[3] if profit_expr else c_row[2])
                                }
                                if profit_expr:
                                    item["profit"] = float(c_row[2])
                                category_sales.append(item)
                    except Exception as exc:
                        logger.warning("Category query error: %s", exc)

                # Top Products
                if prod_col and rev_expr:
                    try:
                        qty_clause = f'SUM(COALESCE("{qty_col}", 1))' if qty_col else "COUNT(*)"
                        pft_prod = f"ROUND(SUM(COALESCE({profit_expr}, 0)), 2) as profit," if profit_expr else ""
                        prod_sql = f"""
                            SELECT 
                                "{prod_col}" as product,
                                ROUND(SUM(COALESCE({rev_expr}, 0)), 2) as revenue,
                                {pft_prod}
                                {qty_clause} as units
                            FROM {quoted}
                            {where_sql}
                            GROUP BY 1
                            ORDER BY revenue DESC
                            LIMIT 5
                        """
                        for p_idx, p_row in enumerate(con.execute(prod_sql).fetchall(), 1):
                            if p_row[0]:
                                item = {
                                    "rank": p_idx,
                                    "product": str(p_row[0]),
                                    "revenue": float(p_row[1]),
                                    "units": int(p_row[3] if profit_expr else p_row[2])
                                }
                                if profit_expr:
                                    item["profit"] = float(p_row[2])
                                top_products.append(item)
                    except Exception as exc:
                        logger.warning("Product query error: %s", exc)

        # Build Retail KPIs
        kpis = []
        if has_revenue:
            cancel_subtext = f"Excludes {total_cancelled_orders} cancelled orders" if total_cancelled_orders > 0 else "Net completed sales"
            formatted_rev = format_currency(total_revenue, currency_symbol)
            kpis.append({
                "id": "revenue",
                "label": "Total Revenue",
                "value": total_revenue,
                "formatted": formatted_rev,
                "subtext": cancel_subtext,
                "is_available": True
            })
        if has_orders:
            kpis.append({
                "id": "orders",
                "label": "Total Orders",
                "value": total_orders,
                "formatted": f"{total_orders:,}",
                "subtext": f"Completed orders ({total_returned_orders} returned)" if total_returned_orders > 0 else "Completed orders",
                "is_available": True
            })
        if has_quantity:
            kpis.append({
                "id": "quantity",
                "label": "Units Sold",
                "value": total_quantity,
                "formatted": f"{total_quantity:,}",
                "subtext": "Total items purchased",
                "is_available": True
            })
        if has_profit:
            formatted_prof = format_currency(total_profit, currency_symbol)
            kpis.append({
                "id": "profit",
                "label": "Total Profit",
                "value": total_profit,
                "formatted": formatted_prof,
                "subtext": "Gross margin earnings",
                "is_available": True
            })
            if total_revenue > 0:
                margin_pct = (total_profit / total_revenue) * 100
                kpis.append({
                    "id": "margin",
                    "label": "Profit Margin",
                    "value": margin_pct,
                    "formatted": f"{margin_pct:.1f}%",
                    "subtext": "Net profitability ratio",
                    "is_available": True
                })

        if has_revenue and has_orders and total_orders > 0:
            aov = round(total_revenue / total_orders, 2)
            kpis.append({
                "id": "aov",
                "label": "Average Order Value",
                "value": aov,
                "formatted": format_currency(aov, currency_symbol),
                "subtext": "Revenue per completed order",
                "is_available": True
            })

        # Build AI Selected Charts for Retail
        charts = []
        if monthly_sales:
            charts.append({
                "id": "monthly_sales",
                "title": "Monthly Sales & Revenue Trend",
                "subtitle": "TIME-SERIES ANALYSIS",
                "type": "line",
                "available_metrics": ["revenue"] + (["profit"] if has_profit else []) + ["orders"],
                "default_metric": "revenue",
                "available_dimensions": ["month"],
                "default_dimension": "month",
                "x_key": "month",
                "y_keys": ["revenue"] + (["profit"] if has_profit else []),
                "data": monthly_sales,
                "description": "Chronological revenue and profitability momentum",
                "recommended_types": ["line", "area", "bar"]
            })
        if regional_sales:
            charts.append({
                "id": "regional_sales",
                "title": "Geographic Performance by Region",
                "subtitle": "GEOGRAPHIC PERFORMANCE",
                "type": "bar",
                "available_metrics": ["revenue"] + (["profit"] if has_profit else []) + ["orders"],
                "default_metric": "revenue",
                "available_dimensions": ["region"],
                "default_dimension": "region",
                "x_key": "region",
                "y_keys": ["revenue"] + (["profit"] if has_profit else []),
                "data": regional_sales,
                "description": "Territory revenue and order volume distribution",
                "recommended_types": ["bar", "horizontal_bar"]
            })
        if category_sales:
            charts.append({
                "id": "category_sales",
                "title": "Category Portfolio Performance",
                "subtitle": "PORTFOLIO MIX",
                "type": "bar",
                "available_metrics": ["revenue"] + (["profit"] if has_profit else []) + ["orders"],
                "default_metric": "revenue",
                "available_dimensions": ["category"],
                "default_dimension": "category",
                "x_key": "category",
                "y_keys": ["revenue"] + (["profit"] if has_profit else []),
                "data": category_sales,
                "description": "Merchandise department breakdown",
                "recommended_types": ["bar", "horizontal_bar", "pie", "donut"]
            })
        if top_products:
            charts.append({
                "id": "top_products",
                "title": "Top 5 Performing Products",
                "subtitle": "PRODUCT LEADERBOARD",
                "type": "bar",
                "available_metrics": ["revenue"] + (["profit"] if has_profit else []) + ["units"],
                "default_metric": "revenue",
                "available_dimensions": ["product"],
                "default_dimension": "product",
                "x_key": "product",
                "y_keys": ["revenue"],
                "data": top_products,
                "description": "Top revenue-generating merchandise items",
                "recommended_types": ["bar", "horizontal_bar"]
            })

        return {
            "tables": schema,
            "domain": "retail",
            "domain_label": "Retail & E-Commerce Analytics",
            "kpis": kpis,
            "charts": charts,
            "monthly_sales": monthly_sales,
            "yearly_comparison": yearly_comparison,
            "regional_sales": regional_sales,
            "category_sales": category_sales,
            "top_products": top_products,
            "available_years": sorted(list(available_years_set)),
            "selected_year": year_filter,
            "currency_symbol": currency_symbol,
            "column_mapping": active_column_mapping,
            "unavailable_explanations": unavailable_explanations,
            "data_freshness": "Real-time DuckDB calculations across retail orders",
            "source_datasets": target_tables,
            "available_dimensions": {
                "regions": sorted(list(available_regions_set)),
                "categories": sorted(list(available_categories_set)),
                "cities": sorted(list(available_cities_set)),
                "sales_channels": sorted(list(available_channels_set))
            }
        }

    def _compute_general_dashboard(
        self,
        project_id: str,
        schema: dict[str, list[dict]],
        target_tables: list[str],
        domain_info: dict[str, Any],
        year_filter: int | None = None
    ) -> dict[str, Any]:
        """Dynamically adapt to arbitrary schemas and generate generic BI metrics."""
        currency_sym = domain_info.get("currency_symbol", "$")
        kpis = []
        charts = []
        available_dims: dict[str, list[str]] = {}

        with duckdb_service.connect(project_id) as con:
            total_records = 0
            for tbl in target_tables:
                quoted = duckdb_service.quote(tbl)
                cnt = con.execute(f"SELECT count(*) FROM {quoted}").fetchone()[0]
                total_records += int(cnt or 0)

            kpis.append({
                "id": "records",
                "label": "Total Records",
                "value": total_records,
                "formatted": f"{total_records:,}",
                "subtext": "Indexed database rows",
                "is_available": True
            })

        return {
            "tables": schema,
            "domain": "general",
            "domain_label": "General Business Intelligence",
            "kpis": kpis,
            "charts": charts,
            "monthly_sales": [],
            "yearly_comparison": [],
            "regional_sales": [],
            "category_sales": [],
            "top_products": [],
            "available_years": [],
            "selected_year": year_filter,
            "currency_symbol": currency_sym,
            "column_mapping": {},
            "unavailable_explanations": {},
            "data_freshness": "Dynamic schema analytics",
            "source_datasets": target_tables,
            "available_dimensions": available_dims
        }

dashboard_service = DashboardService()
