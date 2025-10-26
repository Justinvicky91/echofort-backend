"""
EchoFort Invoice Generator
Generates elegant invoices with GST number for subscriptions and refunds
"""

from datetime import datetime
from fpdf import FPDF
import os

class InvoiceGenerator:
    COMPANY_INFO = {
        "name": "EchoFort",
        "tagline": "Complete Digital Family Protection Platform",
        "address": "India",
        "gst": "33AMTPV8141Q1ZY",
        "email": "admin@echofort.ai",
        "website": "https://echofort.ai"
    }
    
    def __init__(self):
        self.pdf = FPDF()
        
    def generate_subscription_invoice(self, order_data):
        """Generate invoice for subscription purchase"""
        self.pdf.add_page()
        
        # Header
        self.pdf.set_font('Arial', 'B', 24)
        self.pdf.set_text_color(139, 92, 246)  # Purple
        self.pdf.cell(0, 10, 'INVOICE', 0, 1, 'C')
        
        self.pdf.set_font('Arial', '', 10)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.cell(0, 5, self.COMPANY_INFO['tagline'], 0, 1, 'C')
        self.pdf.ln(10)
        
        # Company Info
        self.pdf.set_font('Arial', 'B', 12)
        self.pdf.cell(0, 6, self.COMPANY_INFO['name'], 0, 1)
        self.pdf.set_font('Arial', '', 10)
        self.pdf.cell(0, 5, f"GST: {self.COMPANY_INFO['gst']}", 0, 1)
        self.pdf.cell(0, 5, f"Email: {self.COMPANY_INFO['email']}", 0, 1)
        self.pdf.cell(0, 5, f"Website: {self.COMPANY_INFO['website']}", 0, 1)
        self.pdf.ln(10)
        
        # Invoice Details
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.cell(95, 6, f"Invoice No: INV-{order_data['invoice_number']}", 0, 0)
        self.pdf.cell(95, 6, f"Date: {datetime.now().strftime('%d %B %Y')}", 0, 1, 'R')
        self.pdf.ln(5)
        
        # Customer Info
        self.pdf.set_font('Arial', 'B', 11)
        self.pdf.cell(0, 6, 'Bill To:', 0, 1)
        self.pdf.set_font('Arial', '', 10)
        self.pdf.cell(0, 5, order_data['customer_name'], 0, 1)
        self.pdf.cell(0, 5, order_data['customer_email'], 0, 1)
        self.pdf.cell(0, 5, order_data['customer_phone'], 0, 1)
        self.pdf.ln(10)
        
        # Table Header
        self.pdf.set_fill_color(139, 92, 246)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.cell(90, 8, 'Description', 1, 0, 'L', True)
        self.pdf.cell(30, 8, 'Duration', 1, 0, 'C', True)
        self.pdf.cell(35, 8, 'Amount', 1, 0, 'R', True)
        self.pdf.cell(35, 8, 'Total', 1, 1, 'R', True)
        
        # Table Content
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.set_font('Arial', '', 10)
        
        plan_name = order_data['plan_name']
        billing_cycle = order_data['billing_cycle']
        base_amount = order_data['base_amount']
        
        self.pdf.cell(90, 8, f"{plan_name} Plan", 1, 0, 'L')
        self.pdf.cell(30, 8, billing_cycle.capitalize(), 1, 0, 'C')
        self.pdf.cell(35, 8, f"₹{base_amount:,.2f}", 1, 0, 'R')
        self.pdf.cell(35, 8, f"₹{base_amount:,.2f}", 1, 1, 'R')
        
        # Calculations
        gst_rate = 0.18
        gst_amount = base_amount * gst_rate
        total_amount = base_amount + gst_amount
        
        self.pdf.ln(5)
        
        # Summary
        self.pdf.cell(155, 6, 'Subtotal:', 0, 0, 'R')
        self.pdf.cell(35, 6, f"₹{base_amount:,.2f}", 0, 1, 'R')
        
        self.pdf.cell(155, 6, f'GST (18%):', 0, 0, 'R')
        self.pdf.cell(35, 6, f"₹{gst_amount:,.2f}", 0, 1, 'R')
        
        self.pdf.set_font('Arial', 'B', 11)
        self.pdf.cell(155, 8, 'Total Amount:', 0, 0, 'R')
        self.pdf.cell(35, 8, f"₹{total_amount:,.2f}", 0, 1, 'R')
        
        self.pdf.ln(10)
        
        # Payment Info
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.cell(0, 6, 'Payment Information:', 0, 1)
        self.pdf.set_font('Arial', '', 9)
        self.pdf.cell(0, 5, f"Payment Method: {order_data['payment_method']}", 0, 1)
        self.pdf.cell(0, 5, f"Transaction ID: {order_data['transaction_id']}", 0, 1)
        self.pdf.cell(0, 5, f"Payment Status: PAID", 0, 1)
        
        self.pdf.ln(15)
        
        # Footer
        self.pdf.set_font('Arial', 'I', 9)
        self.pdf.set_text_color(100, 100, 100)
        self.pdf.cell(0, 5, 'Thank you for choosing EchoFort!', 0, 1, 'C')
        self.pdf.cell(0, 5, 'Protecting your family is our priority.', 0, 1, 'C')
        
        # Save PDF
        filename = f"invoice_{order_data['invoice_number']}.pdf"
        filepath = f"/tmp/{filename}"
        self.pdf.output(filepath)
        
        return filepath
    
    def generate_refund_invoice(self, refund_data):
        """Generate refund invoice"""
        self.pdf.add_page()
        
        # Header
        self.pdf.set_font('Arial', 'B', 24)
        self.pdf.set_text_color(220, 38, 38)  # Red
        self.pdf.cell(0, 10, 'REFUND INVOICE', 0, 1, 'C')
        
        self.pdf.set_font('Arial', '', 10)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.cell(0, 5, self.COMPANY_INFO['tagline'], 0, 1, 'C')
        self.pdf.ln(10)
        
        # Company Info
        self.pdf.set_font('Arial', 'B', 12)
        self.pdf.cell(0, 6, self.COMPANY_INFO['name'], 0, 1)
        self.pdf.set_font('Arial', '', 10)
        self.pdf.cell(0, 5, f"GST: {self.COMPANY_INFO['gst']}", 0, 1)
        self.pdf.cell(0, 5, f"Email: {self.COMPANY_INFO['email']}", 0, 1)
        self.pdf.cell(0, 5, f"Website: {self.COMPANY_INFO['website']}", 0, 1)
        self.pdf.ln(10)
        
        # Refund Details
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.cell(95, 6, f"Refund Invoice No: REF-{refund_data['refund_number']}", 0, 0)
        self.pdf.cell(95, 6, f"Date: {datetime.now().strftime('%d %B %Y')}", 0, 1, 'R')
        self.pdf.cell(95, 6, f"Original Invoice: INV-{refund_data['original_invoice']}", 0, 1)
        self.pdf.ln(5)
        
        # Customer Info
        self.pdf.set_font('Arial', 'B', 11)
        self.pdf.cell(0, 6, 'Refund To:', 0, 1)
        self.pdf.set_font('Arial', '', 10)
        self.pdf.cell(0, 5, refund_data['customer_name'], 0, 1)
        self.pdf.cell(0, 5, refund_data['customer_email'], 0, 1)
        self.pdf.cell(0, 5, refund_data['customer_phone'], 0, 1)
        self.pdf.ln(10)
        
        # Refund Reason
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.cell(0, 6, 'Refund Reason:', 0, 1)
        self.pdf.set_font('Arial', '', 10)
        self.pdf.multi_cell(0, 5, refund_data.get('reason', 'Customer requested refund'))
        self.pdf.ln(5)
        
        # Table Header
        self.pdf.set_fill_color(220, 38, 38)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.cell(120, 8, 'Description', 1, 0, 'L', True)
        self.pdf.cell(70, 8, 'Refund Amount', 1, 1, 'R', True)
        
        # Table Content
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.set_font('Arial', '', 10)
        
        refund_amount = refund_data['refund_amount']
        
        self.pdf.cell(120, 8, f"{refund_data['plan_name']} Plan Refund", 1, 0, 'L')
        self.pdf.cell(70, 8, f"₹{refund_amount:,.2f}", 1, 1, 'R')
        
        self.pdf.ln(5)
        
        # Total
        self.pdf.set_font('Arial', 'B', 11)
        self.pdf.cell(120, 8, 'Total Refund Amount:', 0, 0, 'R')
        self.pdf.cell(70, 8, f"₹{refund_amount:,.2f}", 0, 1, 'R')
        
        self.pdf.ln(10)
        
        # Refund Info
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.cell(0, 6, 'Refund Information:', 0, 1)
        self.pdf.set_font('Arial', '', 9)
        self.pdf.cell(0, 5, f"Refund Method: {refund_data['refund_method']}", 0, 1)
        self.pdf.cell(0, 5, f"Refund Transaction ID: {refund_data['refund_transaction_id']}", 0, 1)
        self.pdf.cell(0, 5, f"Refund Status: PROCESSED", 0, 1)
        self.pdf.cell(0, 5, f"Expected in account: 5-7 business days", 0, 1)
        
        self.pdf.ln(15)
        
        # Footer
        self.pdf.set_font('Arial', 'I', 9)
        self.pdf.set_text_color(100, 100, 100)
        self.pdf.cell(0, 5, 'We are sorry to see you go.', 0, 1, 'C')
        self.pdf.cell(0, 5, 'Feel free to return anytime!', 0, 1, 'C')
        
        # Save PDF
        filename = f"refund_invoice_{refund_data['refund_number']}.pdf"
        filepath = f"/tmp/{filename}"
        self.pdf.output(filepath)
        
        return filepath

# Initialize generator
invoice_generator = InvoiceGenerator()

