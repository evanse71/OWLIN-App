"""Test backup functionality"""
from backend.services.backup import _ensure_backup_sessions_table, _get_backup_session, _update_backup_session

_ensure_backup_sessions_table()
s = _get_backup_session()
print(f"Session: last_backup={s['last_backup_at']}, count={s['doc_count_since_backup']}, backup_id={s['last_backup_id']}")

# Test updating with a backup_id
_update_backup_session(backup_id="test-backup-123", increment_count=False)
s2 = _get_backup_session()
print(f"After update: last_backup={s2['last_backup_at']}, count={s2['doc_count_since_backup']}, backup_id={s2['last_backup_id']}")

