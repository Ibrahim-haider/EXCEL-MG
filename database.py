"""
Database engine & session management for the Streamlit build.

Uses SQLite by default (./storage/dev.db) so it runs with zero setup on
Streamlit Community Cloud. Point DATABASE_URL at Postgres for anything
persistent/real — models.py works against either engine unchanged.

NOTE ON PERSISTENCE: Streamlit Community Cloud's filesystem is ephemeral —
it resets on redeploy/reboot/sleep. SQLite is fine for a demo, but for a
real pilot point DATABASE_URL at a hosted Postgres instance (e.g. Neon,
Supabase, Railway) via st.secrets.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

os.makedirs("./storage/uploads", exist_ok=True)
os.makedirs("./storage/reports", exist_ok=True)

try:
    import streamlit as st
    DATABASE_URL = st.secrets.get("DATABASE_URL", os.getenv("DATABASE_URL", "sqlite:///./storage/dev.db"))
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./storage/dev.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Yields a DB session; caller is responsible for closing it."""
    return SessionLocal()
