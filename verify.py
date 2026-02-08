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
            headers = response.info()
            response_body = response.read()
            
            # Helper to parse JSON if content-type says so
            if "application/json" in headers.get("Content-Type", ""):
                try:
                    return status_code, json.loads(response_body.decode('utf-8')), headers
                except:
                    return status_code, response_body, headers
            
            return status_code, response_body, headers

    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8'), None
    except urllib.error.URLError as e:
        return None, str(e), None

def test_phase2_flow():
    print("Waiting for API to be ready...")
    for i in range(10):
        try:
            status, _, _ = make_request("GET", f"{BASE_URL}/health")
            if status == 200:
                break
            time.sleep(1)
        except Exception:
            time.sleep(1)
    else:
        print("API failed to start.")
        return

    print("API is ready. Starting Phase 2 tests...")

    # 1. Create Invoice
    payload = {
        "client_id": 1,
        "issue_date": "2023-10-27",
        "due_date": "2023-11-27",
        "items": [
            {"product_id": 1, "quantity": 5},
        ],
        "tax_amount": 10.0
    }
    
    print("\n[POST] Creating Invoice...")
    status, invoice, _ = make_request("POST", f"{BASE_URL}/invoices", payload)
    
    if status == 201:
        print(f"Success! Created Invoice ID: {invoice['id']}")
        print(f"Initial Status: {invoice['status']}")
        invoice_id = invoice['id']
        if invoice['status'] != 'DRAFT':
            print("ERROR: Status should be DRAFT")
    else:
        print(f"Failed. Status: {status}")
        print(invoice)
        return

    # 2. Update Status
    print(f"\n[PATCH] Updating Status to PAID...")
    status, invoice, _ = make_request("PATCH", f"{BASE_URL}/invoices/{invoice_id}/status", {"status": "PAID"})
    if status == 200:
        print(f"Success! New Status: {invoice['status']}")
        if invoice['status'] != 'PAID':
            print("ERROR: Status did not update")
    else:
        print(f"Failed. Status: {status}")
        print(invoice)

    # 3. Get PDF
    print(f"\n[GET] Downloading PDF...")
    status, content, headers = make_request("GET", f"{BASE_URL}/invoices/{invoice_id}/pdf")
    if status == 200:
        content_type = headers.get("Content-Type")
        print(f"Success! Content-Type: {content_type}")
        print(f"PDF Size: {len(content)} bytes")
        if "application/pdf" not in content_type:
             print("ERROR: Content-Type is not application/pdf")
        
        # Save for manual inspection
        with open("test_invoice.pdf", "wb") as f:
            f.write(content)
        print("Saved to test_invoice.pdf")
    else:
        print(f"Failed. Status: {status}")
        print(content)

    # 4. Send Email
    print(f"\n[POST] Sending Email...")
    status, response, _ = make_request("POST", f"{BASE_URL}/invoices/{invoice_id}/send")
    # Note: Our code doesn't return JSON for this endpoint currently, wait, it does: {"message": ...}
    # Wait, my previous code in `invoices.py` returned a dict. 
    # Let's check status.
    if status == 200:
        print("Success!")
        print(response)
        
        # Verify status changed to SENT (Wait, we set it to SENT in logic, but before we set it to PAID manually. 
        # Does send logic check current status? No. It just updates to SENT.
        # Let's check if it updated.)
        status, invoice_check, _ = make_request("GET", f"{BASE_URL}/invoices/{invoice_id}")
        print(f"Status after send: {invoice_check['status']}")
    else:
        print(f"Failed. Status: {status}")
        print(response)

if __name__ == "__main__":
    test_phase2_flow()
