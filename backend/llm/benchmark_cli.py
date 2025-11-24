#!/usr/bin/env python3
"""
LLM Benchmark CLI

Samples N documents from SQLite and runs LLM processing to generate performance metrics.
Outputs JSON report to stdout for analysis.
"""

import argparse
import json
import logging
import random
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from backend.llm.ocr_llm_integration import OCRLLMIntegration
from backend.llm.local_llm import LLMConfig, LLMProvider, LLMDevice
from backend.config import env_str

# Setup logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise during benchmarking
LOGGER = logging.getLogger("owlin.llm.benchmark")


class LLMBenchmark:
    """LLM benchmark runner."""
    
    def __init__(self, model_path: str, db_path: str = "data/owlin.db"):
        """Initialize benchmark with model and database paths."""
        self.model_path = model_path
        self.db_path = db_path
        self.integration = None
        
    def _initialize_integration(self) -> bool:
        """Initialize LLM integration."""
        try:
            # Create LLM config
            config = LLMConfig(
                model_path=self.model_path,
                provider=LLMProvider.LLAMA_CPP,
                device=LLMDevice.AUTO
            )
            
            # Create integration
            self.integration = OCRLLMIntegration([config])
            
            # Validate integration
            validation = self.integration.validate_integration()
            if not validation["integration_ready"]:
                LOGGER.warning("LLM integration not ready, using mock mode")
                return False
                
            return True
            
        except Exception as e:
            LOGGER.warning(f"Failed to initialize LLM integration: {e}")
            return False
    
    def _get_sample_documents(self, n: int) -> List[Dict[str, Any]]:
        """Get random sample of N documents from database."""
        try:
            con = sqlite3.connect(self.db_path, check_same_thread=False)
            cur = con.cursor()
            
            # Get all document IDs
            cur.execute("SELECT id, path FROM documents WHERE id IS NOT NULL ORDER BY created_at DESC")
            all_docs = cur.fetchall()
            
            if not all_docs:
                con.close()
                return []
            
            # Sample N documents (or all if less than N)
            sample_size = min(n, len(all_docs))
            sampled_docs = random.sample(all_docs, sample_size)
            
            # Get invoice data for sampled documents
            doc_ids = [doc[0] for doc in sampled_docs]
            placeholders = ",".join("?" * len(doc_ids))
            
            cur.execute(f"""
                SELECT document_id, supplier, invoice_date, total_value, ocr_confidence, status
                FROM invoices 
                WHERE document_id IN ({placeholders})
            """, doc_ids)
            
            invoice_data = {row[0]: row[1:] for row in cur.fetchall()}
            
            con.close()
            
            # Combine document and invoice data
            documents = []
            for doc_id, file_path in sampled_docs:
                invoice = invoice_data.get(doc_id)
                documents.append({
                    "doc_id": doc_id,
                    "filename": file_path.split('/')[-1] if file_path else "unknown",
                    "file_path": file_path,
                    "invoice_data": {
                        "supplier": invoice[0] if invoice else None,
                        "date": invoice[1] if invoice else None,
                        "value": invoice[2] if invoice else None,
                        "confidence": invoice[3] if invoice else None,
                        "status": invoice[4] if invoice else None
                    } if invoice else None
                })
            
            return documents
            
        except Exception as e:
            LOGGER.error(f"Failed to get sample documents: {e}")
            return []
    
    def _process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single document with LLM integration."""
        start_time = time.time()
        
        try:
            # Prepare OCR data
            raw_ocr_data = {
                "supplier": document["invoice_data"]["supplier"] if document["invoice_data"] else "Unknown",
                "invoice_date": document["invoice_data"]["date"] if document["invoice_data"] else None,
                "total_amount": document["invoice_data"]["value"] if document["invoice_data"] else None,
                "confidence": document["invoice_data"]["confidence"] if document["invoice_data"] else 0.5,
                "filename": document["filename"],
                "file_path": document["file_path"]
            }
            
            # Prepare context
            context = {
                "doc_id": document["doc_id"],
                "filename": document["filename"]
            }
            
            # Process with LLM integration
            result = self.integration.process_document(
                raw_ocr_data=raw_ocr_data,
                context=context,
                enable_llm_processing=True,
                enable_automation=True
            )
            
            processing_time = time.time() - start_time
            
            # Calculate F1 score (simplified - in real scenario would compare against ground truth)
            f1_score = None
            if result.success and result.final_invoice_card:
                # Simple F1 calculation based on confidence and completeness
                confidence = result.confidence_routing_result.overall_confidence if result.confidence_routing_result else 0.5
                completeness = len([k for k, v in result.final_invoice_card.items() if v is not None]) / 10.0  # Assume 10 key fields
                f1_score = 2 * (confidence * completeness) / (confidence + completeness) if (confidence + completeness) > 0 else 0
            
            return {
                "doc_id": document["doc_id"],
                "success": result.success,
                "time_s": round(processing_time, 3),
                "f1": round(f1_score, 3) if f1_score is not None else None,
                "processing_time": result.total_processing_time,
                "ocr_time": result.confidence_routing_result.processing_time if result.confidence_routing_result else 0,
                "llm_time": result.llm_pipeline_result.processing_time if result.llm_pipeline_result else 0,
                "review_queue_size": len(result.review_queue),
                "automation_artifacts_count": len(result.automation_artifacts),
                "errors": result.errors,
                "warnings": result.warnings
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            return {
                "doc_id": document["doc_id"],
                "success": False,
                "time_s": round(processing_time, 3),
                "f1": None,
                "error": str(e)
            }
    
    def run_benchmark(self, n: int) -> Dict[str, Any]:
        """Run benchmark on N documents."""
        start_time = time.time()
        
        # Initialize integration
        if not self._initialize_integration():
            LOGGER.warning("Using mock LLM integration for benchmark")
        
        # Get sample documents
        documents = self._get_sample_documents(n)
        if not documents:
            return {
                "n": 0,
                "took_s": 0.0,
                "items": [],
                "error": "No documents found in database"
            }
        
        # Process documents
        items = []
        for i, document in enumerate(documents):
            LOGGER.info(f"Processing document {i+1}/{len(documents)}: {document['doc_id']}")
            
            item = self._process_document(document)
            items.append(item)
        
        total_time = time.time() - start_time
        
        # Calculate summary statistics
        successful = sum(1 for item in items if item["success"])
        total_processing_time = sum(item["time_s"] for item in items)
        avg_f1 = sum(item["f1"] for item in items if item["f1"] is not None) / len([item for item in items if item["f1"] is not None]) if any(item["f1"] is not None for item in items) else None
        
        return {
            "n": len(documents),
            "took_s": round(total_time, 3),
            "success_rate": round(successful / len(documents), 3),
            "avg_processing_time": round(total_processing_time / len(documents), 3),
            "avg_f1": round(avg_f1, 3) if avg_f1 is not None else None,
            "items": items
        }


def main():
    """Main benchmark function."""
    parser = argparse.ArgumentParser(description="LLM Benchmark CLI")
    parser.add_argument("--model-path", type=str, 
                       default=env_str("OWLIN_LLM_MODEL", "models/llama-2-7b-chat.Q4_K_M.gguf"),
                       help="Path to LLM model file")
    parser.add_argument("--db-path", type=str, default="data/owlin.db",
                       help="Path to SQLite database")
    parser.add_argument("--n", type=int, default=10,
                       help="Number of documents to sample")
    parser.add_argument("--seed", type=int, default=None,
                       help="Random seed for reproducible results")
    
    args = parser.parse_args()
    
    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)
    
    # Create benchmark runner
    benchmark = LLMBenchmark(args.model_path, args.db_path)
    
    # Run benchmark
    try:
        result = benchmark.run_benchmark(args.n)
        
        # Output JSON to stdout
        print(json.dumps(result, indent=2))
        
        return 0 if result.get("n", 0) > 0 else 1
        
    except Exception as e:
        error_result = {
            "n": 0,
            "took_s": 0.0,
            "items": [],
            "error": str(e)
        }
        print(json.dumps(error_result, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())



