from fastapi import APIRouter, HTTPException, status
from typing import List
import time
from app.database import get_db
from app.schemas import InvoiceCreate, InvoiceResponse, ClientResponse, ProductResponse, InvoiceItemResponse

router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(invoice_data: InvoiceCreate):
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 1. Validate Client
            cursor.execute("SELECT * FROM clients WHERE id = ?", (invoice_data.client_id,))
            client = cursor.fetchone()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            
            # 2. Validate Products and Calculate Total
            total_amount = 0.0
            invoice_items_data = []

            for item in invoice_data.items:
                cursor.execute("SELECT * FROM products WHERE id = ?", (item.product_id,))
                product = cursor.fetchone()
                if not product:
                    raise HTTPException(status_code=404, detail=f"Product with ID {item.product_id} not found")
                
                line_total = product['price'] * item.quantity
                total_amount += line_total
                invoice_items_data.append({
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "price": product['price'],
                    "line_total": line_total
                })

            # 3. Calculate Final Total
            tax = invoice_data.tax_amount if invoice_data.tax_amount is not None else 0.0
            final_total = total_amount + tax

            # 4. Create Invoice Record
            invoice_no = f"INV-{int(time.time())}"
            address_snapshot = client['address']

            cursor.execute("""
                INSERT INTO invoices (invoice_no, issue_date, due_date, client_id, address, tax, total)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_no,
                invoice_data.issue_date.isoformat(),
                invoice_data.due_date.isoformat(),
                invoice_data.client_id,
                address_snapshot,
                tax,
                final_total
            ))
            invoice_id = cursor.lastrowid

            # 5. Create Invoice Items
            for item in invoice_data.items:
                cursor.execute("""
                    INSERT INTO invoice_items (invoice_id, product_id, quantity)
                    VALUES (?, ?, ?)
                """, (invoice_id, item.product_id, item.quantity))
            
            # Commit handled by context manager on exit
            
            # 6. Fetch for Response
            # We need to manually construct response or fetch again.
            # Fetching again is safer to ensure DB state matches.
            return _get_invoice_internal(conn, invoice_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("", response_model=List[InvoiceResponse])
def list_invoices():
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM invoices")
            invoices = cursor.fetchall()
            
            results = []
            for invoice in invoices:
                results.append(_get_invoice_internal(conn, invoice['id']))
            return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int):
    try:
        with get_db() as conn:
            return _get_invoice_internal(conn, invoice_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(invoice_id: int):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM invoices WHERE id = ?", (invoice_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Invoice not found")

            cursor.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
            cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def _get_invoice_internal(conn, invoice_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    invoice = cursor.fetchone()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    cursor.execute("SELECT * FROM clients WHERE id = ?", (invoice['client_id'],))
    client = cursor.fetchone()

    cursor.execute("""
        SELECT ii.*, p.name as product_name, p.price as product_price 
        FROM invoice_items ii
        JOIN products p ON ii.product_id = p.id
        WHERE ii.invoice_id = ?
    """, (invoice_id,))
    items = cursor.fetchall()

    items_response = []
    for item in items:
        line_total = item['quantity'] * item['product_price']
        items_response.append(InvoiceItemResponse(
            id=item['id'],
            product=ProductResponse(id=item['product_id'], name=item['product_name'], price=item['product_price']),
            quantity=item['quantity'],
            line_total=line_total
        ))

    return InvoiceResponse(
        id=invoice['id'],
        invoice_no=invoice['invoice_no'],
        issue_date=invoice['issue_date'],
        due_date=invoice['due_date'],
        client=ClientResponse(id=client['id'], name=client['name'], address=client['address'], company_reg_no=client['company_reg_no']),
        items=items_response,
        tax=invoice['tax'],
        total=invoice['total'],
        address_snapshot=invoice['address']
    )
