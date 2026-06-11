from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class NegotiateRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    listing_id: str = Field(..., min_length=1)
    counterparty_listing_id: str = Field(..., min_length=1)
    latest_user_message: str = Field(..., min_length=1)
    messages: List[ChatMessage] = Field(default_factory=list)
    # Meta Content Library: maps to `q` and `listing_countries` on marketplace preview (server-side only).
    marketplace_search_query: Optional[str] = Field(default=None, max_length=200)
    marketplace_listing_country_iso2: Optional[str] = Field(default=None, min_length=2, max_length=2)


class NegotiateResponse(BaseModel):
    ai_response: str
    # status="ok" for a normal AI response, "refused" when the request was
    # blocked by the safety layer (input classifier or output tripwire). The
    # frontend should render refusals with a distinct, non-conversational
    # treatment and surface the report/flag affordance.
    status: Literal["ok", "refused"] = "ok"
    refusal_reason: Optional[str] = None
    refusal_category: Optional[str] = None
    flagged_for_review: bool = False


class AgreementRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    listing_id: str = Field(..., min_length=1)
    counterparty_listing_id: str = Field(..., min_length=1)
    jurisdiction: Optional[str] = Field(default=None, max_length=200)
    messages: List[ChatMessage] = Field(default_factory=list)
    marketplace_search_query: Optional[str] = Field(default=None, max_length=200)
    marketplace_listing_country_iso2: Optional[str] = Field(default=None, min_length=2, max_length=2)


class AgreementResponse(BaseModel):
    agreement_text: str
    status: Literal["ok", "refused"] = "ok"
    refusal_reason: Optional[str] = None
    refusal_category: Optional[str] = None
    flagged_for_review: bool = False


class SubscribeResponse(BaseModel):
    checkout_url: str


class SubscriptionStatusResponse(BaseModel):
    subscribed: bool
    status: str
