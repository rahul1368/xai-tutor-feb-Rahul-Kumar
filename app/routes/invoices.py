from fastapi import APIRouter, HTTPException, status, Query, Depends, Request
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import date
import time
import io
import math
import sqlite3
from app.database import get_db
from app.schemas import InvoiceCreate, InvoiceResponse, PaginatedInvoiceResponse, InvoiceStatusUpdate, ClientResponse, ProductResponse, InvoiceItemResponse
from app.services.pdf_generator import generate_invoice_pdf
from app.services.email_service import send_invoice_email
from app.rate_limiter import limiter

router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def create_invoice(request: Request, invoice_data: InvoiceCreate, conn: sqlite3.Connection = Depends(get_db)):
    try:
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
        import uuid
        invoice_no = f"INV-{uuid.uuid4().hex[:8].upper()}"
        address_snapshot = client['address']

        cursor.execute("""
            INSERT INTO invoices (invoice_no, issue_date, due_date, client_id, address, tax, total, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_no,
            invoice_data.issue_date.isoformat(),
            invoice_data.due_date.isoformat(),
            invoice_data.client_id,
            address_snapshot,
            tax,
            final_total,
            'DRAFT' # Default status
        ))
        invoice_id = cursor.lastrowid

        # 5. Create Invoice Items
        for item in invoice_data.items:
            cursor.execute("""
                INSERT INTO invoice_items (invoice_id, product_id, quantity)
                VALUES (?, ?, ?)
            """, (invoice_id, item.product_id, item.quantity))
        
        return _get_invoice_internal(conn, invoice_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("", response_model=PaginatedInvoiceResponse)
@limiter.limit("100/minute")
def list_invoices(
    request: Request,
    client_id: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db)
):
    try:
        cursor = conn.cursor()
        
        # Build Query
        query = "SELECT * FROM invoices"
        count_query = "SELECT COUNT(*) FROM invoices"
        params = []
        conditions = []
        
        if client_id:
            conditions.append("client_id = ?")
            params.append(client_id)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if date_from:
            conditions.append("issue_date >= ?")
            params.append(date_from.isoformat())
        
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
            query += where_clause
            count_query += where_clause
        
        # Count total
        cursor.execute(count_query, params)
        total_items = cursor.fetchone()[0]
        
        # Pagination
        offset = (page - 1) * page_size
        query += " LIMIT ? OFFSET ?"
        params.extend([page_size, offset])
        
        # Execute Main Query
        cursor.execute(query, params)
        invoices = cursor.fetchall()
        
        results = []
        for invoice in invoices:
            results.append(_get_invoice_internal(conn, invoice['id']))
        
        total_pages = math.ceil(total_items / page_size) if page_size > 0 else 0
        
        return PaginatedInvoiceResponse(
            items=results,
            total=total_items,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int, conn: sqlite3.Connection = Depends(get_db)):
    try:
        return _get_invoice_internal(conn, invoice_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(invoice_id: int, conn: sqlite3.Connection = Depends(get_db)):
    try:
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

@router.patch("/{invoice_id}/status", response_model=InvoiceResponse)
def update_invoice_status(invoice_id: int, status_update: InvoiceStatusUpdate, conn: sqlite3.Connection = Depends(get_db)):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM invoices WHERE id = ?", (invoice_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        cursor.execute("UPDATE invoices SET status = ? WHERE id = ?", (status_update.status, invoice_id))
        return _get_invoice_internal(conn, invoice_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{invoice_id}/pdf")
@limiter.limit("5/minute")
def get_invoice_pdf(request: Request, invoice_id: int, conn: sqlite3.Connection = Depends(get_db)):
    try:
        invoice_data = _get_invoice_internal_dict(conn, invoice_id)
        pdf_bytes = generate_invoice_pdf(invoice_data)
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes), 
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=invoice_{invoice_data['invoice_no']}.pdf"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")

@router.post("/{invoice_id}/send")
@limiter.limit("5/minute")
def send_invoice(request: Request, invoice_id: int, conn: sqlite3.Connection = Depends(get_db)):
    try:
        cursor = conn.cursor()
        invoice_data = _get_invoice_internal_dict(conn, invoice_id)
        
        # Generate PDF
        pdf_bytes = generate_invoice_pdf(invoice_data)
        
        # Send Email (Mock)
        to_email = "client@example.com" 
        subject = f"Invoice {invoice_data['invoice_no']} from xAI Tutor"
        body = f"Dear {invoice_data['client']['name']},\n\nPlease find attached your invoice.\n\nTotal: ${invoice_data['total']:.2f}"
        
        send_invoice_email(to_email, subject, body, pdf_bytes)
        
        # Update Status to SENT
        cursor.execute("UPDATE invoices SET status = 'SENT' WHERE id = ?", (invoice_id,))
        
        return {"message": "Invoice sent successfully", "status": "SENT"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending invoice: {str(e)}")


def _get_invoice_internal(conn, invoice_id):
    # This returns Pydantic model
    data = _get_invoice_internal_dict(conn, invoice_id)
    return InvoiceResponse(**data)

def _get_invoice_internal_dict(conn, invoice_id):
    # Helper to get dictionary data for both API response and PDF generation
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
        items_response.append({
            "id": item['id'],
            "product": {
                "id": item['product_id'],
                "name": item['product_name'],
                "price": item['product_price']
            },
            "quantity": item['quantity'],
            "line_total": line_total
        })

    return {
        "id": invoice['id'],
        "invoice_no": invoice['invoice_no'],
        "issue_date": invoice['issue_date'],
        "due_date": invoice['due_date'],
        "client": {
            "id": client['id'],
            "name": client['name'],
            "address": client['address'],
            "company_reg_no": client['company_reg_no']
        },
        "items": items_response,
        "tax": invoice['tax'],
        "total": invoice['total'],
        "address_snapshot": invoice['address'],
        "status": invoice['status'] if invoice['status'] else "DRAFT"
    }
