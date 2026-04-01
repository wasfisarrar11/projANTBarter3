from typing import List, Literal

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


class NegotiateResponse(BaseModel):
    ai_response: str


class AgreementRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    listing_id: str = Field(..., min_length=1)
    counterparty_listing_id: str = Field(..., min_length=1)
    jurisdiction: str = Field(default="Arizona, USA")
    messages: List[ChatMessage] = Field(default_factory=list)


class AgreementResponse(BaseModel):
    agreement_text: str
