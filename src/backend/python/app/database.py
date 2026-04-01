from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings


Base = declarative_base()


def _build_engine():
    # Fallback for local development if Azure SQL connection is not set.
    if not settings.DATABASE_URL:
        return create_engine("sqlite:///./antbarter_local.db", future=True)
    return create_engine(settings.DATABASE_URL, future=True, pool_pre_ping=True)


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
