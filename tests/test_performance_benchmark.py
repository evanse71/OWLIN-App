#!/usr/bin/env python3
"""
Performance Benchmark Tests

Tests for the Owlin performance benchmarking suite,
including timing utilities, benchmark runner, and API endpoints.
"""

import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.performance.timing import (
    PerformanceTimer, time_stage, time_operation, BenchmarkLogger,
    get_safe_memory_usage, format_duration
)
from scripts.performance_benchmark import PerformanceBenchmark


class TestPerformanceTimer(unittest.TestCase):
    """Test performance timing utilities."""
    
    def test_performance_timer(self):
        """Test PerformanceTimer context manager."""
        metrics = {}
        
        with PerformanceTimer("test_stage", metrics):
            time.sleep(0.1)
        
        self.assertIn("test_stage_time", metrics)
        self.assertGreater(metrics["test_stage_time"], 0.09)
        self.assertLess(metrics["test_stage_time"], 0.2)
    
    def test_time_stage_decorator(self):
        """Test time_stage decorator."""
        metrics = {}
        
        @time_stage("decorated_stage")
        def test_function(metrics_dict):
            time.sleep(0.05)
            return "success"
        
        result = test_function(metrics)
        
        self.assertEqual(result, "success")
        self.assertIn("decorated_stage_time", metrics)
        self.assertGreater(metrics["decorated_stage_time"], 0.04)
    
    def test_time_operation_context(self):
        """Test time_operation context manager."""
        metrics = {}
        
        with time_operation("context_stage", metrics):
            time.sleep(0.05)
        
        self.assertIn("context_stage_time", metrics)
        self.assertGreater(metrics["context_stage_time"], 0.04)
    
    def test_format_duration(self):
        """Test duration formatting."""
        self.assertEqual(format_duration(0.5), "500.0ms")
        self.assertEqual(format_duration(1.5), "1.50s")
        self.assertEqual(format_duration(65.5), "1m 5.5s")


