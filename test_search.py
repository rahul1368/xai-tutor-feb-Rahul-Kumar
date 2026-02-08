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

def test_search_flow():
    print("Waiting for API to be ready...")
    # Assuming API is running locally via uvicorn for this test
    # (Or via docker if port mapped, works either way)
    for i in range(5):
        try:
            status, _ = make_request("GET", f"{BASE_URL}/health")
            if status == 200:
                break
            time.sleep(1)
        except Exception:
            time.sleep(1)
    else:
        print("API failed to start or not reachable.")
        return

    print("API is ready. Starting Search & Pagination tests...")

    # 1. Seed Data: Create 5 invoices
    # 2 for Client 1 (DRAFT)
    # 2 for Client 2 (PAID)
    # 1 for Client 1 (PAID)
    
    print("\n[SEED] Creating test invoices...")
    
    # Client 1, DRAFT
    make_request("POST", f"{BASE_URL}/invoices", {
        "client_id": 1, "issue_date": "2023-10-01", "due_date": "2023-11-01", 
        "items": [{"product_id": 1, "quantity": 1}], "tax_amount": 0
    })
    make_request("POST", f"{BASE_URL}/invoices", {
        "client_id": 1, "issue_date": "2023-10-02", "due_date": "2023-11-02", 
        "items": [{"product_id": 1, "quantity": 1}], "tax_amount": 0
    })

    # Client 2, PAID
    status, inv3 = make_request("POST", f"{BASE_URL}/invoices", {
        "client_id": 2, "issue_date": "2023-10-03", "due_date": "2023-11-03", 
        "items": [{"product_id": 2, "quantity": 1}], "tax_amount": 0
    })
    if status != 201:
        print(f"Failed to create inv3: {status}, {inv3}")
        return
    make_request("PATCH", f"{BASE_URL}/invoices/{inv3['id']}/status", {"status": "PAID"})
    
    status, inv4 = make_request("POST", f"{BASE_URL}/invoices", {
        "client_id": 2, "issue_date": "2023-10-04", "due_date": "2023-11-04", 
        "items": [{"product_id": 2, "quantity": 1}], "tax_amount": 0
    })
    if status != 201:
        print(f"Failed to create inv4: {status}, {inv4}")
        return
    make_request("PATCH", f"{BASE_URL}/invoices/{inv4['id']}/status", {"status": "PAID"})

    # Client 1, PAID
    status, inv5 = make_request("POST", f"{BASE_URL}/invoices", {
        "client_id": 1, "issue_date": "2023-10-05", "due_date": "2023-11-05", 
        "items": [{"product_id": 1, "quantity": 1}], "tax_amount": 0
    })
    if status != 201:
        print(f"Failed to create inv5: {status}, {inv5}")
        return
    make_request("PATCH", f"{BASE_URL}/invoices/{inv5['id']}/status", {"status": "PAID"})

    
    # 2. Test Pagination
    print(f"\n[GET] Pagination (Page 1, Size 2)...")
    status, response = make_request("GET", f"{BASE_URL}/invoices?page=1&page_size=2")
    if status == 200:
        print(f"Total Items: {response['total']}")
        print(f"Page Items: {len(response['items'])}")
        print(f"Current Page: {response['page']}")
        if len(response['items']) == 2:
            print("SUCCESS: Correct page size.")
        else:
            print(f"FAILURE: Expected 2 items, got {len(response['items'])}")
    else:
        print(f"Failed. Status: {status}")

    # 3. Test Filter: Status = PAID
    print(f"\n[GET] Filter Status=PAID...")
    status, response = make_request("GET", f"{BASE_URL}/invoices?status=PAID&page_size=100")
    if status == 200:
        print(f"Found {response['total']} PAID invoices.")
        all_paid = all(inv['status'] == 'PAID' for inv in response['items'])
        if all_paid and response['total'] >= 3:
             print("SUCCESS: All returned items are PAID.")
        else:
             print("FAILURE: Filter incorrect.")
             
    # 4. Test Filter: Client = 1
    print(f"\n[GET] Filter Client=1...")
    status, response = make_request("GET", f"{BASE_URL}/invoices?client_id=1&page_size=100")
    if status == 200:
        print(f"Found {response['total']} invoices for Client 1.")
        # We created 3 for client 1 (2 draft, 1 paid)
        all_client1 = all(inv['client']['id'] == 1 for inv in response['items'])
        if all_client1 and response['total'] >= 3:
             print("SUCCESS: All returned items are for Client 1.")
        else:
             print("FAILURE: Client filter incorrect.")

    # 5. Test Combination: Client=1 AND Status=DRAFT
    print(f"\n[GET] Filter Client=1 AND Status=DRAFT...")
    status, response = make_request("GET", f"{BASE_URL}/invoices?client_id=1&status=DRAFT&page_size=100")
    if status == 200:
        print(f"Found {response['total']} DRAFT invoices for Client 1.")
        # Expect at least 2
        correct = all(inv['client']['id'] == 1 and inv['status'] == 'DRAFT' for inv in response['items'])
        if correct and response['total'] >= 2:
             print("SUCCESS: Combined filter working.")
        else:
             print("FAILURE: Combined filter incorrect.")

if __name__ == "__main__":
    test_search_flow()
