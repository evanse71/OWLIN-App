from __future__ import annotations
from typing import List, Optional, Literal, Dict, Any
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, conint, Field


class LineItem(BaseModel):
	id: UUID
	description: str
	qty: float
	unit_price_pennies: int
	total_pennies: int
	uom: Optional[str] = None
	sku: Optional[str] = None


# Alias for delivery note items (same shape)
class DnLineItem(LineItem):
	pass


class Invoice(BaseModel):
	id: UUID
	supplier_name: str
	invoice_number: str
	invoice_date: date
	total_amount_pennies: int
	vat_amount_pennies: int
	currency: Literal["GBP"]
	status: Literal["pending", "scanned", "matched", "flagged"]
	confidence: conint(ge=0, le=100)
	line_items: List[LineItem]
	delivery_note_id: Optional[UUID] = None


class DeliveryNote(BaseModel):
	id: UUID
	supplier_name: Optional[str]
	note_number: Optional[str]
	date: Optional[date]
	status: Literal["pending", "parsed", "matched", "rejected"]
	ocr_confidence: conint(ge=0, le=100)
	matched_invoice_id: Optional[UUID]
	items: List[DnLineItem]


class InvoiceSummary(BaseModel):
	id: UUID
	supplier_name: str
	invoice_number: str
	invoice_date: Optional[date]
	total_amount_pennies: int
	vat_amount_pennies: int
	currency: Literal["GBP"]
	status: Literal["pending", "scanned", "matched", "flagged"]
	confidence: conint(ge=0, le=100)


class MatchCandidate(BaseModel):
	invoice: InvoiceSummary
	score: float
	breakdown: Dict[str, float]


class MatchSuggestionsResponse(BaseModel):
	delivery_note_id: UUID
	candidates: List[MatchCandidate]


class MatchConfirmRequest(BaseModel):
	delivery_note_id: UUID
	invoice_id: UUID


class MatchRejectRequest(BaseModel):
	delivery_note_id: UUID


class OkResponse(BaseModel):
	ok: bool


# Insights contracts
from pydantic import confloat
from typing import Literal as _Literal

class TimeSeriesPoint(BaseModel):
	t: date
	v: float
	n: Optional[int] = None

class MetricSeries(BaseModel):
	metric: _Literal["spend", "price_volatility", "on_time_rate", "mismatch_rate", "confidence_median"]
	bucket: _Literal["day", "week", "month"]
	points: List[TimeSeriesPoint]

class InsightBadge(BaseModel):
	label: str
	value: str
	color: _Literal["green", "yellow", "red", "blue"]
	trend: Optional[_Literal["up", "down", "stable"]] = None

class InsightSummary(BaseModel):
	supplier_id: UUID
	period_start: date
	period_end: date
	top_badges: List[InsightBadge]
	series: List[MetricSeries]

class InsightAlertsResponse(BaseModel):
	supplier_id: UUID
	alerts: List[Dict[str, Any]]

class ItemForecast(BaseModel):
	item_name: str
	forecast_amount: float
	confidence: float
	trend: str

class AggregateForecast(BaseModel):
	total_forecast: float
	confidence: float
	items: List[ItemForecast]


# Delivery Matching contracts
class ConfidenceBreakdown(BaseModel):
	supplier: float = Field(ge=0, le=40, description="Supplier match score (0-40 points)")
	date: float = Field(ge=0, le=25, description="Date proximity score (0-25 points)")
	line_items: float = Field(ge=0, le=30, description="Line item overlap score (0-30 points)")
	value: float = Field(ge=0, le=5, description="Value match score (0-5 points)")


class MatchCandidate(BaseModel):
	delivery_note_id: UUID
	confidence: float = Field(ge=0, le=100, description="Overall confidence score (0-100)")
	breakdown: ConfidenceBreakdown
	delivery_note: Optional[Dict[str, Any]] = None  # Full delivery note data


class MatchCandidatesResponse(BaseModel):
	invoice_id: UUID
	candidate_delivery_notes: List[MatchCandidate]


class MatchConfirmRequest(BaseModel):
	invoice_id: UUID
	delivery_note_id: UUID


