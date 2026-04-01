from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class NegotiationSession(Base):
    __tablename__ = "negotiation_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(120), index=True)
    listing_id: Mapped[str] = mapped_column(String(120), index=True)
    counterparty_listing_id: Mapped[str] = mapped_column(String(120), index=True)
    messages_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgreementDraft(Base):
    __tablename__ = "agreement_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(120), index=True)
    listing_id: Mapped[str] = mapped_column(String(120), index=True)
    counterparty_listing_id: Mapped[str] = mapped_column(String(120), index=True)
    jurisdiction: Mapped[str] = mapped_column(String(120))
    agreement_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ApiUsage(Base):
    __tablename__ = "api_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(120), index=True)
    endpoint: Mapped[str] = mapped_column(String(80), index=True)
    estimated_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
