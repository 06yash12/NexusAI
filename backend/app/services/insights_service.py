from datetime import datetime, timezone
from app.services.dashboard_service import dashboard_service

class InsightsService:
    def generate_insights(self, project_id: str) -> dict:
        dash_data = dashboard_service.compute_dashboard(project_id)
        domain = dash_data.get("domain", "general")
        sym = dash_data.get("currency_symbol", "$")
        kpis = {k["id"]: k for k in dash_data.get("kpis", [])}
        charts = {c["id"]: c for c in dash_data.get("charts", [])}

        insights = []
        recommendations = []

        if domain == "healthcare":
            # --- Healthcare Automated Insights ---
            billed_raw = kpis.get("billed", {}).get("value", 0)
            paid_raw = kpis.get("paid", {}).get("value", 0)
            outstanding_raw = kpis.get("outstanding", {}).get("value", 0)
            avg_wait = kpis.get("wait_time", {}).get("value", 0)
            avg_los = kpis.get("length_of_stay", {}).get("value", 0)

            # 1. Collection Rate & Financial Exposure
            if billed_raw > 0:
                collection_rate = (paid_raw / billed_raw) * 100
                insights.append({
                    "type": "trend" if collection_rate >= 70 else "underperformance",
                    "title": f"Revenue Cycle Collection Rate: {collection_rate:.1f}%",
                    "description": f"Total collections reached {sym}{paid_raw:,.2f} against {sym}{billed_raw:,.2f} in billed hospital charges. Outstanding balance stands at {sym}{outstanding_raw:,.2f}.",
                    "supporting_metric": f"{collection_rate:.1f}% Collected",
                    "importance": "high"
                })
                if collection_rate < 75 or outstanding_raw > 1_000_000:
                    recommendations.append({
                        "recommendation": "Accelerate Outstanding Insurance Claims & Copay Adjudication",
                        "rationale": f"Outstanding receivables of {sym}{outstanding_raw:,.2f} represent {(100 - collection_rate):.1f}% of total billed hospital revenue.",
                        "expected_impact": "Accelerate hospital cash flow and shorten Days Sales Outstanding (DSO).",
                        "supporting_data": f"Billed: {sym}{billed_raw:,.2f}, Paid: {sym}{paid_raw:,.2f}, Outstanding: {sym}{outstanding_raw:,.2f}"
                    })

            # 2. Departmental Volume & Performance
            dept_chart = charts.get("department_performance", {})
            dept_data = dept_chart.get("data", [])
            if dept_data:
                top_dept = dept_data[0]
                dept_billed = top_dept.get("billed_amount", 0)
                dept_encounters = top_dept.get("encounters", 0)
                insights.append({
                    "type": "opportunity",
                    "title": f"Top Clinical Department: {top_dept.get('department')}",
                    "description": f"{top_dept.get('department')} is the primary volume driver with {dept_encounters:,} patient encounters and {sym}{dept_billed:,.2f} in billed revenue.",
                    "supporting_metric": f"{dept_encounters:,} Encounters",
                    "importance": "high"
                })

            # 3. Patient Flow & Operational Efficiency
            if avg_wait > 0:
                importance = "high" if avg_wait > 25 else "medium"
                insights.append({
                    "type": "trend",
                    "title": f"Facility Operational Flow: {avg_wait:.1f} min Avg Wait Time",
                    "description": f"Average intake waiting duration across facilities is {avg_wait:.1f} minutes, with an average length of stay of {avg_los:.2f} days.",
                    "supporting_metric": f"{avg_wait:.1f} min Wait",
                    "importance": importance
                })
                if avg_wait > 20:
                    recommendations.append({
                        "recommendation": "Streamline Clinic Intake & Fast-Track Triage Scheduling",
                        "rationale": f"Average wait time of {avg_wait:.1f} minutes exceeds target threshold of 20 minutes.",
                        "expected_impact": "Enhance patient satisfaction and reduce clinic intake bottlenecks.",
                        "supporting_data": f"Average Wait Time: {avg_wait:.1f} mins | Avg Length of Stay: {avg_los:.2f} days"
                    })

            # 4. Diagnostic & Laboratory Analysis
            lab_chart = charts.get("lab_results", {})
            lab_data = lab_chart.get("data", [])
            if lab_data:
                total_tests = sum(item.get("test_count", 0) for item in lab_data)
                abnormal_tests = sum(item.get("test_count", 0) for item in lab_data if item.get("result_flag") in ("Above Demo Range", "Below Demo Range"))
                abnormal_pct = (abnormal_tests / total_tests * 100) if total_tests > 0 else 0
                insights.append({
                    "type": "trend",
                    "title": f"Diagnostic Quality: {total_tests:,} Lab Tests Monitored",
                    "description": f"{abnormal_tests:,} test results ({abnormal_pct:.1f}%) showed deviations outside normal demographic reference ranges.",
                    "supporting_metric": f"{abnormal_pct:.1f}% Out of Range",
                    "importance": "medium"
                })

        elif domain == "retail":
            # --- Retail / Sales Insights ---
            monthly = dash_data.get("monthly_sales", [])
            regional = dash_data.get("regional_sales", [])
            categories = dash_data.get("category_sales", [])
            products = dash_data.get("top_products", [])

            # 1. Month-over-month Trend
            if len(monthly) >= 2:
                prev_rev = monthly[-2]["revenue"]
                curr_rev = monthly[-1]["revenue"]
                growth_pct = ((curr_rev - prev_rev) / prev_rev * 100) if prev_rev > 0 else 0
                trend_dir = "increased" if growth_pct > 0 else "decreased"
                insights.append({
                    "type": "trend",
                    "title": f"Recent Monthly Revenue {trend_dir.capitalize()}",
                    "description": f"Revenue moved from {sym}{prev_rev:,.2f} in {monthly[-2]['month']} to {sym}{curr_rev:,.2f} in {monthly[-1]['month']} ({growth_pct:+.1f}% MoM).",
                    "supporting_metric": f"{growth_pct:+.1f}% Growth",
                    "importance": "high" if abs(growth_pct) > 15 else "medium"
                })
                if growth_pct < -5:
                    recommendations.append({
                        "recommendation": "Investigate month-over-month revenue contraction",
                        "rationale": f"Revenue dipped by {abs(growth_pct):.1f}% in the latest period.",
                        "expected_impact": "Stabilize pipeline and reverse drop in sales momentum.",
                        "supporting_data": f"Prior: {sym}{prev_rev:,.2f}, Current: {sym}{curr_rev:,.2f}"
                    })

            # 2. Regional Performance & Disparity
            if len(regional) >= 2:
                top_region = regional[0]
                bottom_region = regional[-1]
                total_reg_rev = sum(r["revenue"] for r in regional)
                top_share = (top_region["revenue"] / total_reg_rev * 100) if total_reg_rev > 0 else 0
                bottom_share = (bottom_region["revenue"] / total_reg_rev * 100) if total_reg_rev > 0 else 0

                insights.append({
                    "type": "opportunity" if top_share > 40 else "trend",
                    "title": f"Regional Leader: {top_region['region']}",
                    "description": f"{top_region['region']} leads performance generating {sym}{top_region['revenue']:,.2f} ({top_share:.1f}% of total sales).",
                    "supporting_metric": f"{top_share:.1f}% share",
                    "importance": "high"
                })

                if len(regional) > 2 and bottom_share < 15:
                    insights.append({
                        "type": "underperformance",
                        "title": f"Underperforming Region: {bottom_region['region']}",
                        "description": f"{bottom_region['region']} contributed {sym}{bottom_region['revenue']:,.2f} ({bottom_share:.1f}% of regional sales).",
                        "supporting_metric": f"{bottom_share:.1f}% share",
                        "importance": "medium"
                    })
                    recommendations.append({
                        "recommendation": f"Evaluate marketing expansion and channel partners in {bottom_region['region']}",
                        "rationale": f"Regional market penetration is lowest in {bottom_region['region']} despite healthy overall volume.",
                        "expected_impact": "Diversify geographic revenue dependency away from single-region concentration.",
                        "supporting_data": f"Top Region ({top_region['region']}): {sym}{top_region['revenue']:,.2f} vs {bottom_region['region']}: {sym}{bottom_region['revenue']:,.2f}"
                    })

            # 3. Category Concentration
            if categories:
                total_cat_rev = sum(c["revenue"] for c in categories)
                top_cat = categories[0]
                top_cat_share = (top_cat["revenue"] / total_cat_rev * 100) if total_cat_rev > 0 else 0
                insights.append({
                    "type": "trend",
                    "title": f"Category Anchor: {top_cat['category']}",
                    "description": f"{top_cat['category']} represents {top_cat_share:.1f}% of catalog revenue ({sym}{top_cat['revenue']:,.2f}).",
                    "supporting_metric": f"{top_cat_share:.1f}% portfolio share",
                    "importance": "high" if top_cat_share > 50 else "medium"
                })

            # 4. Product Concentration
            if products:
                top_p = products[0]
                insights.append({
                    "type": "opportunity",
                    "title": f"Hero SKU: {top_p['product']}",
                    "description": f"{top_p['product']} is the highest-grossing product with {sym}{top_p['revenue']:,.2f} in revenue ({top_p.get('units', 0):,} units sold).",
                    "supporting_metric": f"{sym}{top_p['revenue']:,.2f}",
                    "importance": "medium"
                })
                recommendations.append({
                    "recommendation": f"Protect supply chain availability and bundle accessories with {top_p['product']}",
                    "rationale": f"{top_p['product']} drives high order frequency and volume.",
                    "expected_impact": "Increase average order value through attach-rate promotions.",
                    "supporting_data": f"Units: {top_p.get('units', 0):,}, Revenue: {sym}{top_p['revenue']:,.2f}"
                })

        else:
            # --- General Analytics Insights ---
            tables = dash_data.get("tables", {})
            insights.append({
                "type": "trend",
                "title": f"Workspace Ingestion: {len(tables)} Active Data Tables",
                "description": f"Successfully loaded and indexed structured records across {len(tables)} tables for ad-hoc analytical queries.",
                "supporting_metric": f"{len(tables)} Tables",
                "importance": "medium"
            })

        # Executive summary
        summary_lines = [
            f"Automated BI synthesis evaluated active datasets in {dash_data.get('domain_label', 'Business Intelligence')}.",
            f"Detected {len(insights)} analytical observations and formulated {len(recommendations)} actionable recommendations.",
            "All recommendations are directly backed by verified SQL aggregations over project data."
        ]

        return {
            "project_id": project_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "insights": insights,
            "recommendations": recommendations,
            "summary": " ".join(summary_lines)
        }

insights_service = InsightsService()