class MatchRejectRequest(BaseModel):
	invoice_id: UUID
	delivery_note_id: UUID


class MatchConfirmResponse(BaseModel):
	status: Literal["confirmed", "rejected"]
	confidence: float


class MatchRejectResponse(BaseModel):
	status: Literal["rejected"]


class RetryLateResponse(BaseModel):
	new_matches_found: int
	message: str
	tone: Literal["ok", "warn", "error", "neutral"] = "neutral"
	tooltip: Optional[str] = None

class InsightCard(BaseModel):
	title: str
	value: str
	description: Optional[str] = None
	badges: List[InsightBadge] = []
	trend: Optional[float] = None
	trend_direction: Literal["up", "down", "neutral"] = "neutral"

class ProductTrend(BaseModel):
	product_name: str
	current_price: float
	price_change: float
	price_change_percent: float
	trend_direction: Literal["up", "down", "stable"]
	confidence: float
	last_updated: datetime
	supplier_count: int
	volume_trend: Optional[float] = None

class ProductTrendsResponse(BaseModel):
	period: str
	products: List[ProductTrend]
	summary: Dict[str, Any]

class ForecastPoint(BaseModel):
	date: date
	value: float
	confidence_lower: float
	confidence_upper: float

class ForecastSeries(BaseModel):
	metric: str
	points: List[ForecastPoint]
	accuracy: float

class ForecastResponse(BaseModel):
	period: str
	series: List[ForecastSeries]
	summary: Dict[str, Any]

# Recovery & Backup contracts
class IntegrityReport(BaseModel):
	ok: bool
	reasons: List[str]
	db_version: Optional[str] = None
	last_backup_at: Optional[datetime] = None

class BackupEntry(BaseModel):
	id: UUID
	name: str
	created_at: datetime
	size_bytes: int
	checksum_sha256: str
	path: str

class RestoreDryRunRequest(BaseModel):
	backup_id: UUID

class FieldDiff(BaseModel):
	column: str
	old: Optional[str] = None
	new: Optional[str] = None
	decision: Literal["keep_old", "use_new", "manual"] = "use_new"

class RowDiff(BaseModel):
	table: str
	pk: str
	diffs: List[FieldDiff]

class DiffReport(BaseModel):
	backup_id: UUID
	rows: List[RowDiff]
	summary: Dict[str, Any]

# Update Bundle contracts
class UpdateBundle(BaseModel):
	id: UUID
	filename: str
	version: str
	build: str
	created_at: datetime
	description: Optional[str] = None
	verified: Literal["pending", "ok", "failed"] = "pending"
	reason: Optional[str] = None

class UpdateAction(BaseModel):
	action: Literal["alembic_upgrade", "copy_tree", "run_hook"]
	revision: Optional[str] = None
	from_path: Optional[str] = None
	to_path: Optional[str] = None
	mode: Optional[Literal["merge", "replace"]] = "merge"
	path: Optional[str] = None
	timeout_sec: Optional[int] = 120

class UpdatePlan(BaseModel):
	bundle: UpdateBundle
	steps: List[UpdateAction]

class ChangelogEntry(BaseModel):
	id: UUID
	version: str
	build: str
	applied_at: datetime
	status: Literal["success", "rollback", "failed"]
	notes: Optional[str] = None

class RollbackPoint(BaseModel):
	id: UUID
	created_at: datetime
	version_before: Optional[str] = None
	backup_zip: str

# Enhanced Update System Contracts
class UpdateValidateResult(BaseModel):
	bundle_id: UUID
	filename: str
	version: str
	build: str
	signature_ok: bool
	manifest_ok: bool
	reason: Optional[str] = None
	checksum_sha256: Optional[str] = None
	created_at: Optional[datetime] = None

class DependencyItem(BaseModel):
	id: str
	version: str
	satisfied: bool
	reason: Optional[str] = None

class UpdateDependencies(BaseModel):
	bundle_id: UUID
	items: List[DependencyItem]
	all_satisfied: bool

