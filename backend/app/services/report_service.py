"""
NEXUS AI — Report Generation Service
Generates Excel and PDF business intelligence reports from DuckDB project data.
"""
import io
from datetime import datetime
from typing import Any


class ReportService:
    def _get_dashboard_data(self, project_id: str) -> dict[str, Any]:
        """Fetch full dashboard data for report generation."""
        from app.services.dashboard_service import dashboard_service
        return dashboard_service.compute_dashboard(project_id)

    def _get_insights_data(self, project_id: str) -> dict[str, Any]:
        """Fetch insights data."""
        try:
            from app.services.insights_service import insights_service
            return insights_service.generate_insights(project_id)
        except Exception:
            return {"insights": [], "recommendations": []}

    # ------------------------------------------------------------------ Excel
    def generate_excel(self, project_id: str) -> bytes:
        """Generate a comprehensive Excel workbook with multiple sheets."""
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        data = self._get_dashboard_data(project_id)
        insights = self._get_insights_data(project_id)
        kpi_list = data.get("kpis", [])
        kpi_map = {k.get("id"): k for k in kpi_list if isinstance(k, dict)}
        currency = data.get("currency_symbol", "$")

        wb = openpyxl.Workbook()

        # --- Colour palette ---
        HEADER_FILL = PatternFill("solid", fgColor="1E293B")
        SUBHEADER_FILL = PatternFill("solid", fgColor="334155")
        ALT_FILL = PatternFill("solid", fgColor="F1F5F9")
        WHITE = "FFFFFF"
        DARK = "1E293B"

        thin = Side(border_style="thin", color="CBD5E1")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        def header_style(cell, text, bold=True):
            cell.value = text
            cell.font = Font(bold=bold, color=WHITE, size=11)
            cell.fill = HEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = border

        def sub_header(cell, text):
            cell.value = text
            cell.font = Font(bold=True, color=WHITE, size=10)
            cell.fill = SUBHEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border

        def data_cell(cell, value, alt=False, bold=False, num_format=None):
            cell.value = value
            cell.font = Font(bold=bold, color=DARK, size=10)
            if alt:
                cell.fill = ALT_FILL
            cell.alignment = Alignment(vertical="center")
            cell.border = border
            if num_format:
                cell.number_format = num_format

        def set_col_widths(ws, widths):
            for col, w in enumerate(widths, 1):
                ws.column_dimensions[get_column_letter(col)].width = w

        # ---- Sheet 1: Executive Summary ----
        ws1 = wb.active
        ws1.title = "Executive Summary"
        ws1.row_dimensions[1].height = 30

        ws1.merge_cells("A1:D1")
        title_cell = ws1["A1"]
        title_cell.value = f"NEXUS AI — Executive KPI Summary  |  Generated {datetime.now().strftime('%d %b %Y %H:%M')}"
        title_cell.font = Font(bold=True, color=WHITE, size=13)
        title_cell.fill = PatternFill("solid", fgColor="0F172A")
        title_cell.alignment = Alignment(horizontal="left", vertical="center")

        ws1.append([])  # blank row

        # Determine domain-aware KPI rows
        domain = data.get("domain", "general")
        if domain == "healthcare":
            kpi_rows = [
                ("Billed Revenue", kpi_map.get("billed", {}).get("formatted", "N/A"), "Total gross clinical billings"),
                ("Collections (Paid)", kpi_map.get("paid", {}).get("formatted", "N/A"), "Realized patient & insurance collections"),
                ("Outstanding Balance", kpi_map.get("outstanding", {}).get("formatted", "N/A"), "Pending receivables"),
                ("Total Encounters", kpi_map.get("encounters", {}).get("formatted", "N/A"), "Completed clinical encounters"),
                ("Unique Patients", kpi_map.get("patients", {}).get("formatted", "N/A"), "Individual patients served"),
            ]
        elif domain == "retail":
            rev_kpi = kpi_map.get("revenue", {})
            pft_kpi = kpi_map.get("profit", {})
            ord_kpi = kpi_map.get("orders", {})
            qty_kpi = kpi_map.get("quantity", {})
            aov_kpi = kpi_map.get("aov", {})
            kpi_rows = [
                ("Total Revenue", rev_kpi.get("formatted", "N/A"), rev_kpi.get("subtext", "Completed revenue")),
                ("Total Profit", pft_kpi.get("formatted", "N/A"), pft_kpi.get("subtext", "Net profit")),
                ("Total Orders", ord_kpi.get("formatted", "N/A"), ord_kpi.get("subtext", "Completed orders")),
                ("Units Sold", qty_kpi.get("formatted", "N/A"), qty_kpi.get("subtext", "Total units")),
                ("Avg Order Value", aov_kpi.get("formatted", "N/A"), aov_kpi.get("subtext", "AOV")),
            ]
        else:
            kpi_rows = [
                (k.get("label", k.get("id", "Metric")), k.get("formatted", str(k.get("value", "N/A"))), k.get("subtext", ""))
                for k in kpi_list if isinstance(k, dict)
            ]
            if not kpi_rows:
                kpi_rows = [("Status", "No structured metrics available", "Upload tabular data to compute KPIs")]

        for col_idx, hdr in enumerate(["KPI", "Value", "Description"], 1):
            header_style(ws1.cell(row=3, column=col_idx), hdr)

        for i, (name, val, desc) in enumerate(kpi_rows):
            row = i + 4
            alt = i % 2 == 1
            data_cell(ws1.cell(row=row, column=1), name, alt=alt, bold=True)
            data_cell(ws1.cell(row=row, column=2), val, alt=alt)
            data_cell(ws1.cell(row=row, column=3), desc, alt=alt)

        set_col_widths(ws1, [28, 20, 40])

        # Strategic Findings & Observations
        findings = insights.get("insights", []) or insights.get("findings", [])
        if findings:
            start_row = len(kpi_rows) + 6
            ws1.merge_cells(f"A{start_row}:D{start_row}")
            cell = ws1.cell(row=start_row, column=1)
            cell.value = "Strategic Findings"
            cell.font = Font(bold=True, color=WHITE, size=11)
            cell.fill = SUBHEADER_FILL
            cell.alignment = Alignment(horizontal="left", vertical="center")

            for j, f_item in enumerate(findings[:6]):
                r = start_row + 1 + j
                c = ws1.cell(row=r, column=1)
                ws1.merge_cells(f"A{r}:D{r}")
                f_title = f_item.get("title", "")
                f_detail = f_item.get("description", f_item.get("detail", ""))
                c.value = f"• {f_title} — {f_detail}"
                c.font = Font(size=10, color=DARK)
                c.alignment = Alignment(wrap_text=True, vertical="center")
                ws1.row_dimensions[r].height = 24

        # ---- Sheet 2: Monthly Revenue Trend ----
        ws2 = wb.create_sheet("Monthly Trend")
        monthly = data.get("monthly_sales", [])

        ws2.append(["Month", f"Revenue ({currency})", f"Profit ({currency})", "Orders", "Units"])
        for c_idx in range(1, 6):
            header_style(ws2.cell(row=1, column=c_idx), ws2.cell(row=1, column=c_idx).value)

        for i, row_data in enumerate(monthly):
            alt = i % 2 == 0
            ws2.cell(row=i + 2, column=1).value = row_data.get("month", "")
            ws2.cell(row=i + 2, column=2).value = round(row_data.get("revenue", 0), 2)
            ws2.cell(row=i + 2, column=3).value = round(row_data.get("profit", 0), 2)
            ws2.cell(row=i + 2, column=4).value = row_data.get("orders", 0)
            ws2.cell(row=i + 2, column=5).value = row_data.get("units", 0)
            for col in range(1, 6):
                data_cell(ws2.cell(row=i + 2, column=col), ws2.cell(row=i + 2, column=col).value, alt=alt)
                if col in (2, 3):
                    ws2.cell(row=i + 2, column=col).number_format = '#,##0.00'

        set_col_widths(ws2, [18, 20, 20, 12, 12])

        # ---- Sheet 3: Regional Performance ----
        ws3 = wb.create_sheet("Regional Performance")
        regional = data.get("regional_sales", [])

        headers3 = ["Region", f"Revenue ({currency})", f"Profit ({currency})", "Orders", "Units", "Margin %"]
        for c_idx, hdr in enumerate(headers3, 1):
            header_style(ws3.cell(row=1, column=c_idx), hdr)

        for i, row_data in enumerate(regional):
            alt = i % 2 == 0
            vals = [
                row_data.get("region", ""),
                round(row_data.get("revenue", 0), 2),
                round(row_data.get("profit", 0), 2),
                row_data.get("orders", 0),
                row_data.get("units", 0),
                round(row_data.get("margin_pct", 0), 1),
            ]
            for c_idx, val in enumerate(vals, 1):
                cell = ws3.cell(row=i + 2, column=c_idx)
                data_cell(cell, val, alt=alt)
                if c_idx in (2, 3):
                    cell.number_format = '#,##0.00'
                if c_idx == 6:
                    cell.number_format = '0.0"%"'

        set_col_widths(ws3, [22, 20, 20, 12, 12, 14])

        # ---- Sheet 4: Category Performance ----
        ws4 = wb.create_sheet("Category Performance")
        category = data.get("category_sales", [])

        headers4 = ["Category", f"Revenue ({currency})", f"Profit ({currency})", "Orders", "Units", "Margin %"]
        for c_idx, hdr in enumerate(headers4, 1):
            header_style(ws4.cell(row=1, column=c_idx), hdr)

        for i, row_data in enumerate(category):
            alt = i % 2 == 0
            vals = [
                row_data.get("category", ""),
                round(row_data.get("revenue", 0), 2),
                round(row_data.get("profit", 0), 2),
                row_data.get("orders", 0),
                row_data.get("units", 0),
                round(row_data.get("margin_pct", 0), 1),
            ]
            for c_idx, val in enumerate(vals, 1):
                cell = ws4.cell(row=i + 2, column=c_idx)
                data_cell(cell, val, alt=alt)
                if c_idx in (2, 3):
                    cell.number_format = '#,##0.00'

        set_col_widths(ws4, [26, 20, 20, 12, 12, 14])

        # ---- Sheet 5: Top Products ----
        ws5 = wb.create_sheet("Top Products")
        products = data.get("top_products", [])

        headers5 = ["Rank", "Product", f"Revenue ({currency})", f"Profit ({currency})", "Orders", "Units", "Margin %"]
        for c_idx, hdr in enumerate(headers5, 1):
            header_style(ws5.cell(row=1, column=c_idx), hdr)

        for i, row_data in enumerate(products):
            alt = i % 2 == 0
            vals = [
                i + 1,
                row_data.get("product", ""),
                round(row_data.get("revenue", 0), 2),
                round(row_data.get("profit", 0), 2),
                row_data.get("orders", 0),
                row_data.get("units", 0),
                round(row_data.get("margin_pct", 0), 1),
            ]
            for c_idx, val in enumerate(vals, 1):
                cell = ws5.cell(row=i + 2, column=c_idx)
                data_cell(cell, val, alt=alt, bold=(c_idx == 1))
                if c_idx in (3, 4):
                    cell.number_format = '#,##0.00'

        set_col_widths(ws5, [8, 36, 20, 20, 12, 12, 14])

        # ---- Sheet 6: YoY Comparison (if available) ----
        yoy = data.get("yearly_comparison", [])
        if yoy:
            ws6 = wb.create_sheet("YoY Comparison")
            headers6 = ["Month", "2025 Revenue", "2026 Revenue", "2025 Profit", "2026 Profit",
                        "2025 Orders", "2026 Orders"]
            for c_idx, hdr in enumerate(headers6, 1):
                header_style(ws6.cell(row=1, column=c_idx), hdr)

            for i, row_data in enumerate(yoy):
                alt = i % 2 == 0
                vals = [
                    row_data.get("month", ""),
                    round(row_data.get("revenue_2025", 0), 2),
                    round(row_data.get("revenue_2026", 0), 2),
                    round(row_data.get("profit_2025", 0), 2),
                    round(row_data.get("profit_2026", 0), 2),
                    row_data.get("orders_2025", 0),
                    row_data.get("orders_2026", 0),
                ]
                for c_idx, val in enumerate(vals, 1):
                    cell = ws6.cell(row=i + 2, column=c_idx)
                    data_cell(cell, val, alt=alt)
                    if c_idx in (2, 3, 4, 5):
                        cell.number_format = '#,##0.00'

            set_col_widths(ws6, [16, 20, 20, 20, 20, 16, 16])

        # ---- Sheet 7: Recommendations ----
        recs = insights.get("recommendations", [])
        if recs:
            ws7 = wb.create_sheet("Recommendations")
            for c_idx, hdr in enumerate(["#", "Priority", "Recommendation", "Expected Impact"], 1):
                header_style(ws7.cell(row=1, column=c_idx), hdr)

            for i, rec in enumerate(recs):
                alt = i % 2 == 0
                vals = [
                    i + 1,
                    rec.get("importance", rec.get("priority", "Medium")).capitalize(),
                    rec.get("recommendation", rec.get("action", "")),
                    rec.get("expected_impact", rec.get("impact", "")),
                ]
                for c_idx, val in enumerate(vals, 1):
                    cell = ws7.cell(row=i + 2, column=c_idx)
                    data_cell(cell, val, alt=alt)
                    if c_idx in (3, 4):
                        cell.alignment = Alignment(wrap_text=True, vertical="center")
                ws7.row_dimensions[i + 2].height = 36

            set_col_widths(ws7, [6, 14, 55, 40])

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    # ------------------------------------------------------------------ PDF
    def generate_pdf(self, project_id: str) -> bytes:
        """Generate a styled PDF business intelligence report."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, PageBreak
        )

        data = self._get_dashboard_data(project_id)
        insights = self._get_insights_data(project_id)
        kpi_list = data.get("kpis", [])
        kpi_map = {k.get("id"): k for k in kpi_list if isinstance(k, dict)}
        currency = data.get("currency_symbol", "$")
        now = datetime.now().strftime("%d %B %Y, %H:%M")

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=2 * cm,
        )

        # Colour palette
        C_DARK = colors.HexColor("#1E293B")
        C_MID = colors.HexColor("#334155")
        C_BLUE = colors.HexColor("#3B82F6")
        C_LIGHT = colors.HexColor("#F1F5F9")
        C_WHITE = colors.white
        C_BORDER = colors.HexColor("#CBD5E1")

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=22,
                                     textColor=C_DARK, spaceAfter=4, fontName="Helvetica-Bold")
        h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=14, textColor=C_DARK,
                              fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)
        h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11, textColor=C_MID,
                              fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4)
        body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9, textColor=C_DARK,
                               leading=14, spaceAfter=4)
        small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, textColor=C_MID)

        def tbl_style(has_header=True):
            base = [
                ("BACKGROUND", (0, 0), (-1, 0), C_DARK if has_header else C_LIGHT),
                ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE if has_header else C_DARK),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 1), (0, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
            return TableStyle(base)

        story: list[Any] = []

        # --- Title Page ---
        story.append(Paragraph("NEXUS AI Enterprise Intelligence", title_style))
        story.append(Paragraph("Business Intelligence Report", ParagraphStyle(
            "sub", parent=styles["Normal"], fontSize=14, textColor=C_BLUE,
            fontName="Helvetica-Bold", spaceAfter=2)))
        story.append(Paragraph(f"Generated: {now}", small))
        story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceAfter=14))

        # --- Executive KPIs ---
        story.append(Paragraph("Executive KPI Summary", h1))
        domain = data.get("domain", "general")

        if domain == "healthcare":
            kpi_data = [
                ["KPI", "Value", "Description"],
                ["Billed Revenue", kpi_map.get("billed", {}).get("formatted", "N/A"), "Total gross clinical billings"],
                ["Collections (Paid)", kpi_map.get("paid", {}).get("formatted", "N/A"), "Realized collections"],
                ["Outstanding Balance", kpi_map.get("outstanding", {}).get("formatted", "N/A"), "Pending receivables"],
                ["Total Encounters", kpi_map.get("encounters", {}).get("formatted", "N/A"), "Completed clinical encounters"],
                ["Unique Patients", kpi_map.get("patients", {}).get("formatted", "N/A"), "Individual patients served"],
            ]
        elif domain == "retail":
            rev_kpi = kpi_map.get("revenue", {})
            pft_kpi = kpi_map.get("profit", {})
            ord_kpi = kpi_map.get("orders", {})
            qty_kpi = kpi_map.get("quantity", {})
            aov_kpi = kpi_map.get("aov", {})

            kpi_data = [
                ["KPI", "Value", "Description"],
                ["Total Revenue", rev_kpi.get("formatted", "N/A"), rev_kpi.get("subtext", "Completed revenue")],
                ["Total Profit", pft_kpi.get("formatted", "N/A"), pft_kpi.get("subtext", "Net profit")],
                ["Total Orders", ord_kpi.get("formatted", "N/A"), ord_kpi.get("subtext", "Completed orders")],
                ["Units Sold", qty_kpi.get("formatted", "N/A"), qty_kpi.get("subtext", "Total units sold")],
                ["Avg Order Value", aov_kpi.get("formatted", "N/A"), aov_kpi.get("subtext", "Average order value")],
            ]
        else:
            kpi_data = [["KPI", "Value", "Description"]]
            for k in kpi_list:
                if isinstance(k, dict):
                    kpi_data.append([
                        k.get("label", k.get("id", "Metric")),
                        k.get("formatted", str(k.get("value", "N/A"))),
                        k.get("subtext", "")
                    ])
            if len(kpi_data) == 1:
                kpi_data.append(["Status", "No structured metrics", "Upload tabular data to compute KPIs"])

        kpi_tbl = Table(kpi_data, colWidths=[5 * cm, 5 * cm, 8 * cm])
        kpi_tbl.setStyle(tbl_style())
        story.append(kpi_tbl)
        story.append(Spacer(1, 0.3 * cm))

        # --- Monthly Trend ---
        monthly = data.get("monthly_sales", [])
        if monthly:
            story.append(Paragraph("Monthly Revenue & Profit Trend", h1))
            m_data = [[
                "Month", f"Revenue ({currency})", f"Profit ({currency})", "Orders", "Units"
            ]]
            for r in monthly:
                m_data.append([
                    r.get("month", ""),
                    f"{r.get('revenue', 0):,.0f}",
                    f"{r.get('profit', 0):,.0f}",
                    f"{r.get('orders', 0):,}",
                    f"{r.get('units', 0):,}",
                ])
            m_tbl = Table(m_data, colWidths=[4 * cm, 5 * cm, 5 * cm, 3 * cm, 3 * cm])
            m_tbl.setStyle(tbl_style())
            story.append(m_tbl)
            story.append(Spacer(1, 0.3 * cm))

        # --- Regional Performance ---
        regional = data.get("regional_sales", [])
        if regional:
            story.append(Paragraph("Geographic Performance", h1))
            reg_data = [[
                "Region", f"Revenue ({currency})", f"Profit ({currency})", "Orders", "Units", "Margin"
            ]]
            for r in regional:
                reg_data.append([
                    r.get("region", ""),
                    f"{r.get('revenue', 0):,.0f}",
                    f"{r.get('profit', 0):,.0f}",
                    f"{r.get('orders', 0):,}",
                    f"{r.get('units', 0):,}",
                    f"{r.get('margin_pct', 0):.1f}%",
                ])
            reg_tbl = Table(reg_data, colWidths=[4 * cm, 4.5 * cm, 4.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm])
            reg_tbl.setStyle(tbl_style())
            story.append(reg_tbl)
            story.append(Spacer(1, 0.3 * cm))

        # --- Category Performance ---
        category = data.get("category_sales", [])
        if category:
            story.append(Paragraph("Category-Wise Performance", h1))
            cat_data = [[
                "Category", f"Revenue ({currency})", f"Profit ({currency})", "Orders", "Margin"
            ]]
            for r in category:
                cat_data.append([
                    r.get("category", ""),
                    f"{r.get('revenue', 0):,.0f}",
                    f"{r.get('profit', 0):,.0f}",
                    f"{r.get('orders', 0):,}",
                    f"{r.get('margin_pct', 0):.1f}%",
                ])
            cat_tbl = Table(cat_data, colWidths=[5.5 * cm, 4.5 * cm, 4.5 * cm, 3 * cm, 3 * cm])
            cat_tbl.setStyle(tbl_style())
            story.append(cat_tbl)
            story.append(Spacer(1, 0.3 * cm))

        # --- Top Products ---
        products = data.get("top_products", [])
        if products:
            story.append(Paragraph("Top Performing Products", h1))
            prod_data = [[
                "#", "Product", f"Revenue ({currency})", f"Profit ({currency})", "Orders", "Margin"
            ]]
            for i, r in enumerate(products):
                prod_data.append([
                    str(i + 1),
                    r.get("product", ""),
                    f"{r.get('revenue', 0):,.0f}",
                    f"{r.get('profit', 0):,.0f}",
                    f"{r.get('orders', 0):,}",
                    f"{r.get('margin_pct', 0):.1f}%",
                ])
            prod_tbl = Table(prod_data, colWidths=[1 * cm, 6 * cm, 4 * cm, 4 * cm, 2.5 * cm, 3 * cm])
            prod_tbl.setStyle(tbl_style())
            story.append(prod_tbl)
            story.append(Spacer(1, 0.3 * cm))

        # --- Strategic Insights & Recommendations ---
        findings = insights.get("insights", []) or insights.get("findings", [])
        recs = insights.get("recommendations", [])

        if findings:
            story.append(PageBreak())
            story.append(Paragraph("Strategic Findings", h1))
            for f_item in findings[:8]:
                f_title = f_item.get("title", "")
                f_detail = f_item.get("description", f_item.get("detail", ""))
                story.append(Paragraph(
                    f"<b>{f_title}</b> — {f_detail}", body
                ))

        if recs:
            story.append(Paragraph("Recommended Actions", h1))
            rec_data = [["#", "Priority", "Recommendation", "Expected Impact"]]
            for i, r in enumerate(recs):
                r_prio = r.get("importance", r.get("priority", "Medium")).capitalize()
                r_action = r.get("recommendation", r.get("action", ""))
                r_impact = r.get("expected_impact", r.get("impact", ""))
                rec_data.append([
                    str(i + 1),
                    r_prio,
                    Paragraph(r_action, small),
                    Paragraph(r_impact, small),
                ])
            rec_tbl = Table(rec_data, colWidths=[1 * cm, 2.5 * cm, 8 * cm, 9 * cm])
            rec_tbl.setStyle(tbl_style())
            story.append(rec_tbl)

        # Footer note
        story.append(Spacer(1, 0.5 * cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
        story.append(Paragraph(
            "Report generated by NEXUS AI Enterprise Platform — All calculations derived from actual DuckDB data. "
            "No fabricated results.", small
        ))

        doc.build(story)
        return buf.getvalue()


report_service = ReportService()
