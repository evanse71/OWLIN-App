import httpx
import subprocess
import sys
import time
import os
import signal
import pytest

@pytest.fixture(scope="module")
def server():
    """Start the single-port server for testing"""
    proc = subprocess.Popen([sys.executable, "-m", "backend.final_single_port"])
    time.sleep(1.5)
    yield proc
    if proc.poll() is None:
        if os.name == "nt":
            proc.terminate()
        else:
            os.kill(proc.pid, signal.SIGTERM)

def j(url):
    """Helper to get JSON from URL"""
    return httpx.get(url, timeout=5).json()

def test_health(server):
    """Test health endpoint"""
    assert j("http://127.0.0.1:8001/api/health")["ok"] is True

def test_status(server):
    """Test status endpoint"""
    s = j("http://127.0.0.1:8001/api/status")
    assert "api_mounted" in s
    assert "ok" in s

def test_root(server):
    """Test root endpoint"""
    response = httpx.get("http://127.0.0.1:8001", timeout=5)
    assert response.status_code == 200

def test_retry_mount(server):
    """Test retry-mount endpoint"""
    response = httpx.post("http://127.0.0.1:8001/api/retry-mount", timeout=5)
    assert response.status_code == 200
    data = response.json()
    assert "ok" in data

def test_manual_invoices(server):
    """Test manual invoices endpoint if API is mounted"""
    s = j("http://127.0.0.1:8001/api/status")
    if s.get("api_mounted"):
        response = httpx.get("http://127.0.0.1:8001/api/manual/invoices", timeout=5)
        assert response.status_code == 200