class UpdateProgressTick(BaseModel):
	job_id: UUID
	kind: Literal['apply','rollback']
	step: Literal['preflight','snapshot','apply','finalise','done','error']
	percent: int = Field(ge=0, le=100)
	message: Optional[str] = None
	occurred_at: datetime

# GM Dashboard contracts
class KpiCard(BaseModel):
	title: str
	value: str
	delta: Optional[str] = None
	trend: Literal["up", "down", "neutral"] = "neutral"
	series: List[float] = []

class SeriesPoint(BaseModel):
	date: str
	value: float

class VenueSeries(BaseModel):
	venue_id: UUID
	venue_name: str
	series: List[SeriesPoint]

class VenueRow(BaseModel):
	venue_id: UUID
	venue_name: str
	total_invoices: int
	total_spend: float
	match_rate: float
	avg_confidence: float
	flagged_issues: int
	delivery_reliability: float

class DashboardSummary(BaseModel):
	period: str
	total_venues: int
	total_invoices: int
	total_spend: float
	avg_match_rate: float
	avg_confidence: float
	total_issues: int
	kpi_cards: List[KpiCard]
	venue_comparison: List[VenueRow]
	trends: List[VenueSeries]

class RefreshRequest(BaseModel):
	venue_ids: Optional[List[UUID]] = None
	force: bool = False

# Supplier Timeline & Escalation contracts
class SupplierBadge(BaseModel):
	label: str
	tone: Literal['ok', 'warn', 'error', 'neutral'] = 'neutral'
	tooltip: Optional[str] = None

class SupplierSummary(BaseModel):
	supplier_id: UUID
	supplier_name: str
	venue_id: Optional[UUID] = None
	mismatch_rate: float
	on_time_rate: float
	price_volatility: float
	badges: List[SupplierBadge]

class TimelineEvent(BaseModel):
	id: UUID
	ts: datetime
	type: Literal['INVOICE', 'DELIVERY', 'ISSUE_OPENED', 'ISSUE_RESOLVED', 'PRICE_SPIKE', 'ESCALATION_OPENED', 'ESCALATION_UPDATED', 'ESCALATION_RESOLVED']
	title: str
	summary: Optional[str] = None
	ref_id: Optional[UUID] = None
	severity: Optional[Literal['info', 'warn', 'error']] = 'info'

class EscalationNote(BaseModel):
	id: UUID
	author_id: UUID
	body: str
	created_at: datetime

class Escalation(BaseModel):
	id: UUID
	supplier_id: UUID
	venue_id: UUID
	level: int
	status: Literal['OPEN', 'ACK', 'IN_PROGRESS', 'WAITING_VENDOR', 'RESOLVED', 'CLOSED']
	title: str
	description: Optional[str] = None
	due_at: Optional[datetime] = None
	opened_by: UUID
	assigned_to: Optional[UUID] = None
	created_at: datetime
	updated_at: datetime
	notes: List[EscalationNote] = []

class CreateEscalationRequest(BaseModel):
	supplier_id: UUID
	venue_id: UUID
	level: int = 1
	title: str
	description: Optional[str] = None
	assigned_to: Optional[UUID] = None

class UpdateEscalationRequest(BaseModel):
	status: Optional[Literal['ACK', 'IN_PROGRESS', 'WAITING_VENDOR', 'RESOLVED', 'CLOSED']] = None
	level: Optional[int] = None
	assigned_to: Optional[UUID] = None
	add_note: Optional[str] = None

class TimelineResponse(BaseModel):
	summary: SupplierSummary
	events: List[TimelineEvent]

# Recovery Mode & Conflict Resolver contracts
class ConflictLog(BaseModel):
	id: UUID
	table_name: str
	conflict_type: Literal['schema', 'row', 'cell']
	detected_at: datetime
	details: dict

class ConflictResolution(BaseModel):
	id: UUID
	conflict_id: UUID
	action: Literal['applied', 'rolled_back', 'ignored']
	resolved_by: UUID
	resolved_at: datetime

class TableDiff(BaseModel):
	table_name: str
	diff_type: Literal['schema', 'row', 'cell']
	html_diff: str
	json_diff: dict
	summary: str

