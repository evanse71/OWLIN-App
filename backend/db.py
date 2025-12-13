# backend/db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_engine = None
_SessionLocal = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(os.environ.get("OWLIN_DB_URL", "sqlite:///./owlin.db"),
                                pool_pre_ping=True, future=True)
    return _engine

def get_session_maker():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)
    return _SessionLocal

def get_db():
    SessionLocal = get_session_maker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()