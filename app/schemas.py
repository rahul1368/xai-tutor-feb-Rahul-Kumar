from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import date

class InvoiceItemCreate(BaseModel):
    product_id: int
    quantity: int

class InvoiceCreate(BaseModel):
    client_id: int
    issue_date: date
    due_date: date
    items: List[InvoiceItemCreate]
    tax_amount: Optional[float] = 0.0

class InvoiceStatusUpdate(BaseModel):
    status: Literal['DRAFT', 'SENT', 'PAID', 'OVERDUE']

class ProductResponse(BaseModel):
    id: int
    name: str
    price: float

class ClientResponse(BaseModel):
    id: int
    name: str
    address: str
    company_reg_no: str

class InvoiceItemResponse(BaseModel):
    id: int
    product: ProductResponse
    quantity: int
    line_total: float

class InvoiceResponse(BaseModel):
    id: int
    invoice_no: str
    issue_date: date
    due_date: date
    client: ClientResponse
    items: List[InvoiceItemResponse]
    tax: float
    total: float
    address_snapshot: str
    status: str

    class Config:
        from_attributes = True

class PaginatedInvoiceResponse(BaseModel):
    items: List[InvoiceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
