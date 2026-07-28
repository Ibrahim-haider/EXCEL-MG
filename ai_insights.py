"""
Generates natural-language insights over a department's latest KPIs.

If ANTHROPIC_API_KEY is set, questions are answered by Claude with the
KPI snapshot injected as context. Otherwise, falls back to simple
keyword matching so the demo still works with zero external dependencies.
"""
import os
from typing import List, Dict


def _get_api_key():
    try:
        import streamlit as st
        if "ANTHROPIC_API_KEY" in st.secrets:
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    return os.getenv("ANTHROPIC_API_KEY")


def _rule_based_answer(question: str, kpis: List[Dict]) -> str:
    q = question.lower()
    kpi_map = {k["code"]: k for k in kpis}

    if "revenue" in q and "revenue_mtd" in kpi_map:
        v = kpi_map["revenue_mtd"]["value"]
        return f"Revenue for the current period is PKR {v:,.0f}."
    if "dealer" in q and "top_dealer" in kpi_map:
        return f"The top-performing dealer right now is {kpi_map['top_dealer']['value_text']}."
    if "claim" in q and "open_warranty_claims" in kpi_map:
        v = kpi_map["open_warranty_claims"]["value"]
        return f"There are currently {int(v)} open warranty claims."
    if "stock" in q or "dead stock" in q:
        v = kpi_map.get("dead_stock_value", {}).get("value")
        if v is not None:
            return f"Dead stock is currently valued at PKR {v:,.0f}."

    return ("I don't have a specific figure for that in the latest upload yet — "
            "try asking about revenue, top dealers, warranty claims, or stock value.")


def _claude_answer(question: str, kpis: List[Dict], department: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=_get_api_key())
    kpi_summary = "\n".join(
        f"- {k['name']}: {k['value'] if k['value'] is not None else k['value_text']} {k.get('unit') or ''}"
        for k in kpis
    )
    prompt = (
        f"You are an analytics assistant for the {department} department of an "
        f"automotive company in Pakistan. Answer the question below using ONLY "
        f"the KPI data provided. Be concise (1-2 sentences), and don't invent numbers "
        f"that aren't in the data.\n\nKPI DATA:\n{kpi_summary}\n\nQUESTION: {question}"
    )
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")


def answer_question(question: str, department: str, kpis: List[Dict]) -> tuple[str, str]:
    """Returns (answer_text, source) where source is 'claude' or 'rule_based'."""
    if _get_api_key():
        try:
            return _claude_answer(question, kpis, department), "claude"
        except Exception:
            pass  # fall through to rule-based
    return _rule_based_answer(question, kpis), "rule_based"
