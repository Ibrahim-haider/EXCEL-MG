"""
Builds chart-ready breakdowns from a department's cleaned row-level data.

Each function returns a list of ChartSpec — a title, a chart kind ('bar' or
'line'), and a pandas Series/DataFrame already shaped for st.bar_chart /
st.line_chart (index = x-axis categories, values = y-axis).
"""
from dataclasses import dataclass
from typing import List, Union

import pandas as pd


@dataclass
class ChartSpec:
    title: str
    kind: str  # 'bar' or 'line'
    data: Union[pd.Series, pd.DataFrame]


def _top_n(series: pd.Series, n: int = 10) -> pd.Series:
    return series.sort_values(ascending=False).head(n)


def _sales_charts(df: pd.DataFrame) -> List[ChartSpec]:
    charts = []

    if "dealer_name" in df.columns and "revenue" in df.columns:
        by_dealer = df.groupby("dealer_name")["revenue"].sum()
        charts.append(ChartSpec("Revenue by Dealer (Top 10)", "bar", _top_n(by_dealer)))

    if "model" in df.columns and "units" in df.columns:
        by_model = df.groupby("model")["units"].sum().sort_values(ascending=False)
        charts.append(ChartSpec("Units Sold by Model", "bar", by_model))

    if "sale_date" in df.columns and "revenue" in df.columns:
        dates = pd.to_datetime(df["sale_date"], errors="coerce")
        trend = df.assign(_date=dates).dropna(subset=["_date"]).groupby("_date")["revenue"].sum().sort_index()
        if len(trend):
            charts.append(ChartSpec("Revenue Trend", "line", trend))

    if "region" in df.columns and "revenue" in df.columns:
        by_region = df.groupby("region")["revenue"].sum().sort_values(ascending=False)
        charts.append(ChartSpec("Revenue by Region", "bar", by_region))

    return charts


def _inventory_charts(df: pd.DataFrame) -> List[ChartSpec]:
    charts = []
    if "location" in df.columns and {"quantity", "unit_value"}.issubset(df.columns):
        value = (df["quantity"] * df["unit_value"])
        by_location = df.assign(_value=value).groupby("location")["_value"].sum().sort_values(ascending=False)
        charts.append(ChartSpec("Inventory Value by Location", "bar", _top_n(by_location)))

    if "status" in df.columns and {"quantity", "unit_value"}.issubset(df.columns):
        value = (df["quantity"] * df["unit_value"])
        by_status = df.assign(_value=value).groupby("status")["_value"].sum().sort_values(ascending=False)
        charts.append(ChartSpec("Inventory Value by Status", "bar", by_status))
    return charts


def _finance_charts(df: pd.DataFrame) -> List[ChartSpec]:
    charts = []
    if "line_item" in df.columns and {"budget", "actual"}.issubset(df.columns):
        by_item = df.groupby("line_item")[["budget", "actual"]].sum().sort_values("budget", ascending=False)
        charts.append(ChartSpec("Budget vs Actual by Line Item", "bar", _top_n_df(by_item, "budget")))
    return charts


def _top_n_df(df: pd.DataFrame, sort_col: str, n: int = 10) -> pd.DataFrame:
    return df.sort_values(sort_col, ascending=False).head(n)


def _marketing_charts(df: pd.DataFrame) -> List[ChartSpec]:
    charts = []
    if "campaign" in df.columns and "spend" in df.columns:
        by_campaign = df.groupby("campaign")["spend"].sum().sort_values(ascending=False)
        charts.append(ChartSpec("Spend by Campaign (Top 10)", "bar", _top_n(by_campaign)))
    if "campaign" in df.columns and "leads" in df.columns:
        by_campaign_leads = df.groupby("campaign")["leads"].sum().sort_values(ascending=False)
        charts.append(ChartSpec("Leads by Campaign (Top 10)", "bar", _top_n(by_campaign_leads)))
    return charts


def _hr_charts(df: pd.DataFrame) -> List[ChartSpec]:
    charts = []
    if "department" in df.columns:
        by_dept = df.groupby("department").size().sort_values(ascending=False)
        charts.append(ChartSpec("Headcount by Department", "bar", by_dept))
    if "status" in df.columns:
        by_status = df.groupby("status").size().sort_values(ascending=False)
        charts.append(ChartSpec("Employees by Status", "bar", by_status))
    return charts


def _aftersales_charts(df: pd.DataFrame) -> List[ChartSpec]:
    charts = []
    if "service_center" in df.columns and "claim_status" in df.columns:
        pivot = df.groupby(["service_center", "claim_status"]).size().unstack(fill_value=0)
        charts.append(ChartSpec("Claims by Service Center", "bar", pivot))
    return charts


CHART_FUNCTIONS = {
    "sales": _sales_charts,
    "inventory": _inventory_charts,
    "finance": _finance_charts,
    "marketing": _marketing_charts,
    "hr": _hr_charts,
    "aftersales": _aftersales_charts,
}


def build_charts(department_code: str, df: pd.DataFrame) -> List[ChartSpec]:
    fn = CHART_FUNCTIONS.get(department_code)
    if not fn or df is None or df.empty:
        return []
    try:
        return fn(df)
    except Exception:
        return []
