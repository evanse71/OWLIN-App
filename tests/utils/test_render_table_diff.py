import pytest
from backend.utils.render_table_diff import (
	render_table_diff, render_schema_diff, render_row_diff, render_cell_diff,
	render_unknown_diff, generate_diff_css, render_conflict_list_html
)


def test_render_schema_diff():
	"""Test schema diff rendering."""
	conflict = {
		'table_name': 'invoices',
		'conflict_type': 'schema',
		'issue': 'missing_table',
		'expected': 'Table invoices should exist',
		'actual': 'Table invoices not found'
	}
	
	result = render_schema_diff(conflict)
	
	assert 'html_diff' in result
	assert 'json_diff' in result
	assert 'summary' in result
	assert 'invoices' in result['summary']
	assert 'missing_table' in result['summary']
	assert 'Schema Conflict: invoices' in result['html_diff']


def test_render_row_diff():
	"""Test row diff rendering."""
	conflict = {
		'table_name': 'delivery_notes',
		'conflict_type': 'row',
		'issue': 'orphaned_records',
		'count': 5,
		'description': '5 delivery notes without matching invoices'
	}
	
	result = render_row_diff(conflict)
	
	assert 'html_diff' in result
	assert 'json_diff' in result
	assert 'summary' in result
	assert '5 orphaned records in delivery_notes' in result['summary']
	assert 'Row Conflict: delivery_notes' in result['html_diff']
	assert 'Affected rows: 5' in result['html_diff']


def test_render_cell_diff():
	"""Test cell diff rendering."""
	conflict = {
		'table_name': 'escalations',
		'conflict_type': 'cell',
		'issue': 'invalid_escalation_level',
		'count': 3,
		'description': '3 escalations with invalid level (should be 1, 2, or 3)'
	}
	
	result = render_cell_diff(conflict)
	
	assert 'html_diff' in result
	assert 'json_diff' in result
	assert 'summary' in result
	assert '3 invalid escalation levels in escalations' in result['summary']
	assert 'Cell Conflict: escalations' in result['html_diff']
	assert 'Affected cells: 3' in result['html_diff']
	assert 'Escalation level must be 1, 2, or 3' in result['html_diff']


def test_render_unknown_diff():
	"""Test unknown diff rendering."""
	conflict = {
		'table_name': 'unknown_table',
		'conflict_type': 'unknown',
		'custom_field': 'custom_value'
	}
	
	result = render_unknown_diff(conflict)
	
	assert 'html_diff' in result
	assert 'json_diff' in result
	assert 'summary' in result
	assert 'Unknown conflict in unknown_table' in result['summary']
	assert 'Unknown Conflict: unknown_table' in result['html_diff']


def test_render_table_diff_schema():
	"""Test render_table_diff with schema conflict."""
	conflict = {
		'table_name': 'invoices',
		'conflict_type': 'schema',
		'issue': 'missing_columns'
	}
	
	result = render_table_diff(conflict)
	
	assert 'html_diff' in result
	assert 'json_diff' in result
	assert 'summary' in result
	assert result['json_diff']['type'] == 'schema'


def test_render_table_diff_row():
	"""Test render_table_diff with row conflict."""
	conflict = {
		'table_name': 'delivery_notes',
		'conflict_type': 'row',
		'issue': 'duplicate_primary_keys'
	}
	
	result = render_table_diff(conflict)
	
	assert 'html_diff' in result
	assert 'json_diff' in result
	assert 'summary' in result
	assert result['json_diff']['type'] == 'row'


def test_render_table_diff_cell():
	"""Test render_table_diff with cell conflict."""
	conflict = {
		'table_name': 'invoices',
		'conflict_type': 'cell',
		'issue': 'negative_amounts',
		'count': 2
	}
	
	result = render_table_diff(conflict)
	
	assert 'html_diff' in result
	assert 'json_diff' in result
	assert 'summary' in result
	assert result['json_diff']['type'] == 'cell'


def test_render_table_diff_unknown():
	"""Test render_table_diff with unknown conflict type."""
	conflict = {
		'table_name': 'test_table',
		'conflict_type': 'unknown_type'
	}
	
	result = render_table_diff(conflict)
	
	assert 'html_diff' in result
	assert 'json_diff' in result
	assert 'summary' in result
	assert result['json_diff']['type'] == 'unknown'


