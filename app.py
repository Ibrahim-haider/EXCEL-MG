"""
MG Pakistan — Enterprise Analytics Portal (Streamlit build)

Single-file Streamlit app that reuses the same DB models and pipeline
services (Excel ingestion, KPI engine, AI insights) as the original
FastAPI prototype, but replaces the API/JWT/HTML layer with native
Streamlit UI and session-based auth.

Run locally:
    pip install -r requirements.txt
    streamlit run app.py

Demo logins (password: password123):
    admin@rd-electronics.pk    (admin)
    sales@rd-electronics.pk    (manager, sales dept)
    finance@rd-electronics.pk  (analyst, finance dept)
"""
import io
from datetime import date, datetime
from uuid import uuid4

import pandas as pd
import streamlit as st
from sqlalchemy import func

import models
from database import Base, engine, get_db
from auth import verify_password
from seed import run_seed
from services.excel_processor import validate_and_clean, REQUIRED_COLUMNS
from services.kpi_engine import compute_kpis
from services.ai_insights import answer_question
from services.chart_engine import build_charts

st.set_page_config(page_title="MG Analytics Portal", page_icon="📊", layout="wide")


# ---------------------------------------------------------------- startup --
@st.cache_resource
def init_db():
    Base.metadata.create_all(bind=engine)
    db = get_db()
    try:
        run_seed(db)
    finally:
        db.close()
    return True


init_db()


# ------------------------------------------------------------------ auth --
def do_login(email: str, password: str):
    db = get_db()
    try:
        user = db.query(models.User).filter(models.User.email == email.strip().lower()).first()
        if not user or not verify_password(password, user.password_hash):
            return False
        user.last_login_at = datetime.utcnow()
        db.commit()
        st.session_state.user = {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role_code": user.role.code,
            "can_upload": user.role.can_upload,
            "can_export": user.role.can_export,
            "can_manage_users": user.role.can_manage_users,
            "department_code": user.department.code if user.department else None,
            "department_id": user.department_id,
        }
        return True
    finally:
        db.close()


def render_login():
    st.title("📊 MG Pakistan — Enterprise Analytics Portal")
    st.caption("Prototype pilot build — Streamlit edition")
    col, _ = st.columns([1, 1])
    with col:
        with st.form("login_form"):
            email = st.text_input("Email", value="admin@rd-electronics.pk")
            password = st.text_input("Password", type="password", value="password123")
            submitted = st.form_submit_button("Log in", use_container_width=True)
        if submitted:
            if do_login(email, password):
                st.rerun()
            else:
                st.error("Incorrect email or password.")

        with st.expander("Demo logins (password: password123)"):
            st.markdown(
                "- `admin@rd-electronics.pk` — Administrator\n"
                "- `sales@rd-electronics.pk` — Sales Manager\n"
                "- `finance@rd-electronics.pk` — Finance Analyst"
            )


# -------------------------------------------------------------- dashboard --
def get_latest_clean_data(db, department_id: int) -> pd.DataFrame:
    """Loads the row-level cleaned data from the most recent published upload."""
    upload = (
        db.query(models.Upload)
        .filter(models.Upload.department_id == department_id)
        .filter(models.Upload.status == "published")
        .filter(models.Upload.clean_data_path.isnot(None))
        .order_by(models.Upload.processed_at.desc())
        .first()
    )
    if not upload:
        return None
    try:
        return pd.read_csv(upload.clean_data_path)
    except Exception:
        return None


def get_dashboard(db, department_code: str):
    department = db.query(models.Department).filter(models.Department.code == department_code).first()
    if not department:
        return None, []

    subq = (
        db.query(
            models.KPISnapshot.kpi_code,
            func.max(models.KPISnapshot.created_at).label("latest"),
        )
        .filter(models.KPISnapshot.department_id == department.id)
        .group_by(models.KPISnapshot.kpi_code)
        .subquery()
    )
    rows = (
        db.query(models.KPISnapshot)
        .join(subq, (models.KPISnapshot.kpi_code == subq.c.kpi_code) &
              (models.KPISnapshot.created_at == subq.c.latest))
        .filter(models.KPISnapshot.department_id == department.id)
        .all()
    )
    defs = {
        d.code: d for d in
        db.query(models.KPIDefinition).filter(models.KPIDefinition.department_id == department.id).all()
    }
    kpis = [
        {
            "code": r.kpi_code,
            "name": defs[r.kpi_code].name if r.kpi_code in defs else r.kpi_code.replace("_", " ").title(),
            "unit": defs[r.kpi_code].unit if r.kpi_code in defs else None,
            "value": float(r.value_numeric) if r.value_numeric is not None else None,
            "value_text": r.value_text,
            "period_end": str(r.period_end),
        }
        for r in rows
    ]
    return department, kpis


