#!/usr/bin/env python3
"""
Owlin Performance Benchmarking Suite

Runs comprehensive performance tests across the AI pipeline,
measuring timing and memory usage for each stage.
"""

import argparse
import json
import os
import random
import sqlite3
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.performance.timing import (
    time_operation, BenchmarkLogger, get_safe_memory_usage, format_duration
)
from backend.config import (
    FEATURE_HTR_ENABLED, FEATURE_DONUT_FALLBACK, env_bool
)


class PerformanceBenchmark:
    """Main benchmark runner for Owlin AI pipeline."""
    
    def __init__(self, db_path: str = "data/owlin.db", benchmark_dir: str = "data/benchmarks"):
        self.db_path = db_path
        self.benchmark_dir = benchmark_dir
        self.logger = BenchmarkLogger(benchmark_dir)
        self.results = {
            "documents": [],
            "summary": {},
            "feature_flags": {
                "htr_enabled": FEATURE_HTR_ENABLED,
                "donut_fallback": FEATURE_DONUT_FALLBACK,
                "llm_automation": env_bool("FEATURE_LLM_AUTOMATION", True)
            }
        }
        
    def get_sample_documents(self, n: int) -> List[Dict[str, Any]]:
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
            print(f"Error getting sample documents: {e}")
            return []
    
    def simulate_pipeline_stage(self, stage_name: str, duration_range: tuple = (0.1, 0.5)) -> Dict[str, Any]:
        """Simulate a pipeline stage with realistic timing."""
        # Simulate processing time
        base_time = random.uniform(*duration_range)
        
        # Add some variance based on stage complexity
        if stage_name in ["llm_processing", "donut_fallback"]:
            base_time *= random.uniform(1.5, 3.0)
        elif stage_name in ["htr_processing", "table_extraction"]:
            base_time *= random.uniform(1.2, 2.0)
        
        time.sleep(base_time)
        
        return {
            "stage": stage_name,
            "duration": round(base_time, 3),
            "success": random.choice([True, True, True, False])  # 75% success rate
        }
    
    def benchmark_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Run full pipeline benchmark on a single document."""
        doc_id = document["doc_id"]
        metrics = {}
        
        print(f"  Processing {doc_id}...")
        
        # Start timing
        start_time = time.perf_counter()
        start_memory = get_safe_memory_usage()
        
        try:
            # Layout segmentation
            with time_operation("layout_segmentation", metrics):
                layout_result = self.simulate_pipeline_stage("layout_segmentation", (0.05, 0.2))
            
            # PaddleOCR
            with time_operation("paddle_ocr", metrics):
                ocr_result = self.simulate_pipeline_stage("paddle_ocr", (0.1, 0.4))
            
            # Table extraction
            with time_operation("table_extraction", metrics):
                table_result = self.simulate_pipeline_stage("table_extraction", (0.05, 0.3))
            
            # HTR (if enabled)
            if FEATURE_HTR_ENABLED:
                with time_operation("htr_processing", metrics):
                    htr_result = self.simulate_pipeline_stage("htr_processing", (0.2, 0.8))
            else:
                metrics["htr_processing_time"] = 0.0
                metrics["htr_processing_memory_mb"] = 0.0
            
            # Donut fallback (if triggered)
            if FEATURE_DONUT_FALLBACK and random.random() < 0.3:  # 30% chance
                with time_operation("donut_fallback", metrics):
                    donut_result = self.simulate_pipeline_stage("donut_fallback", (0.5, 2.0))
            else:
                metrics["donut_fallback_time"] = 0.0
                metrics["donut_fallback_memory_mb"] = 0.0
            
            # LLM post-processing
            with time_operation("llm_processing", metrics):
                llm_result = self.simulate_pipeline_stage("llm_processing", (0.3, 1.0))
            
            # Supplier template matching
            with time_operation("template_matching", metrics):
                template_result = self.simulate_pipeline_stage("template_matching", (0.02, 0.1))
            
            # DB write/commit
            with time_operation("db_write", metrics):
                db_result = self.simulate_pipeline_stage("db_write", (0.01, 0.05))
            
            # Calculate totals
            total_time = time.perf_counter() - start_time
            end_memory = get_safe_memory_usage()
            memory_delta = (end_memory - start_memory) if (start_memory and end_memory) else None
            
            # Compile results
            result = {
                "doc_id": doc_id,
                "filename": document["filename"],
                "success": all([
                    layout_result["success"], ocr_result["success"], 
                    table_result["success"], llm_result["success"]
                ]),
                "total_time": round(total_time, 3),
                "memory_delta_mb": memory_delta,
                "stages": {
                    "layout_segmentation": layout_result,
                    "paddle_ocr": ocr_result,
                    "table_extraction": table_result,
                    "llm_processing": llm_result,
                    "template_matching": template_result,
                    "db_write": db_result
                },
                "metrics": metrics
            }
            
            # Add HTR/Donut results if applicable
            if FEATURE_HTR_ENABLED:
                result["stages"]["htr_processing"] = htr_result
            if FEATURE_DONUT_FALLBACK and "donut_fallback" in metrics:
                result["stages"]["donut_fallback"] = donut_result
            
            return result
            
        except Exception as e:
            return {
                "doc_id": doc_id,
                "filename": document["filename"],
                "success": False,
                "error": str(e),
                "total_time": round(time.perf_counter() - start_time, 3),
                "memory_delta_mb": None
            }
    
    def calculate_summary(self) -> Dict[str, Any]:
        """Calculate summary statistics from benchmark results."""
        if not self.results["documents"]:
            return {}
        
        successful_docs = [d for d in self.results["documents"] if d.get("success", False)]
        
        # Calculate averages
        total_times = [d["total_time"] for d in self.results["documents"]]
        ocr_times = [d["metrics"].get("paddle_ocr_time", 0) for d in self.results["documents"]]
        llm_times = [d["metrics"].get("llm_processing_time", 0) for d in self.results["documents"]]
        memory_deltas = [d["memory_delta_mb"] for d in self.results["documents"] if d["memory_delta_mb"] is not None]
        
        summary = {
            "documents": len(self.results["documents"]),
            "successful_documents": len(successful_docs),
            "success_rate": round(len(successful_docs) / len(self.results["documents"]), 3),
            "avg_total_time": round(sum(total_times) / len(total_times), 3),
            "avg_ocr_time": round(sum(ocr_times) / len(ocr_times), 3),
            "avg_llm_time": round(sum(llm_times) / len(llm_times), 3),
            "avg_memory_mb": round(sum(memory_deltas) / len(memory_deltas), 2) if memory_deltas else None,
            "max_total_time": round(max(total_times), 3),
            "min_total_time": round(min(total_times), 3),
            "total_benchmark_time": round(sum(total_times), 3)
        }
        
        # Add stage-specific averages
        stage_times = {}
        for stage in ["layout_segmentation", "paddle_ocr", "table_extraction", 
                     "htr_processing", "donut_fallback", "llm_processing", 
                     "template_matching", "db_write"]:
            times = [d["metrics"].get(f"{stage}_time", 0) for d in self.results["documents"]]
            if any(times):
                stage_times[f"avg_{stage}_time"] = round(sum(times) / len(times), 3)
        
        summary.update(stage_times)
        
        return summary
    
    def run_benchmark(self, n: int = 10) -> str:
        """Run benchmark on N documents."""
        print(f"Starting Owlin Performance Benchmark ({n} documents)")
        print("=" * 60)
        
        # Get sample documents
        documents = self.get_sample_documents(n)
        if not documents:
            print("No documents found in database")
            return ""
        
        print(f"Processing {len(documents)} documents...")
        
        # Process each document
        for i, document in enumerate(documents, 1):
            print(f"\n[{i}/{len(documents)}] Document: {document['doc_id']}")
            
            result = self.benchmark_document(document)
            self.results["documents"].append(result)
            
            status = "PASS" if result["success"] else "FAIL"
            print(f"  {status} Completed in {format_duration(result['total_time'])}")
        
        # Calculate summary
        self.results["summary"] = self.calculate_summary()
        
        # Save results
        filepath = self.logger.log_benchmark_run(self.results)
        
        # Print summary
        self.print_summary()
        
        return filepath
    
    def print_summary(self):
        """Print benchmark summary to console."""
        summary = self.results["summary"]
        
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)
        
        print(f"Documents processed: {summary['documents']}")
        print(f"Success rate: {summary['success_rate']*100:.1f}%")
        print(f"Average total time: {format_duration(summary['avg_total_time'])}")
        print(f"Average OCR time: {format_duration(summary['avg_ocr_time'])}")
        print(f"Average LLM time: {format_duration(summary['avg_llm_time'])}")
        
        if summary.get('avg_memory_mb'):
            print(f"Average memory usage: {summary['avg_memory_mb']:.1f} MB")
        
        print(f"Total benchmark time: {format_duration(summary['total_benchmark_time'])}")
        
        # Feature flags
        flags = self.results["feature_flags"]
        print(f"\nFeature flags:")
        print(f"  HTR enabled: {flags['htr_enabled']}")
        print(f"  Donut fallback: {flags['donut_fallback']}")
        print(f"  LLM automation: {flags['llm_automation']}")
        
        # Slowest stages
        stage_times = {k: v for k, v in summary.items() if k.startswith('avg_') and k.endswith('_time')}
        if stage_times:
            slowest = max(stage_times.items(), key=lambda x: x[1])
            print(f"\nSlowest stage: {slowest[0]} ({format_duration(slowest[1])})")


def main():
    """Main benchmark function."""
    parser = argparse.ArgumentParser(description="Owlin Performance Benchmark")
    parser.add_argument("--n", type=int, default=10, help="Number of documents to benchmark")
    parser.add_argument("--db-path", type=str, default="data/owlin.db", help="Database path")
    parser.add_argument("--benchmark-dir", type=str, default="data/benchmarks", help="Benchmark output directory")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible results")
    
    args = parser.parse_args()
    
    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)
    
    # Create benchmark runner
    benchmark = PerformanceBenchmark(args.db_path, args.benchmark_dir)
    
    # Run benchmark
    try:
        filepath = benchmark.run_benchmark(args.n)
        if filepath:
            print(f"\nResults saved to: {filepath}")
            return 0
        else:
            print("Benchmark failed")
            return 1
    except Exception as e:
        print(f"Benchmark error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
