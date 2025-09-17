"""
Audit logging service for tracking all actions in the system
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
try:
    from ..db import execute, fetch_all, fetch_one
except ImportError:
    try:
        from backend.db import execute, fetch_all, fetch_one
    except ImportError:
        from db import execute, fetch_all, fetch_one

class AuditService:
    """Service for logging audit events"""
    
    def __init__(self):
        self.ensure_audit_table()
    
    def ensure_audit_table(self):
        """Ensure audit_logs table exists"""
        execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                meta JSON,
                ip_address TEXT,
                user_agent TEXT
            )
        """)
        
        # Create indexes for common queries
        execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)")
        execute("CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor)")
        execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)")
        execute("CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type, resource_id)")
    
    def write_audit(self, 
                   actor: str, 
                   action: str, 
                   meta: Optional[Dict[str, Any]] = None,
                   resource_type: Optional[str] = None,
                   resource_id: Optional[str] = None,
                   ip_address: Optional[str] = None,
                   user_agent: Optional[str] = None) -> str:
        """
        Write an audit log entry
        
        Args:
            actor: Who performed the action (user_id, system, etc.)
            action: What action was performed (PAIR_DN_TO_INVOICE, etc.)
            meta: Additional metadata as dict
            resource_type: Type of resource affected (invoice, delivery_note, etc.)
            resource_id: ID of resource affected
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Audit log ID
        """
        audit_id = f"audit_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{hash(str(meta)) % 10000:04d}"
        
        execute("""
            INSERT INTO audit_logs 
            (id, actor, action, resource_type, resource_id, meta, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            audit_id,
            actor,
            action,
            resource_type,
            resource_id,
            json.dumps(meta) if meta else None,
            ip_address,
            user_agent
        ))
        
        return audit_id
    
    def get_audit_logs(self, 
                      actor: Optional[str] = None,
                      action: Optional[str] = None,
                      resource_type: Optional[str] = None,
                      resource_id: Optional[str] = None,
                      limit: int = 100,
                      offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs with optional filtering
        
        Args:
            actor: Filter by actor
            action: Filter by action
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            limit: Maximum number of records
            offset: Number of records to skip
            
        Returns:
            List of audit log records
        """
        conditions = []
        params = []
        
        if actor:
            conditions.append("actor = ?")
            params.append(actor)
            
        if action:
            conditions.append("action = ?")
            params.append(action)
            
        if resource_type:
            conditions.append("resource_type = ?")
            params.append(resource_type)
            
        if resource_id:
            conditions.append("resource_id = ?")
            params.append(resource_id)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
            SELECT id, timestamp, actor, action, resource_type, resource_id, meta, ip_address, user_agent
            FROM audit_logs
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        
        params.extend([limit, offset])
        
        rows = fetch_all(query, params)
        
        # Parse JSON meta field
        result = []
        for row in rows:
            record = dict(row)
            if record.get('meta'):
                try:
                    record['meta'] = json.loads(record['meta'])
                except json.JSONDecodeError:
                    record['meta'] = {}
            result.append(record)
            
        return result
    
    def get_resource_audit_trail(self, resource_type: str, resource_id: str) -> List[Dict[str, Any]]:
        """Get complete audit trail for a specific resource"""
        return self.get_audit_logs(
            resource_type=resource_type,
            resource_id=resource_id,
            limit=1000
        )
    
    def export_audit_logs(self, 
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         format: str = 'json') -> Dict[str, Any]:
        """
        Export audit logs for external analysis
        
        Args:
            start_date: Start date filter (ISO format)
            end_date: End date filter (ISO format)
            format: Export format ('json', 'csv')
            
        Returns:
            Export data
        """
        conditions = []
        params = []
        
        if start_date:
            conditions.append("timestamp >= ?")
            params.append(start_date)
            
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(end_date)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
            SELECT id, timestamp, actor, action, resource_type, resource_id, meta, ip_address, user_agent
            FROM audit_logs
            {where_clause}
            ORDER BY timestamp ASC
        """
        
        rows = fetch_all(query, params)
        
        # Convert to export format
        if format == 'json':
            result = []
            for row in rows:
                record = dict(row)
                if record.get('meta'):
                    try:
                        record['meta'] = json.loads(record['meta'])
                    except json.JSONDecodeError:
                        record['meta'] = {}
                result.append(record)
            return {'logs': result, 'count': len(result)}
        
        elif format == 'csv':
            # For CSV, flatten meta JSON
            result = []
            for row in rows:
                record = dict(row)
                if record.get('meta'):
                    try:
                        meta = json.loads(record['meta'])
                        # Flatten common meta fields
                        for key, value in meta.items():
                            record[f'meta_{key}'] = value
                    except json.JSONDecodeError:
                        pass
                del record['meta']  # Remove original meta field
                result.append(record)
            return {'logs': result, 'count': len(result)}
        
        else:
            raise ValueError(f"Unsupported export format: {format}")

# Global instance
_audit_service = None

def get_audit_service() -> AuditService:
    """Get singleton instance of audit service"""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service

def write_audit(actor: str, action: str, meta: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    """Convenience function to write audit log"""
    return get_audit_service().write_audit(actor, action, meta, **kwargs)