# backend/htr/dataset.py
"""
HTR sample storage and dataset management.

This module provides SQLite-based storage for HTR training samples,
allowing collection of labeled data for future model training.
"""

from __future__ import annotations
import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .base import HTRSample, HTRModelType

LOGGER = logging.getLogger("owlin.htr.dataset")


class HTRSampleStorage:
    """SQLite-based storage for HTR training samples."""
    
    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """Initialize HTR sample storage."""
        self.db_path = Path(db_path) if db_path else Path("data/owlin.db")
        self._ensure_tables()
    
    def _ensure_tables(self) -> None:
        """Ensure required tables exist in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create htr_samples table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS htr_samples (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sample_id TEXT UNIQUE NOT NULL,
                        image_path TEXT NOT NULL,
                        ground_truth TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        model_used TEXT NOT NULL,
                        metadata TEXT,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )
                """)
                
                # Create htr_models table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS htr_models (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_name TEXT UNIQUE NOT NULL,
                        model_path TEXT NOT NULL,
                        model_type TEXT NOT NULL,
                        version TEXT,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )
                """)
                
                # Create htr_predictions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS htr_predictions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id TEXT NOT NULL,
                        page_num INTEGER NOT NULL,
                        block_id TEXT NOT NULL,
                        text TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        model_used TEXT NOT NULL,
                        bbox TEXT NOT NULL,
                        processing_time REAL NOT NULL,
                        created_at REAL NOT NULL
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_htr_samples_model ON htr_samples(model_used)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_htr_samples_confidence ON htr_samples(confidence)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_htr_predictions_doc ON htr_predictions(document_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_htr_predictions_page ON htr_predictions(page_num)")
                
                conn.commit()
                LOGGER.info("HTR database tables ensured")
                
        except Exception as e:
            LOGGER.error("Failed to ensure HTR tables: %s", e)
            raise
    
    def create_sample(self, image_path: str, ground_truth: str, 
                     confidence: float, model_used: HTRModelType,
                     metadata: Optional[Dict[str, Any]] = None) -> HTRSample:
        """Create a new HTR sample."""
        sample_id = f"htr_sample_{int(time.time() * 1000)}"
        
        return HTRSample(
            sample_id=sample_id,
            image_path=image_path,
            ground_truth=ground_truth,
            confidence=confidence,
            model_used=model_used,
            metadata=metadata or {}
        )
    
    def save_sample(self, sample: HTRSample) -> bool:
        """Save an HTR sample to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO htr_samples 
                    (sample_id, image_path, ground_truth, confidence, model_used, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sample.sample_id,
                    sample.image_path,
                    sample.ground_truth,
                    sample.confidence,
                    sample.model_used.value,
                    json.dumps(sample.metadata),
                    sample.created_at,
                    time.time()
                ))
                
                conn.commit()
                LOGGER.debug("Saved HTR sample: %s", sample.sample_id)
                return True
                
        except Exception as e:
            LOGGER.error("Failed to save HTR sample: %s", e)
            return False
    
    def get_samples(self, model_used: Optional[HTRModelType] = None,
                   min_confidence: Optional[float] = None,
                   max_confidence: Optional[float] = None,
                   limit: Optional[int] = None) -> List[HTRSample]:
        """Get HTR samples with optional filters."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM htr_samples WHERE 1=1"
                params = []
                
                if model_used:
                    query += " AND model_used = ?"
                    params.append(model_used.value)
                
                if min_confidence is not None:
                    query += " AND confidence >= ?"
                    params.append(min_confidence)
                
                if max_confidence is not None:
                    query += " AND confidence <= ?"
                    params.append(max_confidence)
                
                query += " ORDER BY created_at DESC"
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                samples = []
                for row in rows:
                    sample = HTRSample(
                        sample_id=row[1],
                        image_path=row[2],
                        ground_truth=row[3],
                        confidence=row[4],
                        model_used=HTRModelType(row[5]),
                        metadata=json.loads(row[6]) if row[6] else {},
                    )
                    sample.created_at = row[7]
                    samples.append(sample)
                
                return samples
                
        except Exception as e:
            LOGGER.error("Failed to get HTR samples: %s", e)
            return []
    
    def save_prediction(self, document_id: str, page_num: int, block_id: str,
                       text: str, confidence: float, model_used: HTRModelType,
                       bbox: List[int], processing_time: float) -> bool:
        """Save an HTR prediction to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO htr_predictions 
                    (document_id, page_num, block_id, text, confidence, model_used, bbox, processing_time, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    document_id,
                    page_num,
                    block_id,
                    text,
                    confidence,
                    model_used.value,
                    json.dumps(bbox),
                    processing_time,
                    time.time()
                ))
                
                conn.commit()
                LOGGER.debug("Saved HTR prediction: %s", block_id)
                return True
                
        except Exception as e:
            LOGGER.error("Failed to save HTR prediction: %s", e)
            return False
    
    def get_predictions(self, document_id: Optional[str] = None,
                       page_num: Optional[int] = None,
                       model_used: Optional[HTRModelType] = None,
                       limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get HTR predictions with optional filters."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM htr_predictions WHERE 1=1"
                params = []
                
                if document_id:
                    query += " AND document_id = ?"
                    params.append(document_id)
                
                if page_num is not None:
                    query += " AND page_num = ?"
                    params.append(page_num)
                
                if model_used:
                    query += " AND model_used = ?"
                    params.append(model_used.value)
                
                query += " ORDER BY created_at DESC"
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                predictions = []
                for row in rows:
                    prediction = {
                        "id": row[0],
                        "document_id": row[1],
                        "page_num": row[2],
                        "block_id": row[3],
                        "text": row[4],
                        "confidence": row[5],
                        "model_used": row[6],
                        "bbox": json.loads(row[7]),
                        "processing_time": row[8],
                        "created_at": row[9]
                    }
                    predictions.append(prediction)
                
                return predictions
                
        except Exception as e:
            LOGGER.error("Failed to get HTR predictions: %s", e)
            return []
    
    def export_samples_tsv(self, output_path: Union[str, Path],
                          model_used: Optional[HTRModelType] = None,
                          min_confidence: Optional[float] = None) -> bool:
        """Export samples to TSV format for training."""
        try:
            samples = self.get_samples(
                model_used=model_used,
                min_confidence=min_confidence
            )
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write("sample_id\timage_path\tground_truth\tconfidence\tmodel_used\tmetadata\n")
                
                # Write samples
                for sample in samples:
                    f.write(f"{sample.sample_id}\t")
                    f.write(f"{sample.image_path}\t")
                    f.write(f"{sample.ground_truth}\t")
                    f.write(f"{sample.confidence}\t")
                    f.write(f"{sample.model_used.value}\t")
                    f.write(f"{json.dumps(sample.metadata)}\n")
            
            LOGGER.info("Exported %d samples to %s", len(samples), output_path)
            return True
            
        except Exception as e:
            LOGGER.error("Failed to export samples: %s", e)
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get HTR storage statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get sample statistics
                cursor.execute("SELECT COUNT(*) FROM htr_samples")
                total_samples = cursor.fetchone()[0]
                
                cursor.execute("SELECT AVG(confidence) FROM htr_samples")
                avg_confidence = cursor.fetchone()[0] or 0.0
                
                cursor.execute("SELECT model_used, COUNT(*) FROM htr_samples GROUP BY model_used")
                model_counts = dict(cursor.fetchall())
                
                # Get prediction statistics
                cursor.execute("SELECT COUNT(*) FROM htr_predictions")
                total_predictions = cursor.fetchone()[0]
                
                cursor.execute("SELECT AVG(confidence) FROM htr_predictions")
                avg_prediction_confidence = cursor.fetchone()[0] or 0.0
                
                return {
                    "total_samples": total_samples,
                    "avg_sample_confidence": avg_confidence,
                    "model_counts": model_counts,
                    "total_predictions": total_predictions,
                    "avg_prediction_confidence": avg_prediction_confidence
                }
                
        except Exception as e:
            LOGGER.error("Failed to get HTR statistics: %s", e)
            return {}
    
    def cleanup_old_samples(self, days_old: int = 30) -> int:
        """Clean up old samples to save space."""
        try:
            cutoff_time = time.time() - (days_old * 24 * 60 * 60)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM htr_samples WHERE created_at < ?", (cutoff_time,))
                deleted_count = cursor.rowcount
                
                cursor.execute("DELETE FROM htr_predictions WHERE created_at < ?", (cutoff_time,))
                deleted_predictions = cursor.rowcount
                
                conn.commit()
                
                LOGGER.info("Cleaned up %d samples and %d predictions older than %d days",
                           deleted_count, deleted_predictions, days_old)
                
                return deleted_count + deleted_predictions
                
        except Exception as e:
            LOGGER.error("Failed to cleanup old samples: %s", e)
            return 0
