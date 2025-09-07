#!/usr/bin/env python3
"""
Audit Service

Logs policy decisions and OCR processing for audit trail
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import asdict

from ..ocr.policy import PolicyDecision, PolicyAction
from ..ocr.classifier import ClassificationResult
from ..ocr.validate import ValidationResult

logger = logging.getLogger(__name__)

class AuditService:
    """Audit service for logging policy decisions and OCR processing"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "owlin.db"
        self.db_path = Path(db_path)
    
    def log_policy_decision(self,
                          user_id: Optional[str],
                          session_id: Optional[str],
                          document_id: Optional[int],
                          policy_decision: PolicyDecision,
                          classification: ClassificationResult,
                          validation: ValidationResult,
                          ocr_confidence: float,
                          processing_time_ms: int,
                          extracted_data: Dict[str, Any]) -> bool:
        """
        Log a policy decision to the audit trail
        
        Args:
            user_id: User ID (optional)
            session_id: Session ID (optional)
            document_id: Document ID (optional)
            policy_decision: Policy decision
            classification: Classification result
            validation: Validation result
            ocr_confidence: OCR confidence
            processing_time_ms: Processing time in milliseconds
            extracted_data: Extracted document data
            
        Returns:
            True if logged successfully
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Prepare reasons as JSON
            reasons_json = json.dumps([reason.value for reason in policy_decision.reasons])
            
            # Prepare additional metadata
            metadata = {
                "classification": {
                    "doc_type": classification.doc_type,
                    "confidence": classification.confidence,
                    "reasons": classification.reasons
                },
                "validation": {
                    "arithmetic_ok": validation.arithmetic_ok if validation else None,
                    "currency_ok": validation.currency_ok if validation else None,
                    "vat_ok": validation.vat_ok if validation else None,
                    "date_ok": validation.date_ok if validation else None,
                    "issues": [issue.issue_type for issue in validation.issues] if validation and validation.issues else []
                },
                "extracted_data": {
                    "supplier": extracted_data.get("supplier"),
                    "total_amount": extracted_data.get("total_amount"),
                    "line_items_count": len(extracted_data.get("line_items", []))
                },
                "auto_retry": {
                    "used": policy_decision.auto_retry_used,
                    "metrics": policy_decision.retry_metrics
                }
            }
            
            cursor.execute("""
                INSERT INTO audit_log (
                    user_id, session_id, action, document_id,
                    policy_action, reasons_json, confidence, processing_time_ms,
                    metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                session_id,
                "OCR_POLICY_DECISION",
                document_id,
                policy_decision.action.value,
                reasons_json,
                ocr_confidence,
                processing_time_ms,
                json.dumps(metadata),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"📋 Audit log: {policy_decision.action.value} for doc {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to log audit trail: {e}")
            return False
    
    def log_ocr_processing(self,
                          user_id: Optional[str],
                          session_id: Optional[str],
                          document_id: Optional[int],
                          file_path: str,
                          processing_time_ms: int,
                          success: bool,
                          error_message: Optional[str] = None) -> bool:
        """
        Log OCR processing event
        
        Args:
            user_id: User ID (optional)
            session_id: Session ID (optional)
            document_id: Document ID (optional)
            file_path: Path to processed file
            processing_time_ms: Processing time in milliseconds
            success: Whether processing was successful
            error_message: Error message if failed
            
        Returns:
            True if logged successfully
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            metadata = {
                "file_path": file_path,
                "success": success,
                "error_message": error_message
            }
            
            cursor.execute("""
                INSERT INTO audit_log (
                    user_id, session_id, action, document_id,
                    policy_action, reasons_json, confidence, processing_time_ms,
                    metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                session_id,
                "OCR_PROCESSING",
                document_id,
                None,  # No policy action for processing events
                None,  # No reasons for processing events
                None,  # No confidence for processing events
                processing_time_ms,
                json.dumps(metadata),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"📋 OCR processing log: {'success' if success else 'failed'} for {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to log OCR processing: {e}")
            return False
    
    def get_audit_logs(self,
                      since: Optional[datetime] = None,
                      action: Optional[str] = None,
                      policy_action: Optional[str] = None,
                      limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get audit logs with optional filtering
        
        Args:
            since: Filter logs since this datetime
            action: Filter by action type
            policy_action: Filter by policy action
            limit: Maximum number of logs to return
            
        Returns:
            List of audit log entries
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            query = "SELECT * FROM audit_log WHERE 1=1"
            params = []
            
            if since:
                query += " AND created_at >= ?"
                params.append(since.isoformat())
            
            if action:
                query += " AND action = ?"
                params.append(action)
            
            if policy_action:
                query += " AND policy_action = ?"
                params.append(policy_action)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            
            logs = []
            for row in rows:
                log_entry = dict(zip(columns, row))
                
                # Parse JSON fields
                if log_entry.get('reasons_json'):
                    log_entry['reasons'] = json.loads(log_entry['reasons_json'])
                
                if log_entry.get('metadata_json'):
                    log_entry['metadata'] = json.loads(log_entry['metadata_json'])
                
                logs.append(log_entry)
            
            conn.close()
            return logs
            
        except Exception as e:
            logger.error(f"❌ Failed to get audit logs: {e}")
            return []

# Global audit service instance
_audit_service: Optional[AuditService] = None

def get_audit_service() -> AuditService:
    """Get global audit service instance"""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service 