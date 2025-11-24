"""
Runtime Verifier Service

Actually checks runtime behavior by reading logs, querying database,
and testing API endpoints. Provides real runtime data to validate LLM claims.
"""

import logging
import sqlite3
import requests
import re
import os
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from contextlib import contextmanager

logger = logging.getLogger("owlin.services.runtime_verifier")


class RuntimeVerifier:
    """Service for verifying runtime behavior."""
    
    # Connection pool for database connections
    _connection_pool = {}
    _pool_lock = threading.Lock()
    
    def __init__(self, db_path: Optional[str] = None, log_dir: Optional[str] = None):
        """
        Initialize the runtime verifier.
        
        Args:
            db_path: Path to SQLite database (default: from env or "data/owlin.db")
            log_dir: Directory containing log files (default: from env or "data/logs")
        """
        import os
        from backend.services.explorer_config import get_config
        
        config = get_config()
        
        self.db_path = Path(db_path or os.getenv("OWLIN_DB_PATH", "data/owlin.db"))
        self.log_dir = Path(log_dir or os.getenv("OWLIN_LOG_DIR", "data/logs"))
        self.api_base_url = os.getenv("OWLIN_API_URL", "http://localhost:8000")
        
        # Configuration
        self.db_timeout = float(os.getenv("OWLIN_DB_TIMEOUT", "5.0"))  # 5 second timeout
        self.api_timeout = float(os.getenv("OWLIN_API_TIMEOUT", "5.0"))  # 5 second timeout
        self.api_max_retries = int(os.getenv("OWLIN_API_MAX_RETRIES", "3"))  # 3 retries
        self.api_retry_backoff_base = float(os.getenv("OWLIN_API_RETRY_BACKOFF", "1.0"))  # Base backoff in seconds
        
        # Create directories if they don't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"RuntimeVerifier initialized with db_path: {self.db_path}, log_dir: {self.log_dir}")
    
    @contextmanager
    def _get_db_connection(self, db_path: Path):
        """
        Get a database connection from the pool or create a new one.
        Uses connection pooling to reuse connections.
        
        Args:
            db_path: Path to the database file
            
        Yields:
            sqlite3.Connection: Database connection
        """
        db_key = str(db_path.absolute())
        conn = None
        
        try:
            with self._pool_lock:
                # Try to get connection from pool
                if db_key in self._connection_pool:
                    conn = self._connection_pool[db_key]
                    # Check if connection is still valid
                    try:
                        conn.execute("SELECT 1")
                    except sqlite3.Error:
                        # Connection is dead, remove from pool
                        try:
                            conn.close()
                        except:
                            pass
                        del self._connection_pool[db_key]
                        conn = None
                
                # Create new connection if needed
                if conn is None:
                    conn = sqlite3.connect(
                        str(db_path),
                        timeout=self.db_timeout,
                        check_same_thread=False
                    )
                    conn.row_factory = sqlite3.Row
                    self._connection_pool[db_key] = conn
            
            yield conn
        except Exception as e:
            # Remove bad connection from pool
            with self._pool_lock:
                if db_key in self._connection_pool:
                    try:
                        self._connection_pool[db_key].close()
                    except:
                        pass
                    del self._connection_pool[db_key]
            raise e
    
    def close_db_connection(self, db_path: Optional[str] = None):
        """
        Close a database connection in the pool.
        Useful for cleanup in tests.
        
        Args:
            db_path: Optional database path. If None, closes all connections.
        """
        with self._pool_lock:
            if db_path:
                db_key = str(Path(db_path).absolute())
                if db_key in self._connection_pool:
                    try:
                        self._connection_pool[db_key].close()
                    except:
                        pass
                    del self._connection_pool[db_key]
            else:
                # Close all connections
                for conn in self._connection_pool.values():
                    try:
                        conn.close()
                    except:
                        pass
                self._connection_pool.clear()
    
    def check_logs(
        self,
        search_pattern: str,
        log_file: Optional[str] = None,
        max_results: int = 20,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Search log files for a pattern.
        
        Args:
            search_pattern: Pattern to search for (regex or plain text)
            log_file: Optional specific log file. If None, searches all logs.
            max_results: Maximum number of results to return
            start_date: Optional start date for filtering log entries
            end_date: Optional end date for filtering log entries
            
        Returns:
            Dict with 'found', 'matches', 'count', and 'sample_matches'
        """
        matches = []
        
        # Determine which log files to search
        log_files = []
        if log_file:
            log_path = self.log_dir / log_file
            if log_path.exists():
                log_files = [log_path]
        else:
            # Search all log files in log directory
            if self.log_dir.exists():
                # Get current log files
                log_files = list(self.log_dir.glob("*.log"))
                
                # Get rotated logs (app.log.1, app.log.2, etc.) and sort by modification time
                rotated_logs = list(self.log_dir.glob("*.log.*"))
                # Sort rotated logs by name (which typically includes rotation number)
                rotated_logs.sort(key=lambda p: p.name, reverse=True)
                log_files.extend(rotated_logs)
        
        if not log_files:
            return {
                "found": False,
                "error": f"Log directory not found or empty: {self.log_dir}",
                "matches": [],
                "count": 0
            }
        
        # Compile regex pattern
        try:
            regex = re.compile(search_pattern, re.IGNORECASE)
        except re.error:
            # If not valid regex, use plain text search
            regex = None
            search_lower = search_pattern.lower()
        
        # Search each log file
        for log_path in log_files:
            try:
                with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    for line_num, line in enumerate(f, 1):
                        if len(matches) >= max_results:
                            break
                        
                        # Extract timestamp for date filtering
                        timestamp_str = self._extract_timestamp(line)
                        timestamp_dt = None
                        
                        if timestamp_str:
                            timestamp_dt = self._parse_timestamp(timestamp_str)
                        
                        # Apply date filtering if specified
                        if start_date and timestamp_dt:
                            if timestamp_dt < start_date:
                                continue
                        if end_date and timestamp_dt:
                            if timestamp_dt > end_date:
                                continue
                        
                        # Check if line matches pattern
                        matches_pattern = False
                        if regex:
                            if regex.search(line):
                                matches_pattern = True
                        else:
                            if search_lower in line.lower():
                                matches_pattern = True
                        
                        if matches_pattern:
                            matches.append({
                                "file": str(log_path.name),
                                "line": line_num,
                                "content": line.strip(),
                                "timestamp": timestamp_str
                            })
            except Exception as e:
                logger.warning(f"Error reading log file {log_path}: {e}")
                continue
        
        return {
            "found": len(matches) > 0,
            "matches": matches,
            "count": len(matches),
            "pattern": search_pattern,
            "files_searched": len(log_files),
            "date_filtered": start_date is not None or end_date is not None
        }
    
    def query_database(
        self,
        query: str,
        db_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a read-only SQL query on the database.
        
        Args:
            query: SQL query to execute (must be SELECT only)
            db_path: Optional database path. If None, uses default.
            
        Returns:
            Dict with 'success', 'results', 'row_count', 'columns', and validation info
        """
        # Security: Only allow SELECT queries
        query_upper = query.strip().upper()
        if not query_upper.startswith('SELECT'):
            return {
                "success": False,
                "error": "Only SELECT queries are allowed for safety",
                "query": query
            }
        
        # Check for dangerous operations
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return {
                    "success": False,
                    "error": f"Query contains dangerous keyword: {keyword}",
                    "query": query
                }
        
        db_file = Path(db_path) if db_path else self.db_path
        
        if not db_file.exists():
            return {
                "success": False,
                "error": f"Database file not found: {db_file}. Check OWLIN_DB_PATH environment variable.",
                "query": query
            }
        
        try:
            # Use connection pool
            with self._get_db_connection(db_file) as conn:
                cursor = conn.cursor()
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                # Get column names
                columns = [description[0] for description in cursor.description] if cursor.description else []
                
                # Convert rows to dictionaries
                results = [dict(row) for row in rows]
                
                # Validate query results
                validation = self._validate_query_results(results, columns)
                
                return {
                    "success": True,
                    "results": results,
                    "row_count": len(results),
                    "columns": columns,
                    "query": query,
                    "validation": validation
                }
        except sqlite3.OperationalError as e:
            error_msg = str(e)
            if "database is locked" in error_msg.lower() or "timeout" in error_msg.lower():
                return {
                    "success": False,
                    "error": f"Database timeout or lock: {error_msg}",
                    "query": query
                }
            return {
                "success": False,
                "error": f"Database error: {error_msg}",
                "query": query
            }
        except sqlite3.Error as e:
            return {
                "success": False,
                "error": f"Database error: {str(e)}",
                "query": query
            }
        except Exception as e:
            logger.error(f"Error executing database query: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "query": query
            }
    
    def test_api_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Test an API endpoint and return the response.
        Uses retry logic with exponential backoff for transient failures.
        
        Args:
            endpoint: API endpoint path (e.g., "/api/health")
            method: HTTP method (GET, POST, etc.)
            payload: Optional request payload
            headers: Optional request headers
            
        Returns:
            Dict with 'success', 'status_code', 'response', 'error', and 'retry_count'
        """
        url = f"{self.api_base_url}{endpoint}"
        method_upper = method.upper()
        
        # Determine if method should retry on failure
        # Don't retry on 4xx errors (client errors), only on 5xx and connection errors
        retry_count = 0
        last_error = None
        
        for attempt in range(self.api_max_retries + 1):  # +1 for initial attempt
            try:
                if method_upper == "GET":
                    response = requests.get(url, headers=headers, timeout=self.api_timeout)
                elif method_upper == "POST":
                    response = requests.post(url, json=payload, headers=headers, timeout=self.api_timeout)
                elif method_upper == "PUT":
                    response = requests.put(url, json=payload, headers=headers, timeout=self.api_timeout)
                elif method_upper == "DELETE":
                    response = requests.delete(url, headers=headers, timeout=self.api_timeout)
                else:
                    return {
                        "success": False,
                        "error": f"Unsupported HTTP method: {method}",
                        "endpoint": endpoint,
                        "retry_count": retry_count
                    }
                
                # Check if we should retry based on status code
                # Don't retry on 4xx errors (client errors)
                if 400 <= response.status_code < 500:
                    # Client error, don't retry
                    try:
                        response_data = response.json()
                    except:
                        response_data = response.text
                    
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "response": response_data,
                        "headers": dict(response.headers),
                        "endpoint": endpoint,
                        "method": method,
                        "retry_count": retry_count
                    }
                
                # Success or 5xx error (server error - may retry)
                if response.status_code < 400:
                    # Success
                    try:
                        response_data = response.json()
                    except:
                        response_data = response.text
                    
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "response": response_data,
                        "headers": dict(response.headers),
                        "endpoint": endpoint,
                        "method": method,
                        "retry_count": retry_count
                    }
                else:
                    # 5xx error - may retry if we have attempts left
                    if attempt < self.api_max_retries:
                        retry_count += 1
                        backoff_time = self.api_retry_backoff_base * (2 ** attempt)
                        logger.warning(
                            f"API endpoint {endpoint} returned {response.status_code}, "
                            f"retrying in {backoff_time}s (attempt {attempt + 1}/{self.api_max_retries})"
                        )
                        time.sleep(backoff_time)
                        continue
                    else:
                        # Max retries reached
                        try:
                            response_data = response.json()
                        except:
                            response_data = response.text
                        
                        return {
                            "success": False,
                            "status_code": response.status_code,
                            "response": response_data,
                            "headers": dict(response.headers),
                            "endpoint": endpoint,
                            "method": method,
                            "retry_count": retry_count,
                            "error": f"Server error after {retry_count} retries"
                        }
                
            except requests.exceptions.ConnectionError as e:
                last_error = e
                if attempt < self.api_max_retries:
                    retry_count += 1
                    backoff_time = self.api_retry_backoff_base * (2 ** attempt)
                    logger.warning(
                        f"Connection error to {endpoint}, "
                        f"retrying in {backoff_time}s (attempt {attempt + 1}/{self.api_max_retries})"
                    )
                    time.sleep(backoff_time)
                    continue
                else:
                    return {
                        "success": False,
                        "error": f"Could not connect to API at {self.api_base_url} after {retry_count} retries",
                        "endpoint": endpoint,
                        "retry_count": retry_count
                    }
            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < self.api_max_retries:
                    retry_count += 1
                    backoff_time = self.api_retry_backoff_base * (2 ** attempt)
                    logger.warning(
                        f"Timeout for {endpoint}, "
                        f"retrying in {backoff_time}s (attempt {attempt + 1}/{self.api_max_retries})"
                    )
                    time.sleep(backoff_time)
                    continue
                else:
                    return {
                        "success": False,
                        "error": f"Request to {endpoint} timed out after {retry_count} retries",
                        "endpoint": endpoint,
                        "retry_count": retry_count
                    }
            except Exception as e:
                last_error = e
                logger.error(f"Error testing API endpoint {endpoint}: {e}")
                if attempt < self.api_max_retries:
                    retry_count += 1
                    backoff_time = self.api_retry_backoff_base * (2 ** attempt)
                    time.sleep(backoff_time)
                    continue
                else:
                    return {
                        "success": False,
                        "error": f"Unexpected error after {retry_count} retries: {str(e)}",
                        "endpoint": endpoint,
                        "retry_count": retry_count
                    }
        
        # Should not reach here, but handle it
        return {
            "success": False,
            "error": f"Failed after {retry_count} retries: {str(last_error) if last_error else 'Unknown error'}",
            "endpoint": endpoint,
            "retry_count": retry_count
        }
    
    def verify_data_exists(
        self,
        table: str,
        conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify that data exists in a table matching given conditions.
        
        Args:
            table: Table name
            conditions: Dict of column:value conditions
            
        Returns:
            Dict with 'exists', 'count', and 'sample_rows'
        """
        # Build WHERE clause
        where_parts = []
        params = []
        for column, value in conditions.items():
            if isinstance(value, str):
                where_parts.append(f"{column} = ?")
                params.append(value)
            else:
                where_parts.append(f"{column} = ?")
                params.append(value)
        
        where_clause = " AND ".join(where_parts)
        query = f"SELECT * FROM {table} WHERE {where_clause} LIMIT 10"
        
        result = self.query_database(query)
        
        if not result.get("success"):
            return {
                "exists": False,
                "error": result.get("error"),
                "count": 0
            }
        
        rows = result.get("results", [])
        
        return {
            "exists": len(rows) > 0,
            "count": len(rows),
            "sample_rows": rows[:5],  # Return first 5 rows
            "table": table,
            "conditions": conditions
        }
    
    def _extract_timestamp(self, line: str) -> Optional[str]:
        """Extract timestamp from log line if present."""
        # Common timestamp patterns
        timestamp_patterns = [
            r'(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})',
            r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})',
            r'\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]'
        ]
        
        for pattern in timestamp_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)
        
        return None
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """
        Parse timestamp string into datetime object.
        
        Args:
            timestamp_str: Timestamp string from log line
            
        Returns:
            datetime object or None if parsing fails
        """
        # Common timestamp formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f"  # With microseconds
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def _validate_query_results(
        self,
        results: List[Dict[str, Any]],
        columns: List[str]
    ) -> Dict[str, Any]:
        """
        Validate query results for consistency and correctness.
        
        Args:
            results: List of result rows as dictionaries
            columns: List of column names
            
        Returns:
            Dict with validation information
        """
        validation = {
            "row_count": len(results),
            "column_count": len(columns),
            "has_results": len(results) > 0,
            "column_names": columns,
            "data_types": {},
            "warnings": []
        }
        
        if not results:
            validation["warnings"].append("Query returned no results")
            return validation
        
        # Validate column consistency
        if columns:
            # Check that all rows have the same columns
            for i, row in enumerate(results):
                row_keys = set(row.keys())
                expected_keys = set(columns)
                if row_keys != expected_keys:
                    validation["warnings"].append(
                        f"Row {i} has inconsistent columns: expected {expected_keys}, got {row_keys}"
                    )
        
        # Analyze data types in first few rows
        sample_size = min(10, len(results))
        type_counts = {}
        
        for row in results[:sample_size]:
            for col, value in row.items():
                if col not in type_counts:
                    type_counts[col] = {}
                
                value_type = type(value).__name__
                type_counts[col][value_type] = type_counts[col].get(value_type, 0) + 1
        
        # Determine most common type for each column
        for col, types in type_counts.items():
            if types:
                most_common_type = max(types.items(), key=lambda x: x[1])[0]
                validation["data_types"][col] = most_common_type
        
        # Check for suspicious results
        if len(results) > 10000:
            validation["warnings"].append(f"Large result set: {len(results)} rows")
        
        return validation

