from __future__ import annotations
from typing import Dict, Any, List, Tuple
import json
import difflib
from datetime import datetime


def render_table_diff(conflict: Dict[str, Any]) -> Dict[str, Any]:
	"""
	Render a table diff in both HTML and JSON formats.
	
	Args:
		conflict: Conflict dictionary from conflict detector
		
	Returns:
		Dictionary with 'html_diff', 'json_diff', and 'summary' keys
	"""
	conflict_type = conflict.get('conflict_type', 'unknown')
	table_name = conflict.get('table_name', 'unknown')
	
	if conflict_type == 'schema':
		return render_schema_diff(conflict)
	elif conflict_type == 'row':
		return render_row_diff(conflict)
	elif conflict_type == 'cell':
		return render_cell_diff(conflict)
	else:
		return render_unknown_diff(conflict)


def render_schema_diff(conflict: Dict[str, Any]) -> Dict[str, Any]:
	"""Render schema-level differences."""
	table_name = conflict.get('table_name', 'unknown')
	issue = conflict.get('issue', 'unknown')
	expected = conflict.get('expected', '')
	actual = conflict.get('actual', '')
	
	# Generate HTML diff
	html_parts = []
	html_parts.append(f'<div class="diff-container">')
	html_parts.append(f'<h3>Schema Conflict: {table_name}</h3>')
	html_parts.append(f'<div class="diff-issue">Issue: {issue}</div>')
	
	if expected and actual:
		html_parts.append('<div class="diff-comparison">')
		html_parts.append('<div class="diff-expected">')
		html_parts.append('<h4>Expected:</h4>')
		html_parts.append(f'<pre>{expected}</pre>')
		html_parts.append('</div>')
		html_parts.append('<div class="diff-actual">')
		html_parts.append('<h4>Actual:</h4>')
		html_parts.append(f'<pre>{actual}</pre>')
		html_parts.append('</div>')
		html_parts.append('</div>')
	
	html_parts.append('</div>')
	
	# Generate JSON diff
	json_diff = {
		"type": "schema",
		"table_name": table_name,
		"issue": issue,
		"expected": expected,
		"actual": actual,
		"timestamp": datetime.utcnow().isoformat()
	}
	
	# Generate summary
	summary = f"Schema conflict in {table_name}: {issue}"
	if expected and actual:
		summary += f" - Expected: {expected}, Actual: {actual}"
	
	return {
		"html_diff": '\n'.join(html_parts),
		"json_diff": json_diff,
		"summary": summary
	}


def render_row_diff(conflict: Dict[str, Any]) -> Dict[str, Any]:
	"""Render row-level differences."""
	table_name = conflict.get('table_name', 'unknown')
	issue = conflict.get('issue', 'unknown')
	count = conflict.get('count', 0)
	description = conflict.get('description', '')
	
	# Generate HTML diff
	html_parts = []
	html_parts.append(f'<div class="diff-container">')
	html_parts.append(f'<h3>Row Conflict: {table_name}</h3>')
	html_parts.append(f'<div class="diff-issue">Issue: {issue}</div>')
	
	if count > 0:
		html_parts.append(f'<div class="diff-count">Affected rows: {count}</div>')
	
	if description:
		html_parts.append(f'<div class="diff-description">{description}</div>')
	
	# Add action suggestions
	html_parts.append('<div class="diff-actions">')
	html_parts.append('<h4>Recommended Actions:</h4>')
	
	if issue == 'orphaned_records':
		html_parts.append('<ul>')
		html_parts.append('<li>Review orphaned records for data integrity</li>')
		html_parts.append('<li>Consider deleting orphaned records</li>')
		html_parts.append('<li>Restore missing parent records if possible</li>')
		html_parts.append('</ul>')
	elif issue == 'duplicate_primary_keys':
		html_parts.append('<ul>')
		html_parts.append('<li>Investigate duplicate key generation</li>')
		html_parts.append('<li>Merge duplicate records if appropriate</li>')
		html_parts.append('<li>Delete duplicate records</li>')
		html_parts.append('</ul>')
	
	html_parts.append('</div>')
	html_parts.append('</div>')
	
	# Generate JSON diff
	json_diff = {
		"type": "row",
		"table_name": table_name,
		"issue": issue,
		"count": count,
		"description": description,
		"timestamp": datetime.utcnow().isoformat()
	}
	
	# Generate summary
	summary = f"Row conflict in {table_name}: {description or issue}"
	if count > 0:
		summary += f" ({count} affected)"
	
	return {
		"html_diff": '\n'.join(html_parts),
		"json_diff": json_diff,
		"summary": summary
	}