class ConflictListItem(BaseModel):
	id: UUID
	table_name: str
	conflict_type: Literal['schema', 'row', 'cell']
	detected_at: datetime
	resolved: bool
	summary: str

class ResolveConflictRequest(BaseModel):
	action: Literal['apply', 'rollback', 'ignore']
	notes: Optional[str] = None

class RecoveryStatus(BaseModel):
	active: bool
	reason: Optional[str] = None
	activated_at: Optional[datetime] = None
	activated_by: Optional[UUID] = None

class ActivateRecoveryRequest(BaseModel):
	reason: str

# Backup & Support Pack contracts
class BackupInfo(BaseModel):
    id: UUID
    created_at: str
    path: str
    size_bytes: int
    mode: Literal['manual','scheduled']
    app_version: str
    db_schema_version: int

class BackupCreateResult(BaseModel):
    id: UUID
    created_at: str
    path: str
    size_bytes: int

class RestorePreviewChange(BaseModel):
    table: str
    adds: int
    updates: int
    deletes: int

class RestorePreview(BaseModel):
    backup_id: UUID
    ok: bool
    reason: Optional[str] = None
    changes: List[RestorePreviewChange] = []

class SupportPackInfo(BaseModel):
    id: UUID
    created_at: str
    path: str
    size_bytes: int
    notes: Optional[str] = None
    app_version: str

# Flagged Issues Bulk Actions contracts
class BulkUpdateRequest(BaseModel):
    issue_ids: List[UUID] = Field(..., description="List of issue IDs to update")
    action: Literal["resolve", "dismiss"] = Field(..., description="Action to perform")

class BulkEscalateRequest(BaseModel):
    issue_ids: List[UUID] = Field(..., description="List of issue IDs to escalate")
    to_role: Literal["gm", "finance"] = Field(..., description="Role to escalate to")
    reason: Optional[str] = Field(None, max_length=250, description="Optional escalation reason")

class BulkAssignRequest(BaseModel):
    issue_ids: List[UUID] = Field(..., description="List of issue IDs to assign")
    assignee_id: UUID = Field(..., description="User ID to assign issues to")

class BulkCommentRequest(BaseModel):
    issue_ids: List[UUID] = Field(..., description="List of issue IDs to comment on")
    body: str = Field(..., min_length=1, max_length=4000, description="Comment text")

class BulkActionResult(BaseModel):
    issue_id: UUID
    success: bool
    error: Optional[str] = None

class BulkActionResponse(BaseModel):
    ok: bool = Field(..., description="Overall success status")
    results: List[BulkActionResult] = Field(..., description="Results for each issue")
    failed: List[BulkActionResult] = Field(..., description="Failed operations")
    message: str = Field(..., description="Summary message")

# Supplier Behaviour Tracking contracts
class SupplierEventRequest(BaseModel):
    supplier_id: UUID = Field(..., description="Supplier ID")
    event_type: Literal["missed_delivery", "invoice_mismatch", "late_delivery", "quality_issue", "price_spike"] = Field(..., description="Type of event")
    severity: Literal["low", "medium", "high"] = Field(..., description="Event severity")
    description: Optional[str] = Field(None, max_length=1000, description="Optional event description")
    source: Literal["invoice_audit", "manual", "system"] = Field(..., description="Event source")

class SupplierEventResponse(BaseModel):
    ok: bool = Field(..., description="Success status")
    event_id: UUID = Field(..., description="Created event ID")
    created_at: str = Field(..., description="Event creation timestamp")

class SupplierEvent(BaseModel):
    id: UUID = Field(..., description="Event ID")
    event_type: Literal["missed_delivery", "invoice_mismatch", "late_delivery", "quality_issue", "price_spike"] = Field(..., description="Event type")
    severity: Literal["low", "medium", "high"] = Field(..., description="Event severity")
    description: Optional[str] = Field(None, description="Event description")
    source: Literal["invoice_audit", "manual", "system"] = Field(..., description="Event source")
    created_at: str = Field(..., description="Creation timestamp")
    is_acknowledged: bool = Field(..., description="Acknowledgment status")

