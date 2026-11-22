import re
from typing import Any

class DomainService:
    HEALTHCARE_INDICATORS = {
        "encounter_id", "patient_id", "diagnosis", "diagnosis_code", "department",
        "facility", "provider_id", "visit_type", "encounter_status",
        "billed_amount", "billed_amount_inr", "paid_amount", "paid_amount_inr",
        "outstanding_amount", "outstanding_amount_inr", "wait_time_minutes",
        "length_of_stay_days", "lab_result_id", "test_name", "result_value",
        "result_flag", "demo_reference_low", "demo_reference_high"
    }

    RETAIL_INDICATORS = {
        "order_id", "sales_order_id", "product", "product_id", "category",
        "quantity", "quantity_sold", "units_sold", "net_revenue", "net_revenue_inr",
        "gross_sales", "gross_sales_inr", "profit", "profit_inr", "gross_profit_inr",
        "cogs", "cogs_inr", "discount_amount", "sales_channel", "inventory",
        "stock", "opening_stock", "closing_stock"
    }

    def detect_domain(self, schema: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        """
        Analyze all table columns across the active project to determine
        the actual business domain, primary entities, measures, and dimensions.
        """
        all_cols_set: set[str] = set()
        col_to_table: dict[str, list[str]] = {}

        for tbl, cols in schema.items():
            for c in cols:
                c_low = c["name"].lower()
                all_cols_set.add(c_low)
                col_to_table.setdefault(c_low, []).append(tbl)

        # Count matches
        hc_score = sum(1 for ind in self.HEALTHCARE_INDICATORS if any(ind in c for c in all_cols_set))
        retail_score = sum(1 for ind in self.RETAIL_INDICATORS if any(ind in c for c in all_cols_set))

        # Currency detection
        currency_sym = "$"
        all_cols_str = " ".join(all_cols_set)
        if "inr" in all_cols_str or "rupee" in all_cols_str:
            currency_sym = "₹"
        elif "eur" in all_cols_str:
            currency_sym = "€"
        elif "gbp" in all_cols_str:
            currency_sym = "£"

        if hc_score >= 4 and hc_score > retail_score:
            domain = "healthcare"
            domain_label = "Healthcare & Clinical Intelligence"
        elif retail_score >= 3:
            domain = "retail"
            domain_label = "Retail & E-Commerce Analytics"
        else:
            domain = "general"
            domain_label = "General Business Intelligence"

        # Identify multipart / chunked tables (e.g. *_part_1, *_part_2)
        table_groups: dict[str, list[str]] = {}
        for tbl in schema.keys():
            base_match = re.sub(r'(_part_\d+|_chunk_\d+).*$', '', tbl, flags=re.IGNORECASE)
            table_groups.setdefault(base_match, []).append(tbl)

        return {
            "domain": domain,
            "domain_label": domain_label,
            "currency_symbol": currency_sym,
            "hc_score": hc_score,
            "retail_score": retail_score,
            "columns": list(all_cols_set),
            "table_groups": table_groups
        }

domain_service = DomainService()