def test_generate_diff_css():
	"""Test CSS generation."""
	css = generate_diff_css()
	
	assert isinstance(css, str)
	assert '.diff-container' in css
	assert '.diff-issue' in css
	assert '.diff-comparison' in css
	assert 'font-family' in css
	assert 'border-radius' in css


def test_render_conflict_list_html_empty():
	"""Test rendering empty conflict list."""
	conflicts = []
	
	html = render_conflict_list_html(conflicts)
	
	assert 'No conflicts detected' in html
	assert 'conflict-list' in html


def test_render_conflict_list_html_with_conflicts():
	"""Test rendering conflict list with conflicts."""
	conflicts = [
		{
			'table_name': 'invoices',
			'conflict_type': 'schema',
			'issue': 'missing_table'
		},
		{
			'table_name': 'delivery_notes',
			'conflict_type': 'row',
			'issue': 'orphaned_records',
			'count': 3
		}
	]
	
	html = render_conflict_list_html(conflicts)
	
	assert 'conflict-list' in html
	assert 'Schema Conflict: invoices' in html
	assert 'Row Conflict: delivery_notes' in html
	assert '3 orphaned records in delivery_notes' in html


def test_cell_diff_validation_rules():
	"""Test that validation rules are included in cell diffs."""
	# Test escalation level validation
	conflict = {
		'table_name': 'escalations',
		'conflict_type': 'cell',
		'issue': 'invalid_escalation_level'
	}
	
	result = render_cell_diff(conflict)
	
	assert 'Escalation level must be 1, 2, or 3' in result['html_diff']
	assert 'Level 1: Standard escalation (48h SLA)' in result['html_diff']
	assert 'Level 2: High priority (24h SLA)' in result['html_diff']
	assert 'Level 3: Critical (8h SLA)' in result['html_diff']
	
	# Test escalation status validation
	conflict = {
		'table_name': 'escalations',
		'conflict_type': 'cell',
		'issue': 'invalid_escalation_status'
	}
	
	result = render_cell_diff(conflict)
	
	assert 'Valid statuses: OPEN, ACK, IN_PROGRESS, WAITING_VENDOR, RESOLVED, CLOSED' in result['html_diff']
	
	# Test negative amounts validation
	conflict = {
		'table_name': 'invoices',
		'conflict_type': 'cell',
		'issue': 'negative_amounts'
	}
	
	result = render_cell_diff(conflict)
	
	assert 'Invoice amounts must be non-negative' in result['html_diff']
	assert 'Consider using credits or adjustments for negative amounts' in result['html_diff']
	
	# Test OCR confidence validation
	conflict = {
		'table_name': 'invoices',
		'conflict_type': 'cell',
		'issue': 'invalid_ocr_confidence'
	}
	
	result = render_cell_diff(conflict)
	
	assert 'OCR confidence must be between 0 and 100' in result['html_diff']
	assert 'Values represent percentage confidence' in result['html_diff']


def test_row_diff_action_suggestions():
	"""Test that action suggestions are included in row diffs."""
	# Test orphaned records suggestions
	conflict = {
		'table_name': 'delivery_notes',
		'conflict_type': 'row',
		'issue': 'orphaned_records',
		'count': 5
	}
	
	result = render_row_diff(conflict)
	
	assert 'Recommended Actions:' in result['html_diff']
	assert 'Review orphaned records for data integrity' in result['html_diff']
	assert 'Consider deleting orphaned records' in result['html_diff']
	assert 'Restore missing parent records if possible' in result['html_diff']
	
	# Test duplicate primary keys suggestions
	conflict = {
		'table_name': 'invoices',
		'conflict_type': 'row',
		'issue': 'duplicate_primary_keys'
	}
	
	result = render_row_diff(conflict)
	
	assert 'Recommended Actions:' in result['html_diff']
	assert 'Investigate duplicate key generation' in result['html_diff']
	assert 'Merge duplicate records if appropriate' in result['html_diff']
	assert 'Delete duplicate records' in result['html_diff'] 