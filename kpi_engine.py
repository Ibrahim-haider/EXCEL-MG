"""
Computes department KPIs from a cleaned DataFrame and returns a list of
(kpi_code, value_numeric, value_text) tuples ready to persist as KPISnapshots.

Add one function per department and register it in KPI_FUNCTIONS.
"""
from datetime import date
import pandas as pd


def _sales_kpis(df: pd.DataFrame) -> list:
    revenue_mtd = float(df["revenue"].sum())
    units_sold = int(df["units"].sum())
    dealers = df["dealer_name"].nunique() if "dealer_name" in df.columns else None
    top_dealer = None
    if "dealer_name" in df.columns:
        by_dealer = df.groupby("dealer_name")["revenue"].sum().sort_values(ascending=False)
        if len(by_dealer):
            top_dealer = by_dealer.index[0]

    kpis = [
        ("revenue_mtd", revenue_mtd, None),
        ("units_sold", units_sold, None),
    ]
    if top_dealer:
        kpis.append(("top_dealer", None, top_dealer))
    if dealers:
        kpis.append(("active_dealers", dealers, None))
    return kpis


def _inventory_kpis(df: pd.DataFrame) -> list:
    inventory_value = float((df["quantity"] * df["unit_value"]).sum())
    dead_stock = float(df.loc[df["status"].str.lower() == "dead", "unit_value"].sum()) \
        if "status" in df.columns else 0.0
    return [
        ("inventory_value", inventory_value, None),
        ("dead_stock_value", dead_stock, None),
    ]


def _finance_kpis(df: pd.DataFrame) -> list:
    budget = float(df["budget"].sum())
    actual = float(df["actual"].sum())
    variance_pct = round(((actual - budget) / budget) * 100, 2) if budget else 0.0
    return [
        ("total_budget", budget, None),
        ("total_actual", actual, None),
        ("variance_pct", variance_pct, None),
    ]


def _marketing_kpis(df: pd.DataFrame) -> list:
    spend = float(df["spend"].sum())
    leads = int(df["leads"].sum())
    cost_per_lead = round(spend / leads, 2) if leads else 0.0
    return [
        ("total_spend", spend, None),
        ("total_leads", leads, None),
        ("cost_per_lead", cost_per_lead, None),
    ]


def _hr_kpis(df: pd.DataFrame) -> list:
    headcount = int(len(df))
    active = int((df["status"].str.lower() == "active").sum()) if "status" in df.columns else headcount
    return [
        ("headcount", headcount, None),
        ("active_employees", active, None),
    ]


def _aftersales_kpis(df: pd.DataFrame) -> list:
    open_claims = int((df["claim_status"].str.lower() == "open").sum()) if "claim_status" in df.columns else 0
    closed_claims = int((df["claim_status"].str.lower() == "closed").sum()) if "claim_status" in df.columns else 0
    return [
        ("open_warranty_claims", open_claims, None),
        ("closed_warranty_claims", closed_claims, None),
    ]


KPI_FUNCTIONS = {
    "sales": _sales_kpis,
    "inventory": _inventory_kpis,
    "finance": _finance_kpis,
    "marketing": _marketing_kpis,
    "hr": _hr_kpis,
    "aftersales": _aftersales_kpis,
}


def compute_kpis(department_code: str, df: pd.DataFrame) -> list:
    fn = KPI_FUNCTIONS.get(department_code)
    if not fn:
        return []
    return fn(df)
