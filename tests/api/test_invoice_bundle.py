import requests

def test_invoice_bundle_contract():
    # assume server already running in CI; or start it in suite-level fixture in your env
    r = requests.get("http://localhost:8000/api/invoices/test_inv_001", timeout=5)
    assert r.status_code in (200,404)
    if r.status_code == 200:
        payload = r.json()
        assert "lines" in payload and isinstance(payload["lines"], list)
        if payload["lines"]:
            line = payload["lines"][0]
            assert "unit_price" in line and "line_total" in line
            assert "unit_price_pennies" not in line and "line_total_pennies" not in line 