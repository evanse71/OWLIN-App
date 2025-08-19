from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Session


def log_event(
	session: Session,
	event_type: str,
	entity_type: str,
	entity_id: str,
	message: str,
) -> None:
	# Assume audit_log table exists with columns: id, event_type, entity_type, entity_id, message, created_at
	session.execute(
		"""
		INSERT INTO audit_log (event_type, entity_type, entity_id, message, created_at)
		VALUES (:event_type, :entity_type, :entity_id, :message, :created_at)
		""",
		{
			"event_type": event_type,
			"entity_type": entity_type,
			"entity_id": entity_id,
			"message": message,
			"created_at": datetime.utcnow().isoformat(),
		},
	) 