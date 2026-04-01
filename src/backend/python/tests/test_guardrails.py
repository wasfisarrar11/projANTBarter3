from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.guardrails import check_limits_or_raise, estimate_tokens_from_text


def test_estimate_tokens_empty():
    assert estimate_tokens_from_text("") == 0


def test_estimate_tokens_non_empty():
    assert estimate_tokens_from_text("abcd") == 1
    assert estimate_tokens_from_text("a" * 8) == 2


def test_check_limits_allows_first_request():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
    db = Session()
    try:
        check_limits_or_raise(
            db=db,
            user_id="user-a",
            endpoint="/api/ai/negotiate",
            estimated_tokens_for_request=50,
        )
    finally:
        db.close()