def render_dashboard(db, department_code: str):
    department, kpis = get_dashboard(db, department_code)
    if not department:
        st.warning(f"Unknown department '{department_code}'.")
        return

    st.subheader(f"{department.name} — Dashboard")
    if not kpis:
        st.info("No KPIs published yet. Upload a report in the **Upload Data** tab to generate them.")
        return

    cols = st.columns(min(4, len(kpis)) or 1)
    for i, k in enumerate(kpis):
        with cols[i % len(cols)]:
            if k["value"] is not None:
                display = f"{k['value']:,.2f}" if k["unit"] not in ("count", "%") else (
                    f"{k['value']:,.0f}" if k["unit"] == "count" else f"{k['value']:.2f}%"
                )
                st.metric(k["name"], f"{display}" + (f" {k['unit']}" if k["unit"] and k["unit"] not in ("count", "%") else ""))
            else:
                st.metric(k["name"], k["value_text"] or "—")
    st.caption(f"As of {kpis[0]['period_end']}")

    clean_df = get_latest_clean_data(db, department.id)
    chart_specs = build_charts(department_code, clean_df) if clean_df is not None else []
    if chart_specs:
        st.divider()
        st.subheader("Charts")
        for i in range(0, len(chart_specs), 2):
            row = chart_specs[i:i + 2]
            cols = st.columns(len(row))
            for col, spec in zip(cols, row):
                with col:
                    st.caption(spec.title)
                    if spec.kind == "line":
                        st.line_chart(spec.data)
                    else:
                        st.bar_chart(spec.data)

        with st.expander("View raw data"):
            st.dataframe(clean_df, use_container_width=True)


# ------------------------------------------------------------------ upload --
def render_upload(db, department_code: str, user_id: str):
    st.subheader("Upload Data")
    st.caption(
        f"Required columns for **{department_code}**: "
        + ", ".join(REQUIRED_COLUMNS.get(department_code, []))
    )
    file = st.file_uploader("Excel file (.xlsx)", type=["xlsx", "xls"])
    if file is None:
        return

    if st.button("Run upload pipeline", type="primary"):
        department = db.query(models.Department).filter(models.Department.code == department_code).first()
        if not department:
            st.error(f"Unknown department '{department_code}'")
            return

        # 1. save to disk
        safe_name = f"{uuid4().hex}_{file.name}"
        stored_path = f"./storage/uploads/{safe_name}"
        with open(stored_path, "wb") as out:
            out.write(file.getbuffer())

        upload = models.Upload(
            department_id=department.id,
            uploaded_by=user_id,
            original_filename=file.name,
            stored_path=stored_path,
            status="uploaded",
        )
        db.add(upload)
        db.commit()
        db.refresh(upload)

        log_box = st.container(border=True)

        def _log(step, level, message):
            db.add(models.UploadPipelineLog(upload_id=upload.id, step=step, level=level, message=message))
            db.commit()
            icon = {"info": "ℹ️", "warning": "⚠️", "error": "❌"}.get(level, "ℹ️")
            log_box.write(f"{icon} **{step}** — {message}")

        _log("uploading", "info", f"Received file: {file.name}")

        # 2. validate + clean
        upload.status = "validating"
        db.commit()
        with st.spinner("Validating and cleaning..."):
            result = validate_and_clean(stored_path, department_code)
        for step, level, message in result.logs:
            _log(step, level, message)

        if not result.ok:
            upload.status = "failed"
            upload.error_message = result.error
            db.commit()
            st.error(f"Upload failed: {result.error}")
            return

        upload.row_count = result.row_count
        upload.valid_row_count = result.valid_row_count
        upload.status = "generating_kpis"

        clean_path = f"./storage/uploads/{upload.id}_clean.csv"
        result.dataframe.to_csv(clean_path, index=False)
        upload.clean_data_path = clean_path
        db.commit()

        # 3. compute + persist KPIs
        with st.spinner("Generating KPIs..."):
            kpi_rows = compute_kpis(department_code, result.dataframe)
        today = date.today()
        for code, value_numeric, value_text in kpi_rows:
            db.add(models.KPISnapshot(
                upload_id=upload.id,
                department_id=department.id,
                kpi_code=code,
                value_numeric=value_numeric,
                value_text=value_text,
                period_start=today.replace(day=1),
                period_end=today,
            ))
        _log("generating_kpis", "info", f"Published {len(kpi_rows)} KPIs.")

        # 4. publish
        upload.status = "published"
        upload.processed_at = datetime.utcnow()
        db.commit()

        st.success(
            f"Upload published: {result.valid_row_count}/{result.row_count} valid rows, "
            f"{len(kpi_rows)} KPIs updated."
        )
        st.cache_data.clear()


# --------------------------------------------------------------- ai insights --
def render_ai(db, department_code: str):
    st.subheader("Ask about your data")
    _, kpis = get_dashboard(db, department_code)
    if not kpis:
        st.info("No KPIs published yet for this department.")
        return

    question = st.text_input("Question", placeholder="e.g. who is our top dealer?")
    if st.button("Ask") and question:
        with st.spinner("Thinking..."):
            answer, source = answer_question(question, department_code, kpis)
        department = db.query(models.Department).filter(models.Department.code == department_code).first()
        db.add(models.AIInsight(department_id=department.id, insight_text=answer, category="qa"))
        db.commit()
        st.markdown(f"**Answer** ({'Claude' if source == 'claude' else 'rule-based fallback'}):")
        st.write(answer)

    st.divider()
    st.caption("Try: revenue, top dealer, warranty claims, dead stock value.")


# ------------------------------------------------------------------ reports --
def _build_pdf(title: str, kpis) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, title)
    c.setFont("Helvetica", 11)
    y = 760
    for k in kpis:
        value = k["value"] if k["value"] is not None else k["value_text"]
        c.drawString(50, y, f"{k['name']}: {value} {k['unit'] or ''}")
        y -= 20
    c.save()
    return buf.getvalue()


def _build_xlsx(title: str, kpis) -> bytes:
    from openpyxl import Workbook

    buf = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = (title[:31] or "Report")
    ws.append(["KPI", "Value", "Unit", "Period"])
    for k in kpis:
        ws.append([k["name"], k["value"] if k["value"] is not None else k["value_text"], k["unit"], k["period_end"]])
    wb.save(buf)
    return buf.getvalue()


def render_reports(db, department_code: str):
    st.subheader("Generate Report")
    report_name = st.text_input("Report name", value=f"{department_code}_report")
    fmt = st.radio("Format", ["pdf", "xlsx"], horizontal=True)
    if st.button("Generate", type="primary"):
        _, kpis = get_dashboard(db, department_code)
        data = _build_pdf(report_name, kpis) if fmt == "pdf" else _build_xlsx(report_name, kpis)
        mime = "application/pdf" if fmt == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        st.download_button(
            f"Download {fmt.upper()}",
            data=data,
            file_name=f"{report_name}.{fmt}",
            mime=mime,
        )


# -------------------------------------------------------------------- main --
def render_app():
    user = st.session_state.user
    db = get_db()
    try:
        all_depts = [d.code for d in db.query(models.Department).order_by(models.Department.name).all()]

        with st.sidebar:
            st.markdown(f"**{user['full_name']}**")
            st.caption(f"{user['role_code'].title()}" + (f" · {user['department_code']}" if user['department_code'] else ""))

            if user["role_code"] == "admin":
                department_code = st.selectbox("Department", all_depts, index=all_depts.index("sales") if "sales" in all_depts else 0)
            else:
                department_code = user["department_code"] or (all_depts[0] if all_depts else None)
                st.text(f"Department: {department_code}")

            pages = ["Dashboard"]
            if user["can_upload"]:
                pages.append("Upload Data")
            pages += ["AI Insights"]
            if user["can_export"]:
                pages.append("Reports")
            page = st.radio("Navigate", pages)

            st.divider()
            if st.button("Log out", use_container_width=True):
                del st.session_state.user
                st.rerun()

        if not department_code:
            st.warning("No departments configured yet.")
            return

        if page == "Dashboard":
            render_dashboard(db, department_code)
        elif page == "Upload Data":
            render_upload(db, department_code, user["id"])
        elif page == "AI Insights":
            render_ai(db, department_code)
        elif page == "Reports":
            render_reports(db, department_code)
    finally:
        db.close()


if "user" not in st.session_state:
    render_login()
else:
    render_app()
