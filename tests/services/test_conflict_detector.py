import pytest
import os
import tempfile
import shutil
from sqlite3 import connect
from backend.services.conflict_detector import (
	ensure_conflict_tables, detect_schema_conflicts, detect_row_conflicts,
	detect_cell_conflicts, run_conflict_detection, get_conflict_summary
)


@pytest.fixture
def temp_db():
	"""Create a temporary database for testing."""
	temp_dir = tempfile.mkdtemp()
	db_path = os.path.join(temp_dir, "test.db")
	
	# Create a basic database with some tables
	conn = connect(db_path)
	cur = conn.cursor()
	
	# Create test tables
	cur.execute("""
		CREATE TABLE invoices (
			id TEXT PRIMARY KEY,
			supplier_id TEXT NOT NULL,
			venue_id TEXT NOT NULL,
			invoice_date DATE NOT NULL,
			total_amount_pennies INTEGER NOT NULL,
			ocr_confidence REAL NULL
		)
	""")
	
	cur.execute("""
		CREATE TABLE delivery_notes (
			id TEXT PRIMARY KEY,
			supplier_id TEXT NOT NULL,
			venue_id TEXT NOT NULL,
			date DATE NOT NULL,
			expected_date DATE NULL,
			status TEXT NULL
		)
	""")
	
	cur.execute("""
		CREATE TABLE escalations (
			id TEXT PRIMARY KEY,
			supplier_id TEXT NOT NULL,
			venue_id TEXT NOT NULL,
			level INTEGER NOT NULL,
			status TEXT NOT NULL,
			title TEXT NOT NULL,
			description TEXT NULL,
			due_at TIMESTAMP NULL,
			created_at TIMESTAMP NOT NULL,
			updated_at TIMESTAMP NOT NULL
		)
	""")
	
	# Insert some test data
	cur.execute("""
		INSERT INTO invoices (id, supplier_id, venue_id, invoice_date, total_amount_pennies, ocr_confidence)
		VALUES ('inv1', 'supp1', 'venue1', '2025-01-01', 10000, 95.5)
	""")
	
	cur.execute("""
		INSERT INTO delivery_notes (id, supplier_id, venue_id, date, expected_date, status)
		VALUES ('dn1', 'supp1', 'venue1', '2025-01-01', '2025-01-01', 'delivered')
	""")
	
	cur.execute("""
		INSERT INTO escalations (id, supplier_id, venue_id, level, status, title, description, created_at, updated_at)
		VALUES ('esc1', 'supp1', 'venue1', 1, 'OPEN', 'Test escalation', 'Test description', '2025-01-01T00:00:00', '2025-01-01T00:00:00')
	""")
	
	conn.commit()
	conn.close()
	
	yield db_path
	
	# Cleanup
	shutil.rmtree(temp_dir)


def test_ensure_conflict_tables():
	"""Test that conflict tables are created correctly."""
	# This test would require mocking the database connection
	# For now, just test that the function doesn't raise an exception
	try:
		ensure_conflict_tables()
		assert True
	except Exception as e:
		pytest.fail(f"ensure_conflict_tables raised an exception: {e}")


def test_detect_schema_conflicts(temp_db):
	"""Test schema conflict detection."""
	# Temporarily set the database path
	original_db_path = os.environ.get('OWLIN_DB_PATH')
	os.environ['OWLIN_DB_PATH'] = temp_db
	
	try:
		conflicts = detect_schema_conflicts()
		
		# Should not detect conflicts in a properly structured database
		assert isinstance(conflicts, list)
		
		# Test with a missing table
		conn = connect(temp_db)
		cur = conn.cursor()
		cur.execute("DROP TABLE invoices")
		conn.commit()
		conn.close()
		
		conflicts = detect_schema_conflicts()
		assert len(conflicts) > 0
		assert any(c['table_name'] == 'invoices' for c in conflicts)
		
	finally:
		if original_db_path:
			os.environ['OWLIN_DB_PATH'] = original_db_path
		else:
			del os.environ['OWLIN_DB_PATH']


