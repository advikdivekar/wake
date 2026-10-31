"""Stable JSON contract (see docs/ARCHITECTURE.md §3)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Citation(BaseModel):
    doc_id: str
    chunk_id: str
    title: str
    url: Optional[str] = None
    location: Optional[str] = None
    excerpt: str
    score: Optional[float] = None
    license: Optional[str] = None


class Segment(BaseModel):
    segment_id: int
    channel: str
    channel_name: Optional[str]
    channel_kind: Optional[str]
    split: Literal["train", "test"]
    sampling: int
    n_points: int
    start: str
    end: str
    label: Optional[int] = None


class Gap(BaseModel):
    start: str
    end: str
    seconds: float


class ZeroRun(BaseModel):
    start_idx: int
    end_idx: int


class TelemetrySeries(BaseModel):
    segment_id: Optional[int]
    t: list[str]
    v: list[float]
    gaps: list[Gap] = []
    zero_runs: list[ZeroRun] = []
    peaks_idx: list[int] = []


class Contributor(BaseModel):
    feature: str
    value: float
    z: float
    importance: float
    plain: str


class Prediction(BaseModel):
    segment_id: Optional[int]
    probability: float
    decision: Literal["prioritise", "queue", "archive"]
    thresholds: dict
    model: str
    contributors: list[Contributor] = []


class SimilarSegment(BaseModel):
    segment_id: int
    distance: float
    label: int
    channel: str
    note: str = "Resemblance in measured characteristics, not evidence of a shared fault."


class MemoryRecord(BaseModel):
    record_id: Optional[str] = None
    channel_id: Optional[str] = None
    sensor_type: Optional[str] = None
    units: Optional[str] = None
    event_date: Optional[str] = None
    publication_date: Optional[str] = None
    observation: Optional[str] = None
    operational_response: Optional[str] = None
    root_cause: Optional[str] = None
    evidence_excerpt: Optional[str] = None
    unknown_fields: list[str] = []
    source: Optional[Citation] = None


class KnownItem(BaseModel):
    statement: str
    basis: Literal["measured", "cited"]
    citations: list[Citation] = []


class SignalEvidence(BaseModel):
    zero_runs: int
    max_zero_run: int
    gap_count: int
    max_gap_s: float
    n_peaks: int
    irregular_sampling: bool
    noise_std: float


class InvestigationCard(BaseModel):
    card_id: str
    segment_id: int
    created_at: str
    prediction: Prediction
    signal_evidence: SignalEvidence
    historical_context: list[SimilarSegment]
    documents: list[Citation]
    known: list[KnownItem]
    unknown: list[str]
    suggested_action: str
    summary: str
    summary_model: str
    review_status: Literal["unreviewed", "confirmed", "rejected", "investigating"] = "unreviewed"
    ground_truth: Optional[int] = None


class FeedbackIn(BaseModel):
    action: Literal["confirm", "reject", "investigate"]
    note: str = ""


class AskIn(BaseModel):
    question: str
    k: int = Field(6, ge=1, le=20)


class AskAnswer(BaseModel):
    question: str
    answer: str
    citations: list[Citation]
    missing: list[str]
    model: str


class ExtractIn(BaseModel):
    text: str


class PredictIn(BaseModel):
    segment_id: Optional[int] = None
    channel: Optional[str] = None
    sampling: Optional[int] = None
    t: Optional[list[str]] = None
    v: Optional[list[float]] = None


class InvestigateIn(BaseModel):
    segment_id: int
    use_lm: bool = True