class SupplierEventsResponse(BaseModel):
    supplier_id: UUID = Field(..., description="Supplier ID")
    events: List[SupplierEvent] = Field(..., description="List of events")

class SupplierInsight(BaseModel):
    metric_name: str = Field(..., description="Metric name")
    metric_value: float = Field(..., description="Metric value")
    trend_direction: Literal["up", "down", "flat"] = Field(..., description="Trend direction")
    trend_percentage: float = Field(..., description="Trend percentage")
    period_days: int = Field(..., description="Analysis period in days")
    last_updated: str = Field(..., description="Last update timestamp")

class SupplierInsightsResponse(BaseModel):
    supplier_id: UUID = Field(..., description="Supplier ID")
    insights: List[SupplierInsight] = Field(..., description="List of insights")

class SupplierAlert(BaseModel):
    supplier_id: UUID = Field(..., description="Supplier ID")
    supplier_name: str = Field(..., description="Supplier name")
    alert_type: str = Field(..., description="Alert type")
    severity: Literal["low", "medium", "high"] = Field(..., description="Alert severity")
    summary: str = Field(..., description="Alert summary")

class SupplierAlertsResponse(BaseModel):
    alerts: List[SupplierAlert] = Field(..., description="List of alerts")

# License Manager contracts
class LicenseSummary(BaseModel):
    customer: str = Field(..., description="Customer name")
    license_id: str = Field(..., description="License ID")
    expires_utc: str = Field(..., description="Expiry date in UTC")
    device_id: str = Field(..., description="Device ID")
    venues: List[str] = Field(..., description="List of venue IDs")
    roles: Dict[str, int] = Field(..., description="Role limits")
    features: Dict[str, bool] = Field(..., description="Feature flags")

class LicenseStatus(BaseModel):
    valid: bool = Field(..., description="License validity")
    state: Literal["valid", "grace", "expired", "invalid", "mismatch", "not_found"] = Field(..., description="License state")
    grace_until_utc: Optional[str] = Field(None, description="Grace period end")
    reason: Optional[str] = Field(None, description="Reason for invalid state")
    summary: Optional[LicenseSummary] = Field(None, description="License summary")

class LicenseUploadRequest(BaseModel):
    license_content: str = Field(..., description="License file content")

class LicenseUploadResponse(BaseModel):
    ok: bool = Field(..., description="Upload success")
    message: str = Field(..., description="Result message")
    status: LicenseStatus = Field(..., description="Updated license status")

class LicenseVerifyResponse(BaseModel):
    signature_valid: bool = Field(..., description="Signature verification result")
    device_match: bool = Field(..., description="Device binding check")
    expiry_check: str = Field(..., description="Expiry status")
    grace_period: Optional[str] = Field(None, description="Grace period info")
    overall_valid: bool = Field(..., description="Overall validity")

# Recovery Mode contracts
class SnapshotInfo(BaseModel):
    id: str = Field(..., description="Snapshot ID")
    size_bytes: int = Field(..., description="Snapshot size in bytes")
    created_at: str = Field(..., description="Creation timestamp")
    manifest_ok: bool = Field(..., description="Manifest verification status")

class RecoveryStatus(BaseModel):
    state: Literal["normal", "degraded", "recovery", "restore_pending"] = Field(..., description="Recovery state")
    reason: Optional[str] = Field(None, description="Reason for recovery state")
    details: List[str] = Field(..., description="Detailed issues")
    snapshots: List[SnapshotInfo] = Field(..., description="Available snapshots")
    live_db_hash: str = Field(..., description="Live database hash")
    schema_version: int = Field(..., description="Current schema version")
    app_version: str = Field(..., description="Current app version")

class RestorePreview(BaseModel):
    snapshot: SnapshotInfo = Field(..., description="Selected snapshot")
    tables: List[Dict[str, Any]] = Field(..., description="Table diffs")
    summary: Dict[str, int] = Field(..., description="Summary statistics")

class DiffCell(BaseModel):
    col: str = Field(..., description="Column name")
    old: Optional[Any] = Field(None, description="Old value")
    new: Optional[Any] = Field(None, description="New value")
    changed: bool = Field(..., description="Whether value changed")

