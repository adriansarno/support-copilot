"""Pydantic request/response models for the API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    chat_id: str | None = None
    top_k: int = 10
    skip_grading: bool = False


class CitationResponse(BaseModel):
    source_index: int
    chunk_id: str
    title: str
    source_type: str
    content_snippet: str


class GradeResponse(BaseModel):
    relevance: float
    faithfulness: float
    completeness: float
    explanation: str
    low_confidence: bool


class SourceResponse(BaseModel):
    chunk_id: str
    title: str
    source_type: str
    content: str
    score: float


class PromptMetadataResponse(BaseModel):
    prompt_name: str = ""
    prompt_version: str = ""
    prompt_hash: str = ""


class ChatResponse(BaseModel):
    chat_id: str
    message_id: str
    answer: str
    citations: list[CitationResponse] = []
    grade: GradeResponse | None = None
    sources: list[SourceResponse] = []
    prompt_metadata: PromptMetadataResponse | None = None


class ChatHistoryResponse(BaseModel):
    chat_id: str
    messages: list[ChatMessage]
    created_at: str


class ChatListItem(BaseModel):
    chat_id: str
    title: str
    created_at: str
    message_count: int


# ---------------------------------------------------------------------------
# Suggest Reply
# ---------------------------------------------------------------------------

class SuggestReplyRequest(BaseModel):
    ticket_subject: str
    ticket_body: str
    agent_notes: str = ""
    top_k: int = 8


class SuggestReplyResponse(BaseModel):
    reply: str
    citations: list[CitationResponse] = []
    sources: list[SourceResponse] = []
    prompt_metadata: PromptMetadataResponse | None = None


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    chat_id: str
    message_id: str
    rating: int = Field(..., ge=-1, le=1)  # -1 = down, 0 = neutral, 1 = up
    comment: str = ""


class FeedbackResponse(BaseModel):
    feedback_id: str
    status: str = "recorded"
