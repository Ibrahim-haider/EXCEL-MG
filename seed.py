"""
Idempotent seed data: departments, roles, KPI definitions, demo logins.
Called once at app startup (see app.py's init_db, cached with st.cache_resource).
"""
import models
from auth import hash_password

DEPARTMENTS = [
    ("admin", "Admin"), ("management", "Management"), ("sales", "Sales"),
    ("finance", "Finance"), ("inventory", "Inventory"), ("marketing", "Marketing"),
    ("hr", "HR"), ("aftersales", "After Sales"),
]

ROLES = [
    ("admin", "Administrator", True, True, True),
    ("manager", "Department Manager", True, True, False),
    ("analyst", "Analyst", True, True, False),
    ("viewer", "Viewer", False, True, False),
]

KPI_DEFS = [
    ("sales", "revenue_mtd", "Revenue (MTD)", "PKR"),
    ("sales", "units_sold", "Units Sold", "units"),
    ("sales", "top_dealer", "Top Dealer", None),
    ("sales", "active_dealers", "Active Dealers", "count"),
    ("inventory", "inventory_value", "Inventory Value", "PKR"),
    ("inventory", "dead_stock_value", "Dead Stock Value", "PKR"),
    ("finance", "total_budget", "Total Budget", "PKR"),
    ("finance", "total_actual", "Total Actual", "PKR"),
    ("finance", "variance_pct", "Budget Variance", "%"),
    ("marketing", "total_spend", "Total Spend", "PKR"),
    ("marketing", "total_leads", "Total Leads", "count"),
    ("marketing", "cost_per_lead", "Cost per Lead", "PKR"),
    ("hr", "headcount", "Headcount", "count"),
    ("hr", "active_employees", "Active Employees", "count"),
    ("aftersales", "open_warranty_claims", "Open Warranty Claims", "count"),
    ("aftersales", "closed_warranty_claims", "Closed Warranty Claims", "count"),
]

DEMO_USERS = [
    ("Admin User", "admin@rd-electronics.pk", "admin", "admin"),
    ("Sales Manager", "sales@rd-electronics.pk", "manager", "sales"),
    ("Finance Analyst", "finance@rd-electronics.pk", "analyst", "finance"),
]


def _get_or_create_department(db, code, name):
    dept = db.query(models.Department).filter_by(code=code).first()
    if not dept:
        dept = models.Department(code=code, name=name)
        db.add(dept)
        db.commit()
        db.refresh(dept)
    return dept


def _get_or_create_role(db, code, name, can_upload, can_export, can_manage_users):
    role = db.query(models.Role).filter_by(code=code).first()
    if not role:
        role = models.Role(code=code, name=name, can_upload=can_upload,
                            can_export=can_export, can_manage_users=can_manage_users)
        db.add(role)
        db.commit()
        db.refresh(role)
    return role


def run_seed(db):
    depts = {code: _get_or_create_department(db, code, name) for code, name in DEPARTMENTS}
    roles = {r[0]: _get_or_create_role(db, *r) for r in ROLES}

    for dept_code, kpi_code, name, unit in KPI_DEFS:
        exists = db.query(models.KPIDefinition).filter_by(
            department_id=depts[dept_code].id, code=kpi_code).first()
        if not exists:
            db.add(models.KPIDefinition(
                department_id=depts[dept_code].id, code=kpi_code, name=name, unit=unit))
    db.commit()

    for full_name, email, role_code, dept_code in DEMO_USERS:
        if not db.query(models.User).filter_by(email=email).first():
            db.add(models.User(
                full_name=full_name,
                email=email,
                password_hash=hash_password("password123"),
                role_id=roles[role_code].id,
                department_id=depts[dept_code].id,
            ))
    db.commit()
