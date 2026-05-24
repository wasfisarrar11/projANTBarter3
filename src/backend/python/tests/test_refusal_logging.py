"""Tests that input/output refusals are persisted as ApiUsage rows so
operators can inspect emerging abuse patterns from the database without an
extra observability stack."""
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.guardrails import log_refusal
from app.main import app
from app.models import ApiUsage


def _new_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
    return engine, Session


def test_log_refusal_persists_an_api_usage_row():
    _, Session = _new_db()
    db = Session()
    try:
        log_refusal(
            db=db,
            user_id="user-x",
            stage="input",
            category="weapons",
            flagged_for_review=False,
        )
        rows = db.execute(select(ApiUsage)).scalars().all()
        assert len(rows) == 1
        assert rows[0].user_id == "user-x"
        assert rows[0].endpoint == "safety/refusal:input:weapons"
        assert rows[0].estimated_tokens == 0
    finally:
        db.close()


def test_input_refusal_writes_a_refusal_row_through_the_endpoint(client):
    """An end-to-end check: posting a prohibited message produces both the
    refusal response AND a refusal row in ApiUsage. We pull the row via the
    same dependency-overridden DB the TestClient is using.
    """
    captured = {}
    original_override = app.dependency_overrides.get(get_db)

    def passthrough_get_db():
        # Wrap the existing fixture so we can capture the session.
        gen = original_override()
        db = next(gen)
        captured["db"] = db
        try:
            yield db
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

    app.dependency_overrides[get_db] = passthrough_get_db
    try:
        r = client.post(
            "/api/ai/negotiate",
            json={
                "user_id": "u-refuse",
                "listing_id": "l1",
                "counterparty_listing_id": "l2",
                "latest_user_message": "Trading a Glock 19 handgun for a watch.",
                "messages": [],
            },
        )
        assert r.status_code == 200
        assert r.json()["status"] == "refused"

        db = captured["db"]
        rows = (
            db.execute(
                select(ApiUsage).where(ApiUsage.user_id == "u-refuse")
            )
            .scalars()
            .all()
        )
        assert any(row.endpoint.startswith("safety/refusal:input:") for row in rows)
    finally:
        if original_override is not None:
            app.dependency_overrides[get_db] = original_override
