from fpdf import FPDF
import io

class InvoicePDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 20)
        self.cell(0, 10, 'INVOICE', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_invoice_pdf(invoice_data: dict) -> bytes:
    pdf = InvoicePDF()
    pdf.add_page()
    
    # Invoice details
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Invoice No: {invoice_data['invoice_no']}", 0, 1)
    
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"Date: {invoice_data['issue_date']}", 0, 1)
    pdf.cell(0, 10, f"Due Date: {invoice_data['due_date']}", 0, 1)
    pdf.cell(0, 10, f"Status: {invoice_data['status']}", 0, 1)
    
    pdf.ln(5)
    
    # Client details
    client = invoice_data['client']
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "Bill To:", 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"{client['name']}", 0, 1)
    pdf.multi_cell(0, 10, f"{client['address']}\nReg No: {client['company_reg_no']}")
    
    pdf.ln(10)
    
    # Items Table Header
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(80, 10, 'Item', 1)
    pdf.cell(30, 10, 'Quantity', 1, 0, 'C')
    pdf.cell(40, 10, 'Unit Price', 1, 0, 'R')
    pdf.cell(40, 10, 'Total', 1, 0, 'R')
    pdf.ln()
    
    # Items
    pdf.set_font('Arial', '', 12)
    for item in invoice_data['items']:
        product_name = item['product']['name']
        quantity = str(item['quantity'])
        price = f"{item['product']['price']:.2f}"
        total = f"{item['line_total']:.2f}"
        
        pdf.cell(80, 10, product_name, 1)
        pdf.cell(30, 10, quantity, 1, 0, 'C')
        pdf.cell(40, 10, price, 1, 0, 'R')
        pdf.cell(40, 10, total, 1, 0, 'R')
        pdf.ln()

    pdf.ln(5)
    
    # Totals
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(150, 10, 'Tax', 0, 0, 'R')
    pdf.cell(40, 10, f"{invoice_data['tax']:.2f}", 1, 0, 'R')
    pdf.ln()
    
    pdf.cell(150, 10, 'Grand Total', 0, 0, 'R')
    pdf.cell(40, 10, f"{invoice_data['total']:.2f}", 1, 0, 'R')
    
    # Output to bytes
    return bytes(pdf.output(dest='S'))