def render_cell_diff(conflict: Dict[str, Any]) -> Dict[str, Any]:
	"""Render cell-level differences."""
	table_name = conflict.get('table_name', 'unknown')
	issue = conflict.get('issue', 'unknown')
	count = conflict.get('count', 0)
	description = conflict.get('description', '')
	
	# Generate HTML diff
	html_parts = []
	html_parts.append(f'<div class="diff-container">')
	html_parts.append(f'<h3>Cell Conflict: {table_name}</h3>')
	html_parts.append(f'<div class="diff-issue">Issue: {issue}</div>')
	
	if count > 0:
		html_parts.append(f'<div class="diff-count">Affected cells: {count}</div>')
	
	if description:
		html_parts.append(f'<div class="diff-description">{description}</div>')
	
	# Add validation rules
	html_parts.append('<div class="diff-validation">')
	html_parts.append('<h4>Validation Rules:</h4>')
	
	if issue == 'invalid_escalation_level':
		html_parts.append('<ul>')
		html_parts.append('<li>Escalation level must be 1, 2, or 3</li>')
		html_parts.append('<li>Level 1: Standard escalation (48h SLA)</li>')
		html_parts.append('<li>Level 2: High priority (24h SLA)</li>')
		html_parts.append('<li>Level 3: Critical (8h SLA)</li>')
		html_parts.append('</ul>')
	elif issue == 'invalid_escalation_status':
		html_parts.append('<ul>')
		html_parts.append('<li>Valid statuses: OPEN, ACK, IN_PROGRESS, WAITING_VENDOR, RESOLVED, CLOSED</li>')
		html_parts.append('</ul>')
	elif issue == 'negative_amounts':
		html_parts.append('<ul>')
		html_parts.append('<li>Invoice amounts must be non-negative</li>')
		html_parts.append('<li>Consider using credits or adjustments for negative amounts</li>')
		html_parts.append('</ul>')
	elif issue == 'invalid_ocr_confidence':
		html_parts.append('<ul>')
		html_parts.append('<li>OCR confidence must be between 0 and 100</li>')
		html_parts.append('<li>Values represent percentage confidence</li>')
		html_parts.append('</ul>')
	
	html_parts.append('</div>')
	html_parts.append('</div>')
	
	# Generate JSON diff
	json_diff = {
		"type": "cell",
		"table_name": table_name,
		"issue": issue,
		"count": count,
		"description": description,
		"timestamp": datetime.utcnow().isoformat()
	}
	
	# Generate summary
	summary = f"Cell conflict in {table_name}: {description or issue}"
	if count > 0:
		summary += f" ({count} affected)"
	
	return {
		"html_diff": '\n'.join(html_parts),
		"json_diff": json_diff,
		"summary": summary
	}