class TestBenchmarkLogger(unittest.TestCase):
    """Test benchmark logging functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.logger = BenchmarkLogger(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_ensure_benchmark_dir(self):
        """Test benchmark directory creation."""
        new_dir = os.path.join(self.temp_dir, "new_benchmark_dir")
        logger = BenchmarkLogger(new_dir)
        self.assertTrue(os.path.exists(new_dir))
    
    def test_log_benchmark_run(self):
        """Test benchmark result logging."""
        test_results = {
            "documents": [{"doc_id": "test1", "total_time": 1.5}],
            "summary": {"avg_total_time": 1.5}
        }
        
        filepath = self.logger.log_benchmark_run(test_results)
        
        self.assertTrue(os.path.exists(filepath))
        self.assertTrue(filepath.endswith(".json"))
        
        # Verify content
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.assertIn("timestamp", data)
        self.assertIn("benchmark_version", data)
        self.assertEqual(data["documents"], test_results["documents"])
    
    def test_get_latest_benchmark(self):
        """Test getting latest benchmark results."""
        # No benchmarks initially
        self.assertIsNone(self.logger.get_latest_benchmark())
        
        # Add a benchmark
        test_results = {"test": "data"}
        self.logger.log_benchmark_run(test_results)
        
        # Should now have the benchmark
        latest = self.logger.get_latest_benchmark()
        self.assertIsNotNone(latest)
        self.assertEqual(latest["test"], "data")


class TestPerformanceBenchmark(unittest.TestCase):
    """Test performance benchmark runner."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = os.path.join(self.temp_dir, "test.db")
        
        # Create test database
        import sqlite3
        con = sqlite3.connect(self.temp_db)
        cur = con.cursor()
        
        # Create tables
        cur.execute("""
            CREATE TABLE documents (
                id TEXT PRIMARY KEY,
                path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE invoices (
                id TEXT PRIMARY KEY,
                document_id TEXT,
                supplier TEXT,
                invoice_date TEXT,
                total_value REAL,
                ocr_confidence REAL,
                status TEXT
            )
        """)
        
        # Insert test data
        test_docs = [
            ("doc1", "test1.pdf", "2025-01-01"),
            ("doc2", "test2.pdf", "2025-01-02"),
            ("doc3", "test3.pdf", "2025-01-03")
        ]
        
        cur.executemany(
            "INSERT INTO documents (id, path, created_at) VALUES (?, ?, ?)",
            test_docs
        )
        
        test_invoices = [
            ("inv1", "doc1", "Test Supplier", "2025-01-01", 100.0, 0.9, "processed"),
            ("inv2", "doc2", "Test Supplier", "2025-01-02", 200.0, 0.8, "processed")
        ]
        
        cur.executemany(
            "INSERT INTO invoices (id, document_id, supplier, invoice_date, total_value, ocr_confidence, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            test_invoices
        )
        
        con.commit()
        con.close()
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_sample_documents(self):
        """Test document sampling."""
        benchmark = PerformanceBenchmark(self.temp_db, self.temp_dir)
        
        docs = benchmark.get_sample_documents(2)
        
        self.assertEqual(len(docs), 2)
        self.assertIn("doc_id", docs[0])
        self.assertIn("filename", docs[0])
        self.assertIn("file_path", docs[0])
    
    def test_simulate_pipeline_stage(self):
        """Test pipeline stage simulation."""
        benchmark = PerformanceBenchmark(self.temp_db, self.temp_dir)
        
        result = benchmark.simulate_pipeline_stage("test_stage", (0.01, 0.02))
        
        self.assertIn("stage", result)
        self.assertIn("duration", result)
        self.assertIn("success", result)
        self.assertEqual(result["stage"], "test_stage")
        self.assertGreater(result["duration"], 0.01)
        self.assertLess(result["duration"], 0.02)
    
    def test_benchmark_document(self):
        """Test single document benchmarking."""
        benchmark = PerformanceBenchmark(self.temp_db, self.temp_dir)
        
        test_doc = {
            "doc_id": "test_doc",
            "filename": "test.pdf",
            "file_path": "test.pdf",
            "invoice_data": None
        }
        
        result = benchmark.benchmark_document(test_doc)
        
        self.assertIn("doc_id", result)
        self.assertIn("success", result)
        self.assertIn("total_time", result)
        self.assertIn("metrics", result)
        self.assertEqual(result["doc_id"], "test_doc")
    
    def test_calculate_summary(self):
        """Test summary calculation."""
        benchmark = PerformanceBenchmark(self.temp_db, self.temp_dir)
        
        # Add test results
        benchmark.results["documents"] = [
            {
                "success": True,
                "total_time": 1.0,
                "metrics": {
                    "paddle_ocr_time": 0.3,
                    "llm_processing_time": 0.5
                },
                "memory_delta_mb": 10.0
            },
            {
                "success": False,
                "total_time": 2.0,
                "metrics": {
                    "paddle_ocr_time": 0.4,
                    "llm_processing_time": 0.6
                },
                "memory_delta_mb": 15.0
            }
        ]
        
        summary = benchmark.calculate_summary()
        
        self.assertEqual(summary["documents"], 2)
        self.assertEqual(summary["successful_documents"], 1)
        self.assertEqual(summary["success_rate"], 0.5)
        self.assertEqual(summary["avg_total_time"], 1.5)
        self.assertEqual(summary["avg_ocr_time"], 0.35)
        self.assertEqual(summary["avg_llm_time"], 0.55)


class TestPerformanceAPI(unittest.TestCase):
    """Test performance API endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test benchmark file
        test_data = {
            "timestamp": "2025-01-01T12:00:00Z",
            "summary": {
                "documents": 5,
                "success_rate": 0.8,
                "avg_total_time": 1.5,
                "avg_ocr_time": 0.3,
                "avg_llm_time": 0.7,
                "avg_memory_mb": 12.5
            },
            "feature_flags": {
                "htr_enabled": False,
                "donut_fallback": False,
                "llm_automation": True
            }
        }
        
        os.makedirs(self.temp_dir, exist_ok=True)
        test_file = os.path.join(self.temp_dir, "benchmark_run_20250101_120000.json")
        
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('backend.api.performance_router.BenchmarkLogger')
    def test_get_performance_summary(self, mock_logger_class):
        """Test performance summary endpoint."""
        from backend.api.performance_router import get_performance_summary
        
        # Mock the logger
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger
        
        # Mock benchmark data
        mock_benchmark = {
            "timestamp": "2025-01-01T12:00:00Z",
            "summary": {
                "documents": 5,
                "success_rate": 0.8,
                "avg_total_time": 1.5,
                "avg_ocr_time": 0.3,
                "avg_llm_time": 0.7,
                "avg_memory_mb": 12.5
            },
            "feature_flags": {
                "htr_enabled": False,
                "donut_fallback": False,
                "llm_automation": True
            }
        }
        
        mock_logger.get_latest_benchmark.return_value = mock_benchmark
        
        # Test the endpoint
        result = get_performance_summary()
        
        self.assertEqual(result["timestamp"], "2025-01-01T12:00:00Z")
        self.assertEqual(result["documents"], 5)
        self.assertEqual(result["avg_total_time"], 1.5)
        self.assertEqual(result["avg_ocr_time"], 0.3)
        self.assertEqual(result["avg_llm_time"], 0.7)
        self.assertEqual(result["avg_memory_mb"], 12.5)
        self.assertEqual(result["status"], "success")


class TestCommandParsingPerformance(unittest.TestCase):
    """Benchmark command parsing performance."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('backend.services.chat_service.CodeReader'), \
             patch('backend.services.chat_service.CodeExplorer'), \
             patch('backend.services.chat_service.CodeVerifier'), \
             patch('backend.services.chat_service.ResponseValidator'), \
             patch('backend.services.chat_service.RuntimeVerifier'), \
             patch('backend.services.chat_service.ArchitectureAnalyzer'), \
             patch('backend.services.chat_service.ResponseRewriter'), \
             patch('backend.services.chat_service.get_config'), \
             patch('backend.services.chat_service.RetryHandler'), \
             patch('backend.services.chat_service.get_registry'), \
             patch('backend.services.chat_service.ChatService._check_ollama_available', return_value=True):
            from backend.services.chat_service import ChatService
            self.chat_service = ChatService()
    
    def test_parse_large_response(self):
        """Benchmark parsing large response with many commands."""
        # Create a large response with 100 commands
        commands = []
        for i in range(100):
            commands.append(f"READ backend/file{i}.py")
            commands.append(f"SEARCH term{i}")
            commands.append(f"GREP pattern{i}")
        
        response = "\n".join(commands)
        
        start_time = time.time()
        parsed = self.chat_service._parse_agent_commands(response)
        elapsed = time.time() - start_time
        
        self.assertEqual(len(parsed), 300)  # 100 * 3 commands
        self.assertLess(elapsed, 1.0)  # Should complete in under 1 second
        print(f"Parsed 300 commands in {elapsed:.3f}s ({elapsed*1000/300:.2f}ms per command)")


