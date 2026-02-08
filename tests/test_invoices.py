from fastapi import status
import pytest

def test_create_invoice_success(client):
    response = client.post("/invoices", json={
        "client_id": 1,
        "issue_date": "2023-01-01",
        "due_date": "2023-01-31",
        "items": [{"product_id": 1, "quantity": 5}],
        "tax_amount": 5.0
    })
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["client"]["id"] == 1
    assert data["items"][0]["product"]["id"] == 1
    assert data["items"][0]["quantity"] == 5
    assert data["total"] == 55.0 # (10.0 * 5) + 5.0 tax
    assert data["status"] == "DRAFT"

def test_create_invoice_invalid_client(client):
    response = client.post("/invoices", json={
        "client_id": 999, # Non-existent
        "issue_date": "2023-01-01",
        "due_date": "2023-01-31",
        "items": [{"product_id": 1, "quantity": 1}]
    })
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_create_invoice_negative_quantity(client):
    response = client.post("/invoices", json={
        "client_id": 1,
        "issue_date": "2023-01-01",
        "due_date": "2023-01-31",
        "items": [{"product_id": 1, "quantity": -5}]
    })
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_create_invoice_invalid_dates(client):
    response = client.post("/invoices", json={
        "client_id": 1,
        "issue_date": "2023-01-31",
        "due_date": "2023-01-01", # Before issue date
        "items": [{"product_id": 1, "quantity": 1}]
    })
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_list_invoices_pagination(client):
    # Create multiple invoices
    for _ in range(5):
        client.post("/invoices", json={
            "client_id": 1,
            "issue_date": "2023-01-01",
            "due_date": "2023-01-31",
            "items": [{"product_id": 1, "quantity": 1}]
        })
    
    response = client.get("/invoices?page=1&page_size=2")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 5 # 5 plus any form previous tests if DB persists (it shouldn't per function, but file persists per session)
    # Actually conftest scope is session for db creation, but we don't truncate between tests in this simple setup.
    # So total will increase.

def test_get_invoice_pdf(client):
    # Create invoice
    create_res = client.post("/invoices", json={
        "client_id": 1,
        "issue_date": "2023-01-01",
        "due_date": "2023-01-31",
        "items": [{"product_id": 1, "quantity": 1}]
    })
    invoice_id = create_res.json()["id"]
    
    response = client.get(f"/invoices/{invoice_id}/pdf")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 0

def test_update_status(client):
    # Create invoice
    create_res = client.post("/invoices", json={
        "client_id": 1,
        "issue_date": "2023-01-01",
        "due_date": "2023-01-31",
        "items": [{"product_id": 1, "quantity": 1}]
    })
    invoice_id = create_res.json()["id"]
    
    response = client.patch(f"/invoices/{invoice_id}/status", json={"status": "PAID"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "PAID"
