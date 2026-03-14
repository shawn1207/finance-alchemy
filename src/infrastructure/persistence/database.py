from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

from .models import Base

# Default to SQLite in project root
DB_URL = "sqlite:///finance_alchemy.db"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)

def get_db_session() -> Session:
    """Get a new database session."""
    return SessionLocal()