class TestResultFormattingPerformance(unittest.TestCase):
    """Benchmark result formatting performance."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('backend.services.chat_service.CodeReader'), \
             patch('backend.services.chat_service.CodeExplorer'), \
             patch('backend.services.chat_service.CodeVerifier'), \
             patch('backend.services.chat_service.ResponseValidator'), \
             patch('backend.services.chat_service.RuntimeVerifier'), \
             patch('backend.services.chat_service.ArchitectureAnalyzer'), \
             patch('backend.services.chat_service.ResponseRewriter'), \
             patch('backend.services.chat_service.get_config'), \
             patch('backend.services.chat_service.RetryHandler'), \
             patch('backend.services.chat_service.get_registry'), \
             patch('backend.services.chat_service.ChatService._check_ollama_available', return_value=True):
            from backend.services.chat_service import ChatService
            self.chat_service = ChatService()
    
    def test_format_large_result_set(self):
        """Benchmark formatting large result set (1000+ results)."""
        # Create 1000 results
        results = []
        for i in range(1000):
            results.append({
                "type": "search",
                "file": f"backend/file{i}.py",
                "line": i * 10,
                "match": f"Found match {i}",
                "context": f"Context for match {i}" * 10
            })
        
        start_time = time.time()
        formatted = self.chat_service._format_findings(results)
        elapsed = time.time() - start_time
        
        self.assertIsNotNone(formatted)
        self.assertLess(elapsed, 5.0)  # Should complete in under 5 seconds
        print(f"Formatted 1000 results in {elapsed:.3f}s")
    
    def test_smart_truncate_large_content(self):
        """Benchmark smart truncation of large content."""
        # Create large content (100KB)
        large_content = "def function():\n" * 5000
        
        start_time = time.time()
        truncated = self.chat_service._smart_truncate_content(large_content, max_length=500)
        elapsed = time.time() - start_time
        
        self.assertLess(len(truncated), 1000)  # Should be truncated
        self.assertLess(elapsed, 0.5)  # Should complete quickly
        print(f"Truncated 100KB content in {elapsed:.3f}s")
    
    def test_deduplicate_large_result_set(self):
        """Benchmark deduplication of large result set."""
        # Create 1000 results with many duplicates
        results = []
        for i in range(1000):
            results.append({
                "type": "grep",
                "file": f"backend/file{i%10}.py",  # Only 10 unique files
                "line": (i % 10) * 10 + (i // 10),
                "match": f"Match {i}"
            })
        
        start_time = time.time()
        deduplicated = self.chat_service._deduplicate_results(results)
        elapsed = time.time() - start_time
        
        self.assertLess(len(deduplicated), len(results))  # Should have fewer results
        self.assertLess(elapsed, 2.0)  # Should complete in under 2 seconds
        print(f"Deduplicated 1000 results to {len(deduplicated)} in {elapsed:.3f}s")


class TestCachingPerformance(unittest.TestCase):
    """Benchmark caching effectiveness."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('backend.services.chat_service.CodeReader'), \
             patch('backend.services.chat_service.CodeExplorer'), \
             patch('backend.services.chat_service.CodeVerifier'), \
             patch('backend.services.chat_service.ResponseValidator'), \
             patch('backend.services.chat_service.RuntimeVerifier'), \
             patch('backend.services.chat_service.ArchitectureAnalyzer'), \
             patch('backend.services.chat_service.ResponseRewriter'), \
             patch('backend.services.chat_service.get_config'), \
             patch('backend.services.chat_service.RetryHandler'), \
             patch('backend.services.chat_service.get_registry'), \
             patch('backend.services.chat_service.ChatService._check_ollama_available', return_value=True):
            from backend.services.chat_service import ChatService
            self.chat_service = ChatService()
    
    def test_path_resolution_cache_hit_rate(self):
        """Benchmark path resolution cache hit rate."""
        test_paths = ["backend/main.py"] * 100
        
        # First pass (cache miss)
        start_time = time.time()
        for path in test_paths:
            with patch('os.path.exists', return_value=True):
                self.chat_service._resolve_file_path(path)
        first_pass_time = time.time() - start_time
        
        # Second pass (cache hit)
        start_time = time.time()
        for path in test_paths:
            with patch('os.path.exists', return_value=True):
                self.chat_service._resolve_file_path(path)
        second_pass_time = time.time() - start_time
        
        # Cache should make second pass faster
        self.assertLess(second_pass_time, first_pass_time)
        speedup = first_pass_time / second_pass_time if second_pass_time > 0 else float('inf')
        print(f"Path resolution cache speedup: {speedup:.2f}x (first: {first_pass_time:.3f}s, second: {second_pass_time:.3f}s)")
    
    def test_relevance_score_cache(self):
        """Benchmark relevance score caching."""
        result = {
            "type": "search",
            "file": "backend/main.py",
            "match": "test match",
            "line": 100
        }
        query = "test query"
        
        # First pass (cache miss)
        start_time = time.time()
        for _ in range(100):
            self.chat_service._score_result_relevance(result, query)
        first_pass_time = time.time() - start_time
        
        # Second pass (cache hit)
        start_time = time.time()
        for _ in range(100):
            self.chat_service._score_result_relevance(result, query)
        second_pass_time = time.time() - start_time
        
        # Cache should make second pass faster
        if second_pass_time > 0:
            speedup = first_pass_time / second_pass_time
            print(f"Relevance score cache speedup: {speedup:.2f}x")


