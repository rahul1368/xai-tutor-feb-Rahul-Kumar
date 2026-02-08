from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Literal
from datetime import date

class InvoiceItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")

class InvoiceCreate(BaseModel):
    client_id: int
    issue_date: date
    due_date: date
    items: List[InvoiceItemCreate] = Field(..., min_items=1, description="Must have at least one item")
    tax_amount: Optional[float] = Field(0.0, ge=0, description="Tax amount must be non-negative")

    @model_validator(mode='after')
    def check_dates(self):
        if self.due_date < self.issue_date:
            raise ValueError('due_date must be greater than or equal to issue_date')
        return self

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
