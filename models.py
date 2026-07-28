"""
SQLAlchemy models. These mirror database/schema.sql but use portable column
types (String UUIDs, plain strings for enums, JSON) so the same code runs
against SQLite in dev and Postgres in production.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Numeric, Text,
    ForeignKey, ForeignKeyConstraint
)
from sqlalchemy.orm import relationship

from database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    code = Column(String(30), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    code = Column(String(30), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    can_upload = Column(Boolean, default=False)
    can_export = Column(Boolean, default=True)
    can_manage_users = Column(Boolean, default=False)


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    role = relationship("Role")
    department = relationship("Department")


class Upload(Base):
    __tablename__ = "uploads"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=False)
    status = Column(String(20), default="uploaded")
    # uploaded -> validating -> cleaning -> generating_kpis -> published | failed
    row_count = Column(Integer, nullable=True)
    valid_row_count = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    clean_data_path = Column(String(500), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    department = relationship("Department")
    uploader = relationship("User")


class UploadPipelineLog(Base):
    __tablename__ = "upload_pipeline_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(String(36), ForeignKey("uploads.id"), nullable=False)
    step = Column(String(40), nullable=False)
    level = Column(String(10), default="info")
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class KPIDefinition(Base):
    __tablename__ = "kpi_definitions"
    id = Column(Integer, primary_key=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    code = Column(String(60), nullable=False)
    name = Column(String(150), nullable=False)
    unit = Column(String(30), nullable=True)
    description = Column(Text, nullable=True)


class KPISnapshot(Base):
    __tablename__ = "kpi_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(String(36), ForeignKey("uploads.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    kpi_code = Column(String(60), nullable=False)
    value_numeric = Column(Numeric(18, 2), nullable=True)
    value_text = Column(String(255), nullable=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Dealer(Base):
    __tablename__ = "dealers"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)


class SalesRecord(Base):
    __tablename__ = "sales_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(String(36), ForeignKey("uploads.id"), nullable=False)
    dealer_id = Column(Integer, ForeignKey("dealers.id"), nullable=True)
    model = Column(String(100), nullable=True)
    units = Column(Integer, default=0)
    revenue = Column(Numeric(18, 2), default=0)
    sale_date = Column(Date, nullable=False)


class AIInsight(Base):
    __tablename__ = "ai_insights"
    id = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    upload_id = Column(String(36), ForeignKey("uploads.id"), nullable=True)
    insight_text = Column(Text, nullable=False)
    category = Column(String(50), nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)


class Report(Base):
    __tablename__ = "reports"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    requested_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    report_name = Column(String(200), nullable=False)
    format = Column(String(10), nullable=False)
    file_path = Column(String(500), nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity = Column(String(60), nullable=True)
    entity_id = Column(String(60), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
