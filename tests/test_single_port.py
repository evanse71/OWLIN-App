import httpx
import pytest
import subprocess
import time
import os
import sys
import signal

@pytest.fixture(scope="module")
def server():
    proc = subprocess.Popen([sys.executable, "backend/simple_single_port.py"])
    time.sleep(2)  # Give it time to start
    yield proc
    if proc.poll() is None:
        if os.name == "nt":
            proc.terminate()
        else:
            os.kill(proc.pid, signal.SIGTERM)
        proc.wait(timeout=5)

def test_health(server):
    r = httpx.get("http://127.0.0.1:8001/api/health", timeout=5)
    assert r.status_code == 200
    assert r.json().get("ok") is True

def test_status(server):
    r = httpx.get("http://127.0.0.1:8001/api/status", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    # API mounting status should be present
    assert "api_mounted" in data

def test_root(server):
    r = httpx.get("http://127.0.0.1:8001", timeout=5)
    assert r.status_code == 200
    # Should return either HTML or JSON fallback
    content = r.text
    assert len(content) > 0
