from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from uuid import UUID
from datetime import date, datetime

class SupplierProfile(BaseModel):
    id: UUID
    name: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    preferred: bool = False

class SupplierMetrics(BaseModel):
    total_spend: float = Field(..., description="Total spend in GBP")
    avg_delivery_time_days: float = Field(..., description="Average delivery time in days")
    delivery_on_time_pct: float = Field(..., description="Percentage of on-time deliveries")
    mismatch_rate_pct: float = Field(..., description="Percentage of mismatched items")
    credit_response_days: float = Field(..., description="Average credit response time in days")

class TrendPoint(BaseModel):
    date: date
    value: float

class SupplierTrends(BaseModel):
    price_history: List[TrendPoint] = Field(default_factory=list, description="Historical price trends")
    delivery_timeliness: List[TrendPoint] = Field(default_factory=list, description="Delivery timeliness trends")

class Insight(BaseModel):
    type: Literal["price_increase", "delivery_delays", "credit_slow", "preferred_inactivity", "multiple_issues"]
    severity: Literal["low", "medium", "high"]
    message: str
    recommendation: str

class RiskRating(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Risk score from 0-100")
    label: str = Field(..., description="Human-readable risk label")
    color: str = Field(..., description="Hex color for UI display")

class SupplierScorecard(BaseModel):
    supplier: SupplierProfile
    metrics: SupplierMetrics
    trends: SupplierTrends
    insights: List[Insight] = Field(default_factory=list)
    risk_rating: RiskRating
    last_updated: datetime = Field(..., description="When this scorecard was last updated") 