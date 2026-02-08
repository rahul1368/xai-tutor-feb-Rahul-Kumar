from fastapi import status
from fastapi.testclient import TestClient
import pytest
import time
from app.rate_limiter import limiter

@pytest.fixture(autouse=True)
def enable_rate_limit():
    """Enable rate limiting for these tests and reset buckets."""
    limiter.enabled = True
    limiter.reset()
    yield
    limiter.enabled = False

def test_rate_limit_pdf(client):
    # Tests that /pdf endpoint is limited to 5/minute
    
    # Create invoice first
    create_res = client.post("/invoices", json={
        "client_id": 1,
        "issue_date": "2023-01-01",
        "due_date": "2023-01-31",
        "items": [{"product_id": 1, "quantity": 1}]
    })
    invoice_id = create_res.json()["id"]
    
    # Hit endpoint 5 times (allowed)
    for _ in range(5):
        res = client.get(f"/invoices/{invoice_id}/pdf")
        assert res.status_code == status.HTTP_200_OK
    
    # Hit 6th time (should produce 429)
    res = client.get(f"/invoices/{invoice_id}/pdf")
    assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Rate limit exceeded" in res.text

def test_rate_limit_create_invoice(client):
    # Tests that create endpoint is limited to 10/minute
    
    # Hit endpoint 10 times (allowed)
    for _ in range(10):
        res = client.post("/invoices", json={
            "client_id": 1,
            "issue_date": "2023-01-01",
            "due_date": "2023-01-31",
            "items": [{"product_id": 1, "quantity": 1}]
        })
        assert res.status_code == status.HTTP_201_CREATED
    
    # Hit 11th time (should produce 429)
    res = client.post("/invoices", json={
        "client_id": 1,
        "issue_date": "2023-01-01",
        "due_date": "2023-01-31",
        "items": [{"product_id": 1, "quantity": 1}]
    })
    assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS

