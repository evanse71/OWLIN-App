from __future__ import annotations
from uuid import uuid4
from datetime import datetime, timedelta
from sqlite3 import connect
import os

from ..contracts import TimelineEvent, SupplierSummary, SupplierBadge
from .metrics import get_latest_metrics

DB_PATH = os.path.join("data", "owlin.db")


def _get_conn():
	os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
	return connect(DB_PATH)


def build_summary(supplier_id: str, venue_id: str | None) -> SupplierSummary:
	"""Build supplier summary with metrics and badges."""
	conn = _get_conn()
	cur = conn.cursor()
	
	# Get supplier name
	cur.execute("SELECT name FROM suppliers WHERE id = ?", (supplier_id,))
	supplier_name = cur.fetchone()
	supplier_name = supplier_name[0] if supplier_name else "Supplier"
	
	# Get metrics
	if venue_id:
		mismatch, ontime, vol = get_latest_metrics(supplier_id, venue_id)
	else:
		# Fallback if no venue specified
		mismatch, ontime, vol = 0.0, 0.0, 0.0
	
	# Create badges based on metrics
	badges = []
	
	if ontime < 80:
		badges.append(SupplierBadge(
			label="Low on-time",
			tone="warn",
			tooltip="On-time deliveries < 80%"
		))
	
	if mismatch > 10:
		badges.append(SupplierBadge(
			label="High mismatch",
			tone="warn",
			tooltip="Mismatch rate > 10%"
		))
	
	if vol > 15:
		badges.append(SupplierBadge(
			label="High volatility",
			tone="warn",
			tooltip="Price volatility > 15%"
		))
	
	if ontime >= 95 and mismatch <= 5:
		badges.append(SupplierBadge(
			label="Top performer",
			tone="ok",
			tooltip="Excellent performance metrics"
		))
	
	conn.close()
	
	return SupplierSummary(
		supplier_id=supplier_id,
		supplier_name=supplier_name,
		venue_id=venue_id,
		mismatch_rate=mismatch,
		on_time_rate=ontime,
		price_volatility=vol,
		badges=badges
	)


def build_timeline(supplier_id: str, venue_id: str | None, start: datetime, end: datetime) -> list[TimelineEvent]:
	"""Build chronological timeline of events for a supplier."""
	conn = _get_conn()
	cur = conn.cursor()
	
	events = []
	
	# Invoices
	venue_filter = "AND venue_id = ?" if venue_id else ""
	venue_params = [venue_id] if venue_id else []
	
	cur.execute(f"""
		SELECT id, invoice_date, total_amount_pennies, ocr_confidence
		FROM invoices 
		WHERE supplier_id = ? {venue_filter} AND invoice_date BETWEEN ? AND ?
		ORDER BY invoice_date
	""", [supplier_id] + venue_params + [start.date().isoformat(), end.date().isoformat()])
	
	for row in cur.fetchall():
		inv_id, inv_date, amount, confidence = row
		events.append(TimelineEvent(
			id=inv_id,
			ts=datetime.combine(inv_date, datetime.min.time()),
			type="INVOICE",
			title=f"Invoice: ${amount/100:.2f}",
			summary=f"OCR Confidence: {confidence:.1f}%" if confidence else None,
			ref_id=inv_id,
			severity="info"
		))
	
	# Delivery notes
	cur.execute(f"""
		SELECT id, date, expected_date, status
		FROM delivery_notes 
		WHERE supplier_id = ? {venue_filter} AND date BETWEEN ? AND ?
		ORDER BY date
	""", [supplier_id] + venue_params + [start.date().isoformat(), end.date().isoformat()])
	
	for row in cur.fetchall():
		dn_id, dn_date, expected_date, status = row
		ontime = expected_date and dn_date <= expected_date
		severity = "error" if not ontime else "info"
		
		events.append(TimelineEvent(
			id=dn_id,
			ts=datetime.combine(dn_date, datetime.min.time()),
			type="DELIVERY",
			title=f"Delivery: {status or 'Received'}",
			summary="Late delivery" if not ontime else "On time",
			ref_id=dn_id,
			severity=severity
		))
	
	# Flagged issues
	cur.execute(f"""
		SELECT id, created_at, type, status, description
		FROM flagged_issues 
		WHERE supplier_id = ? {venue_filter} AND created_at BETWEEN ? AND ?
		ORDER BY created_at
	""", [supplier_id] + venue_params + [start.isoformat(), end.isoformat()])
	
	for row in cur.fetchall():
		issue_id, created_at, issue_type, status, description = row
		severity = "error" if status in ("OPEN", "ESCALATED") else "warn"
		
		events.append(TimelineEvent(
			id=issue_id,
			ts=created_at,
			type="ISSUE_OPENED",
			title=f"Issue: {issue_type}",
			summary=description,
			ref_id=issue_id,
			severity=severity
		))
		
		# Check if resolved
		if status in ("RESOLVED", "CLOSED"):
			events.append(TimelineEvent(
				id=str(uuid4()),
				ts=created_at + timedelta(hours=1),  # Assume resolved 1 hour later
				type="ISSUE_RESOLVED",
				title="Issue resolved",
				summary=f"Status: {status}",
				ref_id=issue_id,
				severity="info"
			))
	
	# Escalations
	cur.execute(f"""
		SELECT id, created_at, level, status, title, description
		FROM escalations 
		WHERE supplier_id = ? {venue_filter} AND created_at BETWEEN ? AND ?
		ORDER BY created_at
	""", [supplier_id] + venue_params + [start.isoformat(), end.isoformat()])
	
	for row in cur.fetchall():
		esc_id, created_at, level, status, title, description = row
		severity = "error" if level == 3 else "warn" if level == 2 else "info"
		
		events.append(TimelineEvent(
			id=esc_id,
			ts=created_at,
			type="ESCALATION_OPENED",
			title=f"Escalation L{level}: {title}",
			summary=description,
			ref_id=esc_id,
			severity=severity
		))
		
		# Get escalation notes
		cur.execute("""
			SELECT id, author_id, body, created_at 
			FROM escalation_notes 
			WHERE escalation_id = ? AND created_at BETWEEN ? AND ?
			ORDER BY created_at
		""", [esc_id, start.isoformat(), end.isoformat()])
		
		for note_row in cur.fetchall():
			note_id, author_id, body, note_created_at = note_row
			events.append(TimelineEvent(
				id=note_id,
				ts=note_created_at,
				type="ESCALATION_UPDATED",
				title="Note added",
				summary=body[:100] + "..." if len(body) > 100 else body,
				ref_id=esc_id,
				severity="info"
			))
		
		# Check if resolved
		if status in ("RESOLVED", "CLOSED"):
			events.append(TimelineEvent(
				id=str(uuid4()),
				ts=created_at + timedelta(hours=2),  # Assume resolved 2 hours later
				type="ESCALATION_RESOLVED",
				title=f"Escalation {status.lower()}",
				summary=f"Status: {status}",
				ref_id=esc_id,
				severity="info"
			))
	
	conn.close()
	
	# Sort all events by timestamp
	events.sort(key=lambda x: x.ts)
	
	return events 