def render_unknown_diff(conflict: Dict[str, Any]) -> Dict[str, Any]:
	"""Render unknown conflict type."""
	table_name = conflict.get('table_name', 'unknown')
	
	html_parts = []
	html_parts.append(f'<div class="diff-container">')
	html_parts.append(f'<h3>Unknown Conflict: {table_name}</h3>')
	html_parts.append(f'<div class="diff-unknown">Unknown conflict type detected</div>')
	html_parts.append(f'<pre>{json.dumps(conflict, indent=2)}</pre>')
	html_parts.append('</div>')
	
	json_diff = {
		"type": "unknown",
		"table_name": table_name,
		"raw_conflict": conflict,
		"timestamp": datetime.utcnow().isoformat()
	}
	
	summary = f"Unknown conflict in {table_name}"
	
	return {
		"html_diff": '\n'.join(html_parts),
		"json_diff": json_diff,
		"summary": summary
	}


def generate_diff_css() -> str:
	"""Generate CSS styles for diff rendering."""
	return """
	<style>
	.diff-container {
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		padding: 16px;
		margin: 8px 0;
		background: white;
	}
	
	.diff-container h3 {
		margin: 0 0 12px 0;
		color: #374151;
		font-size: 16px;
		font-weight: 600;
	}
	
	.diff-container h4 {
		margin: 12px 0 8px 0;
		color: #6b7280;
		font-size: 14px;
		font-weight: 500;
	}
	
	.diff-issue {
		background: #fef3c7;
		border: 1px solid #f59e0b;
		border-radius: 4px;
		padding: 8px 12px;
		margin: 8px 0;
		color: #92400e;
		font-weight: 500;
	}
	
	.diff-count {
		background: #dbeafe;
		border: 1px solid #3b82f6;
		border-radius: 4px;
		padding: 8px 12px;
		margin: 8px 0;
		color: #1e40af;
		font-weight: 500;
	}
	
	.diff-description {
		background: #f3f4f6;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		padding: 8px 12px;
		margin: 8px 0;
		color: #374151;
	}
	
	.diff-comparison {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 16px;
		margin: 12px 0;
	}
	
	.diff-expected, .diff-actual {
		border: 1px solid #e5e7eb;
		border-radius: 4px;
		padding: 12px;
	}
	
	.diff-expected {
		background: #f0fdf4;
		border-color: #22c55e;
	}
	
	.diff-actual {
		background: #fef2f2;
		border-color: #ef4444;
	}
	
	.diff-expected h4 {
		color: #166534;
	}
	
	.diff-actual h4 {
		color: #991b1b;
	}
	
	.diff-expected pre, .diff-actual pre {
		margin: 8px 0 0 0;
		font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
		font-size: 12px;
		white-space: pre-wrap;
		word-break: break-word;
	}
	
	.diff-actions, .diff-validation {
		background: #f9fafb;
		border: 1px solid #e5e7eb;
		border-radius: 4px;
		padding: 12px;
		margin: 12px 0;
	}
	
	.diff-actions ul, .diff-validation ul {
		margin: 8px 0;
		padding-left: 20px;
	}
	
	.diff-actions li, .diff-validation li {
		margin: 4px 0;
		color: #4b5563;
	}
	
	.diff-unknown {
		background: #fef2f2;
		border: 1px solid #ef4444;
		border-radius: 4px;
		padding: 8px 12px;
		margin: 8px 0;
		color: #991b1b;
		font-weight: 500;
	}
	
	.diff-unknown pre {
		background: #f9fafb;
		border: 1px solid #e5e7eb;
		border-radius: 4px;
		padding: 12px;
		margin: 8px 0;
		font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
		font-size: 12px;
		overflow-x: auto;
	}
	</style>
	"""


def render_conflict_list_html(conflicts: List[Dict[str, Any]]) -> str:
	"""Render a list of conflicts in HTML format."""
	if not conflicts:
		return '<div class="no-conflicts">No conflicts detected</div>'
	
	html_parts = []
	html_parts.append('<div class="conflict-list">')
	
	for conflict in conflicts:
		diff_result = render_table_diff(conflict)
		html_parts.append(diff_result['html_diff'])
	
	html_parts.append('</div>')
	
	return '\n'.join(html_parts) 