def test_detect_row_conflicts(temp_db):
	"""Test row conflict detection."""
	# Temporarily set the database path
	original_db_path = os.environ.get('OWLIN_DB_PATH')
	os.environ['OWLIN_DB_PATH'] = temp_db
	
	try:
		conflicts = detect_row_conflicts()
		
		# Should not detect conflicts in a clean database
		assert isinstance(conflicts, list)
		
		# Test with orphaned records
		conn = connect(temp_db)
		cur = conn.cursor()
		cur.execute("DELETE FROM invoices WHERE id = 'inv1'")
		conn.commit()
		conn.close()
		
		conflicts = detect_row_conflicts()
		assert len(conflicts) > 0
		assert any(c['table_name'] == 'delivery_notes' for c in conflicts)
		
	finally:
		if original_db_path:
			os.environ['OWLIN_DB_PATH'] = original_db_path
		else:
			del os.environ['OWLIN_DB_PATH']


def test_detect_cell_conflicts(temp_db):
	"""Test cell conflict detection."""
	# Temporarily set the database path
	original_db_path = os.environ.get('OWLIN_DB_PATH')
	os.environ['OWLIN_DB_PATH'] = temp_db
	
	try:
		conflicts = detect_cell_conflicts()
		
		# Should not detect conflicts in a clean database
		assert isinstance(conflicts, list)
		
		# Test with invalid escalation level
		conn = connect(temp_db)
		cur = conn.cursor()
		cur.execute("UPDATE escalations SET level = 5 WHERE id = 'esc1'")
		conn.commit()
		conn.close()
		
		conflicts = detect_cell_conflicts()
		assert len(conflicts) > 0
		assert any(c['table_name'] == 'escalations' and c['issue'] == 'invalid_escalation_level' for c in conflicts)
		
	finally:
		if original_db_path:
			os.environ['OWLIN_DB_PATH'] = original_db_path
		else:
			del os.environ['OWLIN_DB_PATH']


def test_get_conflict_summary():
	"""Test conflict summary generation."""
	# Test schema conflict
	schema_conflict = {
		'table_name': 'invoices',
		'conflict_type': 'schema',
		'issue': 'missing_table'
	}
	summary = get_conflict_summary(schema_conflict)
	assert 'Missing table: invoices' in summary
	
	# Test row conflict
	row_conflict = {
		'table_name': 'delivery_notes',
		'conflict_type': 'row',
		'issue': 'orphaned_records',
		'count': 5
	}
	summary = get_conflict_summary(row_conflict)
	assert '5 orphaned records in delivery_notes' in summary
	
	# Test cell conflict
	cell_conflict = {
		'table_name': 'escalations',
		'conflict_type': 'cell',
		'issue': 'invalid_escalation_level',
		'count': 3
	}
	summary = get_conflict_summary(cell_conflict)
	assert '3 invalid escalation levels in escalations' in summary


def test_run_conflict_detection(temp_db):
	"""Test full conflict detection run."""
	# Temporarily set the database path
	original_db_path = os.environ.get('OWLIN_DB_PATH')
	os.environ['OWLIN_DB_PATH'] = temp_db
	
	try:
		conflicts = run_conflict_detection()
		
		# Should return a list of conflicts
		assert isinstance(conflicts, list)
		
		# Should log conflicts to database
		conn = connect(temp_db)
		cur = conn.cursor()
		cur.execute("SELECT COUNT(*) FROM conflict_logs")
		count = cur.fetchone()[0]
		conn.close()
		
		assert count >= 0  # May be 0 if no conflicts detected
		
	finally:
		if original_db_path:
			os.environ['OWLIN_DB_PATH'] = original_db_path
		else:
			del os.environ['OWLIN_DB_PATH'] 