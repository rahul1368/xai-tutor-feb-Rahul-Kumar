import urllib.request
import urllib.error
import json
import time

BASE_URL = "http://localhost:8000"

def make_request(method, url, data=None):
    req = urllib.request.Request(url, method=method)
    if data:
        json_data = json.dumps(data).encode('utf-8')
        req.add_header('Content-Type', 'application/json')
        req.data = json_data
    
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            response_body = response.read().decode('utf-8')
            try:
                json_response = json.loads(response_body) if response_body else None
            except json.JSONDecodeError:
                json_response = response_body
            return status_code, json_response
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except urllib.error.URLError as e:
        return None, str(e)

def test_invoice_flow():
    print("Waiting for API to be ready...")
    for i in range(10):
        try:
            status, _ = make_request("GET", f"{BASE_URL}/health")
            if status == 200:
                break
            time.sleep(1)
        except Exception:
            time.sleep(1)
    else:
        print("API failed to start.")
        return

    print("API is ready. Starting tests...")

    # 1. Create Invoice
    payload = {
        "client_id": 1,
        "issue_date": "2023-10-27",
        "due_date": "2023-11-27",
        "items": [
            {"product_id": 1, "quantity": 2},
            {"product_id": 2, "quantity": 1}
        ],
        "tax_amount": 5.0
    }
    
    print("\n[POST] Creating Invoice...")
    status, invoice = make_request("POST", f"{BASE_URL}/invoices", payload)
    
    if status == 201:
        print(f"Success! Created Invoice ID: {invoice['id']}")
        print(json.dumps(invoice, indent=2))
        invoice_id = invoice['id']
    else:
        print(f"Failed. Status: {status}")
        print(invoice)
        return

    # 2. List Invoices
    print("\n[GET] Listing Invoices...")
    status, invoices = make_request("GET", f"{BASE_URL}/invoices")
    if status == 200:
        print(f"Found {len(invoices)} invoices.")
        found = any(inv['id'] == invoice_id for inv in invoices)
        print(f"Invoice {invoice_id} found in list: {found}")
    else:
        print(f"Failed. Status: {status}")

    # 3. Get Invoice Detail
    print(f"\n[GET] Fetching Invoice {invoice_id}...")
    status, invoice_detail = make_request("GET", f"{BASE_URL}/invoices/{invoice_id}")
    if status == 200:
        print("Success!")
        print(json.dumps(invoice_detail, indent=2))
    else:
        print(f"Failed. Status: {status}")

    # 4. Delete Invoice
    print(f"\n[DELETE] Deleting Invoice {invoice_id}...")
    status, _ = make_request("DELETE", f"{BASE_URL}/invoices/{invoice_id}")
    if status == 204:
        print("Success! (No Content)")
    else:
        print(f"Failed. Status: {status}")

    # 5. Verify Deletion
    print(f"\n[GET] Verifying Invoice {invoice_id} is gone...")
    status, _ = make_request("GET", f"{BASE_URL}/invoices/{invoice_id}")
    if status == 404:
        print("Success! Invoice not found.")
    else:
        print(f"Failed. Status: {status}")

if __name__ == "__main__":
    test_invoice_flow()
