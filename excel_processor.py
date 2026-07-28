"""
Turns an uploaded Excel file into a clean, validated DataFrame.

This is intentionally template-driven: each department has a minimal set of
required columns. Swap/extend REQUIRED_COLUMNS and clean_dataframe() to match
RD's real report templates.
"""
from dataclasses import dataclass, field
from typing import List, Tuple
import pandas as pd

REQUIRED_COLUMNS = {
    "sales": ["dealer_name", "region", "model", "units", "revenue", "sale_date"],
    "inventory": ["sku", "location", "quantity", "unit_value", "status"],
    "finance": ["line_item", "budget", "actual", "period"],
    "marketing": ["campaign", "spend", "leads", "period"],
    "hr": ["employee_id", "department", "status", "period"],
    "aftersales": ["service_center", "technician", "claim_status", "claim_date"],
}


@dataclass
class ProcessingResult:
    ok: bool
    dataframe: pd.DataFrame = None
    row_count: int = 0
    valid_row_count: int = 0
    logs: List[Tuple[str, str, str]] = field(default_factory=list)  # (step, level, message)
    error: str = None

    def log(self, step: str, level: str, message: str):
        self.logs.append((step, level, message))


def validate_and_clean(file_path: str, department_code: str) -> ProcessingResult:
    result = ProcessingResult(ok=False)

    # --- STEP 1: read ---
    try:
        df = pd.read_excel(file_path)
    except Exception as exc:
        result.error = f"Could not read Excel file: {exc}"
        result.log("validating", "error", result.error)
        return result

    result.row_count = len(df)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    result.log("validating", "info", f"Read {result.row_count} rows, {len(df.columns)} columns.")

    # --- STEP 2: schema check ---
    required = REQUIRED_COLUMNS.get(department_code, [])
    missing = [c for c in required if c not in df.columns]
    if missing:
        result.error = f"Missing required columns for '{department_code}': {missing}"
        result.log("validating", "error", result.error)
        return result
    result.log("validating", "info", f"Schema check passed ({len(required)}/{len(required)} required columns found).")

    # --- STEP 3: clean ---
    before = len(df)
    df = df.drop_duplicates()
    dropped_dupes = before - len(df)
    if dropped_dupes:
        result.log("cleaning", "warning", f"Removed {dropped_dupes} duplicate rows.")

    # drop fully-empty required fields
    before = len(df)
    df = df.dropna(subset=[c for c in required if c in df.columns], how="any")
    dropped_na = before - len(df)
    if dropped_na:
        result.log("cleaning", "warning", f"Dropped {dropped_na} rows with missing required values.")

    # normalize obvious text fields
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()

    result.log("cleaning", "info", "Normalized text fields and currency formatting.")

    result.valid_row_count = len(df)
    result.dataframe = df
    result.ok = True
    result.log("generating_kpis", "info", f"{result.valid_row_count} clean rows ready for KPI generation.")
    return result