class TestTimeoutHandlingPerformance(unittest.TestCase):
    """Benchmark timeout handling performance."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('backend.services.chat_service.CodeReader'), \
             patch('backend.services.chat_service.CodeExplorer'), \
             patch('backend.services.chat_service.CodeVerifier'), \
             patch('backend.services.chat_service.ResponseValidator'), \
             patch('backend.services.chat_service.RuntimeVerifier'), \
             patch('backend.services.chat_service.ArchitectureAnalyzer'), \
             patch('backend.services.chat_service.ResponseRewriter'), \
             patch('backend.services.chat_service.get_config'), \
             patch('backend.services.chat_service.RetryHandler'), \
             patch('backend.services.chat_service.get_registry'), \
             patch('backend.services.chat_service.ChatService._check_ollama_available', return_value=True):
            from backend.services.chat_service import ChatService
            self.chat_service = ChatService()
    
    def test_timeout_execution(self):
        """Benchmark timeout execution overhead."""
        def slow_function():
            time.sleep(0.1)
            return "result"
        
        start_time = time.time()
        result = self.chat_service._execute_with_timeout(
            slow_function,
            timeout=0.2,
            timeout_message="Timeout"
        )
        elapsed = time.time() - start_time
        
        self.assertEqual(result, "result")
        self.assertLess(elapsed, 0.15)  # Should complete before timeout
        print(f"Timeout execution completed in {elapsed:.3f}s")
    
    def test_timeout_cancellation(self):
        """Benchmark timeout cancellation overhead."""
        def slow_function():
            time.sleep(1.0)  # Will timeout
            return "result"
        
        start_time = time.time()
        result = self.chat_service._execute_with_timeout(
            slow_function,
            timeout=0.1,
            timeout_message="Timeout"
        )
        elapsed = time.time() - start_time
        
        self.assertIn("Timeout", result)
        self.assertLess(elapsed, 0.2)  # Should timeout quickly
        print(f"Timeout cancellation completed in {elapsed:.3f}s")


if __name__ == "__main__":
    unittest.main()
