"""
Explainer System

Generates human-readable explanations for line item verdicts with caching.
"""

import json
import logging
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from pydantic import BaseModel, Field
from db_manager_unified import get_db_manager

logger = logging.getLogger(__name__)

class ExplanationOutput(BaseModel):
    """Strict JSON output schema for explanations"""
    headline: str = Field(..., max_length=100)
    explanation: str = Field(..., max_length=500)
    suggested_actions: List[Dict[str, str]] = Field(..., max_items=3)
    engine_verdict: str
    engine_facts_hash: str
    model_id: str = "deterministic"
    prompt_hash: str = ""
    response_hash: str = ""

@dataclass
class ExplainerCache:
    """Cache entry for explanations"""
    line_fingerprint: str
    explanation_json: str
    created_at: datetime
    ttl_days: int = 30

class ExplainerEngine:
    """Deterministic explanation engine with caching"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.cache_ttl_days = 30
        self._init_cache_table()
    
    def _init_cache_table(self):
        """Initialize explanation cache table"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if table exists
                cursor.execute("PRAGMA table_info(explanation_cache)")
                if not cursor.fetchall():
                    cursor.executescript("""
                        CREATE TABLE explanation_cache (
                            line_fingerprint TEXT PRIMARY KEY,
                            explanation_json TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            ttl_days INTEGER DEFAULT 30
                        );
                        CREATE INDEX idx_explanation_cache_created ON explanation_cache(created_at);
                    """)
                    conn.commit()
                    logger.info("Created explanation_cache table")
                    
        except Exception as e:
            logger.error(f"❌ Failed to init cache table: {e}")
    
    def explain_line_item(self, line_fingerprint: str, verdict: str, 
                         context: Dict[str, Any], use_llm: bool = False) -> Optional[ExplanationOutput]:
        """
        Generate explanation for line item.
        
        Args:
            line_fingerprint: Line fingerprint for caching
            verdict: Assigned verdict
            context: Additional context data
            use_llm: Whether to use LLM (currently always uses deterministic)
            
        Returns:
            ExplanationOutput or None if failed
        """
        try:
            # Check cache first
            cached = self._get_cached_explanation(line_fingerprint)
            if cached:
                return cached
            
            # Generate explanation
            explanation = self._generate_explanation(verdict, context)
            if not explanation:
                return None
            
            # Cache the explanation
            self._cache_explanation(line_fingerprint, explanation)
            
            return explanation
            
        except Exception as e:
            logger.error(f"❌ Explanation generation failed: {e}")
            return None
    
    def _get_cached_explanation(self, line_fingerprint: str) -> Optional[ExplanationOutput]:
        """Get cached explanation if valid"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT explanation_json, created_at, ttl_days
                    FROM explanation_cache 
                    WHERE line_fingerprint = ?
                """, (line_fingerprint,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                explanation_json, created_at_str, ttl_days = row
                created_at = datetime.fromisoformat(created_at_str)
                
                # Check if expired
                if datetime.now() - created_at > timedelta(days=ttl_days):
                    # Remove expired entry
                    cursor.execute("DELETE FROM explanation_cache WHERE line_fingerprint = ?", 
                                 (line_fingerprint,))
                    conn.commit()
                    return None
                
                # Parse and return cached explanation
                explanation_data = json.loads(explanation_json)
                return ExplanationOutput(**explanation_data)
                
        except Exception as e:
            logger.error(f"❌ Cache retrieval failed: {e}")
            return None
    
    def _cache_explanation(self, line_fingerprint: str, explanation: ExplanationOutput):
        """Cache explanation"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO explanation_cache 
                    (line_fingerprint, explanation_json, created_at, ttl_days)
                    VALUES (?, ?, ?, ?)
                """, (
                    line_fingerprint,
                    explanation.json(),
                    datetime.now().isoformat(),
                    self.cache_ttl_days
                ))
                
                conn.commit()
                logger.debug(f"Cached explanation for {line_fingerprint[:8]}...")
                
        except Exception as e:
            logger.error(f"❌ Cache storage failed: {e}")
    
    def _generate_explanation(self, verdict: str, context: Dict[str, Any]) -> Optional[ExplanationOutput]:
        """Generate deterministic explanation"""
        try:
            # Create engine facts hash
            facts_hash = self._compute_facts_hash(verdict, context)
            
            # Generate explanation based on verdict
            if verdict == "price_incoherent":
                headline = "Price calculation mismatch"
                explanation = "The calculated line total doesn't match the unit price × quantity."
                actions = [
                    {"label": "Review unit price", "reason": "Check for OCR errors in price extraction"},
                    {"label": "Verify quantity", "reason": "Confirm quantity parsing is correct"}
                ]
            
            elif verdict == "vat_mismatch":
                headline = "VAT calculation error"
                explanation = "The VAT amount doesn't match the expected calculation from the subtotal."
                actions = [
                    {"label": "Check VAT rate", "reason": "Verify VAT rate is correctly applied"},
                    {"label": "Review subtotal", "reason": "Confirm subtotal calculation is accurate"}
                ]
            
            elif verdict == "pack_mismatch":
                headline = "Pack quantity mismatch"
                explanation = "The pack descriptor doesn't match the actual quantity."
                actions = [
                    {"label": "Review pack info", "reason": "Check pack size and units per pack"},
                    {"label": "Verify quantity", "reason": "Confirm total quantity calculation"}
                ]
            
            elif verdict == "ocr_low_conf":
                headline = "Low OCR confidence"
                explanation = "The OCR confidence for this line is below the acceptable threshold."
                actions = [
                    {"label": "Review image quality", "reason": "Check for blur, rotation, or poor contrast"},
                    {"label": "Manual verification", "reason": "Verify extracted text manually"}
                ]
            
            elif verdict == "off_contract_discount":
                headline = "Off-contract discount detected"
                explanation = "This line shows a discount that's not covered by existing contract terms."
                actions = [
                    {"label": "Review discount", "reason": "Verify discount amount and reason"},
                    {"label": "Update contract", "reason": "Consider adding to supplier contract terms"}
                ]
            
            elif verdict == "ok_on_contract":
                headline = "Line item OK"
                explanation = "This line item matches expected contract terms and pricing."
                actions = [
                    {"label": "No action needed", "reason": "Line item is within expected parameters"}
                ]
            
            else:
                headline = "Unknown verdict"
                explanation = "The system assigned an unrecognized verdict to this line item."
                actions = [
                    {"label": "Manual review", "reason": "Review line item manually for unusual characteristics"}
                ]
            
            return ExplanationOutput(
                headline=headline,
                explanation=explanation,
                suggested_actions=actions,
                engine_verdict=verdict,
                engine_facts_hash=facts_hash,
                model_id="deterministic",
                prompt_hash="",
                response_hash=""
            )
            
        except Exception as e:
            logger.error(f"❌ Explanation generation failed: {e}")
            return None
    
    def _compute_facts_hash(self, verdict: str, context: Dict[str, Any]) -> str:
        """Compute hash of engine facts for consistency"""
        try:
            facts = {
                'verdict': verdict,
                'context_keys': sorted(context.keys()),
                'timestamp': datetime.now().isoformat()
            }
            
            facts_json = json.dumps(facts, sort_keys=True)
            return hashlib.sha256(facts_json.encode('utf-8')).hexdigest()
            
        except Exception as e:
            logger.error(f"❌ Facts hash computation failed: {e}")
            return ""
    
    def clear_expired_cache(self) -> int:
        """Clear expired cache entries and return count"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete expired entries
                cursor.execute("""
                    DELETE FROM explanation_cache 
                    WHERE datetime(created_at) < datetime('now', '-30 days')
                """)
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleared {deleted_count} expired cache entries")
                return deleted_count
                
        except Exception as e:
            logger.error(f"❌ Cache cleanup failed: {e}")
            return 0

# Global explainer instance
_explainer_engine: Optional[ExplainerEngine] = None

def get_explainer_engine() -> ExplainerEngine:
    """Get global explainer engine instance"""
    global _explainer_engine
    if _explainer_engine is None:
        _explainer_engine = ExplainerEngine()
    return _explainer_engine 