class DiffRow(BaseModel):
    key: str = Field(..., description="Row key")
    op: Literal["add", "remove", "change", "identical"] = Field(..., description="Operation type")
    cells: List[DiffCell] = Field(..., description="Cell differences")

class TableDiff(BaseModel):
    table: str = Field(..., description="Table name")
    pk: List[str] = Field(..., description="Primary key columns")
    stats: Dict[str, int] = Field(..., description="Statistics")
    rows: List[DiffRow] = Field(..., description="Row differences")

class ResolvePlan(BaseModel):
    snapshot_id: str = Field(..., description="Snapshot ID")
    decisions: Dict[str, Dict[str, str]] = Field(..., description="Table decisions")
    merge_fields: Optional[Dict[str, Dict[str, Dict[str, str]]]] = Field(None, description="Merge field decisions")

class RestoreCommitResponse(BaseModel):
    ok: bool = Field(..., description="Success status")
    restore_id: str = Field(..., description="Restore operation ID")

# Supplier Scorecard contracts
class SupplierMetric(BaseModel):
	name: str
	score: float
	trend: Literal["up","down","stable"]
	detail: str

class SupplierInsight(BaseModel):
	id: str
	timestamp: datetime
	severity: Literal["info","warn","critical"]
	message: str

class SupplierScorecard(BaseModel):
	supplier_id: str
	overall_score: float
	categories: Dict[str, SupplierMetric]
	insights: List[SupplierInsight]

# Matching contracts
class MatchReason(BaseModel):
    code: str             # e.g., "DATE_WINDOW_MATCH", "SKU_FUZZY_MATCH"
    detail: str           # human-readable
    weight: float         # contribution to confidence (pos/neg)

class LineDiff(BaseModel):
    id: str
    invoice_line_id: Optional[int]
    delivery_line_id: Optional[int]
    status: Literal["ok","qty_mismatch","price_mismatch","missing_on_dn","missing_on_inv"]
    confidence: float
    qty_invoice: Optional[float]
    qty_dn: Optional[float]
    qty_uom: Optional[str]      # normalized
    price_invoice: Optional[float]
    price_dn: Optional[float]
    reasons: List[MatchReason]

class MatchingPair(BaseModel):
    id: str
    invoice_id: int
    delivery_note_id: int
    status: Literal["matched","partial","unmatched","conflict"]
    confidence: float
    reasons: List[MatchReason]
    line_diffs: List[LineDiff]

class MatchingSummary(BaseModel):
    totals: dict   # counts per status
    pairs: List[MatchingPair]

class MatchingConfig(BaseModel):
    date_window_days: int = 3
    amount_proximity_pct: float = 0.10
    qty_tol_rel: float = 0.025
    qty_tol_abs: float = 0.25
    price_tol_rel: float = 0.05
    fuzzy_desc_threshold: float = 0.90

# Forecast contracts
class ForecastPoint(BaseModel):
    t: str                 # ISO date (month start)
    yhat: float
    yhat_lower: float
    yhat_upper: float

class ForecastSeries(BaseModel):
    item_id: int
    supplier_id: Optional[int]
    venue_id: Optional[int]
    horizon_months: int
    granularity: Literal["month"]
    model: str
    version: int
    points: List[ForecastPoint]
    explain: Dict[str, Any]   # includes residual sd, params, scenario info

class ForecastQuality(BaseModel):
    item_id: int
    model: str
    window_days: int
    smape: float
    mape: float
    wape: float
    bias_pct: float

class ForecastSummary(BaseModel):
    items: List[Dict[str, Any]]  # each with item_id, name, latest_price, trend, forecast_1m, 3m, 12m

class ForecastScenario(BaseModel):
    inflation_annual_pct: float        # 0..10%
    shock_pct: float                   # apply to last known price (+/-)
    weight_by_venue: bool
    alt_supplier_id: Optional[int]

class ForecastJob(BaseModel):
    id: str
    job_type: str
    status: str
    progress: int
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
