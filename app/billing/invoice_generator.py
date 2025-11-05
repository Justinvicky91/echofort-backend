"""
Invoice Generator Module
Generates PDF invoices and sends via SendGrid email
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy import text
from datetime import datetime, date
from decimal import Decimal
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64
from typing import Optional

router = APIRouter(prefix="/billing", tags=["Billing"])

# Business details
BUSINESS_NAME = "EchoFort AI Private Limited"
BUSINESS_GSTIN = "29AABCE1234F1Z5"  # Replace with actual GSTIN
BUSINESS_ADDRESS = """
EchoFort AI Private Limited
123 Tech Park, Whitefield
Bangalore, Karnataka 560066
India
"""
BUSINESS_EMAIL = "billing@echofort.ai"
BUSINESS_PHONE = "+91 80 1234 5678"

# Invoice storage directory
INVOICE_DIR = Path("/tmp/invoices")
INVOICE_DIR.mkdir(exist_ok=True, parents=True)


def generate_invoice_id() -> str:
    """Generate unique invoice ID"""
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S")
    return f"INV-{now.year}-{timestamp}"


def generate_invoice_pdf(
    invoice_id: str,
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    plan_name: str,
    amount: Decimal,
    transaction_id: str,
    invoice_date: date,
    customer_address: Optional[str] = None
) -> str:
    """
    Generate PDF invoice
    Returns: file path of generated PDF
    """
    
    # Create PDF file path
    filename = f"{invoice_id}.pdf"
    filepath = INVOICE_DIR / filename
    
    # Create PDF document
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )
    
    # Container for PDF elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=12,
    )
    
    # Title
    title = Paragraph("TAX INVOICE", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.2*inch))
    
    # Invoice header info
    header_data = [
        ['Invoice ID:', invoice_id],
        ['Invoice Date:', invoice_date.strftime('%d %B %Y')],
        ['Transaction ID:', transaction_id],
    ]
    
    header_table = Table(header_data, colWidths=[2*inch, 3*inch])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#424242')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # From and To sections
    from_to_data = [
        [
            Paragraph('<b>From:</b>', styles['Normal']),
            Paragraph('<b>To:</b>', styles['Normal'])
        ],
        [
            Paragraph(f'<b>{BUSINESS_NAME}</b><br/>{BUSINESS_ADDRESS.replace(chr(10), "<br/>")}', styles['Normal']),
            Paragraph(f'<b>{customer_name}</b><br/>{customer_email}<br/>{customer_phone}' + 
                     (f'<br/>{customer_address}' if customer_address else ''), styles['Normal'])
        ],
        [
            Paragraph(f'<b>GSTIN:</b> {BUSINESS_GSTIN}<br/><b>Email:</b> {BUSINESS_EMAIL}<br/><b>Phone:</b> {BUSINESS_PHONE}', 
                     styles['Normal']),
            Paragraph('', styles['Normal'])
        ]
    ]
    
    from_to_table = Table(from_to_data, colWidths=[3*inch, 3*inch])
    from_to_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(from_to_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Invoice items table
    items_heading = Paragraph('Invoice Details', heading_style)
    elements.append(items_heading)
    
    # Calculate tax (18% GST)
    tax_rate = 0.18
    base_amount = amount / Decimal(1 + tax_rate)
    tax_amount = amount - base_amount
    
    items_data = [
        ['#', 'Description', 'Quantity', 'Rate', 'Amount'],
        ['1', f'{plan_name} Subscription', '1', f'₹{base_amount:.2f}', f'₹{base_amount:.2f}'],
        ['', '', '', 'Subtotal:', f'₹{base_amount:.2f}'],
        ['', '', '', 'GST (18%):', f'₹{tax_amount:.2f}'],
        ['', '', '', '<b>Total:</b>', f'<b>₹{amount:.2f}</b>'],
    ]
    
    items_table = Table(items_data, colWidths=[0.5*inch, 2.5*inch, 1*inch, 1.5*inch, 1.5*inch])
    items_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        
        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        
        # Subtotal and tax rows
        ('FONTNAME', (3, -3), (-1, -2), 'Helvetica'),
        ('FONTNAME', (3, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (3, -3), (-1, -1), 10),
        
        # Grid
        ('GRID', (0, 0), (-1, 1), 1, colors.black),
        ('LINEABOVE', (3, -3), (-1, -3), 1, colors.grey),
        ('LINEABOVE', (3, -1), (-1, -1), 2, colors.black),
        
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(items_table)
    elements.append(Spacer(1, 0.4*inch))
    
    # Payment info
    payment_info = Paragraph(
        f'<b>Payment Status:</b> PAID<br/>'
        f'<b>Payment Method:</b> Razorpay<br/>'
        f'<b>Transaction ID:</b> {transaction_id}',
        styles['Normal']
    )
    elements.append(payment_info)
    elements.append(Spacer(1, 0.3*inch))
    
    # Terms and conditions
    terms = Paragraph(
        '<b>Terms & Conditions:</b><br/>'
        '1. This is a computer-generated invoice and does not require a signature.<br/>'
        '2. Refunds are allowed only within 24 hours of purchase.<br/>'
        '3. For support, contact support@echofort.ai',
        styles['Normal']
    )
    elements.append(terms)
    elements.append(Spacer(1, 0.3*inch))
    
    # Footer
    footer = Paragraph(
        '<i>Thank you for your business!</i><br/>'
        f'<font size=8>Generated on {datetime.now().strftime("%d %B %Y at %I:%M %p")}</font>',
        ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9)
    )
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    
    return str(filepath)


async def send_invoice_email(
    customer_email: str,
    customer_name: str,
    invoice_id: str,
    plan_name: str,
    amount: Decimal,
    pdf_path: str
) -> bool:
    """
    Send invoice via SendGrid email with PDF attachment
    Returns: True if sent successfully
    """
    
    sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
    if not sendgrid_api_key:
        raise Exception("SENDGRID_API_KEY not configured")
    
    # Read PDF file
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    # Encode PDF to base64
    encoded_pdf = base64.b64encode(pdf_data).decode()
    
    # Create email
    message = Mail(
        from_email='billing@echofort.ai',
        to_emails=customer_email,
        subject=f'Your EchoFort Subscription Invoice — {plan_name}',
        html_content=f'''
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #1a237e;">Thank you for your subscription!</h2>
                
                <p>Dear {customer_name},</p>
                
                <p>Thank you for subscribing to <strong>{plan_name}</strong>. Your payment has been successfully processed.</p>
                
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #1a237e;">Payment Details</h3>
                    <p style="margin: 5px 0;"><strong>Invoice ID:</strong> {invoice_id}</p>
                    <p style="margin: 5px 0;"><strong>Plan:</strong> {plan_name}</p>
                    <p style="margin: 5px 0;"><strong>Amount Paid:</strong> ₹{amount:.2f}</p>
                    <p style="margin: 5px 0;"><strong>Date:</strong> {datetime.now().strftime("%d %B %Y")}</p>
                </div>
                
                <p>Your invoice is attached to this email as a PDF file. Please keep it for your records.</p>
                
                <p><strong>Important:</strong> Refunds are allowed only within 24 hours of purchase. After 24 hours, no cancellations or refunds will be processed.</p>
                
                <p>If you have any questions or need assistance, please don't hesitate to contact our support team at <a href="mailto:support@echofort.ai">support@echofort.ai</a>.</p>
                
                <p>Thank you for choosing EchoFort!</p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    <strong>EchoFort AI Private Limited</strong><br>
                    Bangalore, India<br>
                    <a href="https://echofort.ai">echofort.ai</a>
                </p>
            </div>
        </body>
        </html>
        '''
    )
    
    # Attach PDF
    attachment = Attachment(
        FileContent(encoded_pdf),
        FileName(f'{invoice_id}.pdf'),
        FileType('application/pdf'),
        Disposition('attachment')
    )
    message.attachment = attachment
    
    # Send email
    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        
        if response.status_code in [200, 202]:
            return True
        else:
            print(f"[ERROR] SendGrid returned {response.status_code}: {response.body}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to send invoice email: {e}")
        return False


async def create_invoice(
    request: Request,
    user_id: int,
    plan_name: str,
    amount: Decimal,
    transaction_id: str,
    razorpay_payment_id: str,
    razorpay_order_id: str,
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    customer_address: Optional[str] = None,
    subscription_id: Optional[int] = None
) -> dict:
    """
    Create invoice, generate PDF, and send email
    Returns: invoice record
    """
    
    db = request.app.state.db
    
    # Generate invoice ID
    invoice_id = generate_invoice_id()
    invoice_date = date.today()
    
    # Generate PDF
    try:
        pdf_path = generate_invoice_pdf(
            invoice_id=invoice_id,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            plan_name=plan_name,
            amount=amount,
            transaction_id=transaction_id,
            invoice_date=invoice_date,
            customer_address=customer_address
        )
        pdf_generated = True
    except Exception as e:
        print(f"[ERROR] Failed to generate PDF: {e}")
        pdf_path = None
        pdf_generated = False
    
    # Send email
    email_sent = False
    sent_at = None
    if pdf_generated and pdf_path:
        try:
            email_sent = await send_invoice_email(
                customer_email=customer_email,
                customer_name=customer_name,
                invoice_id=invoice_id,
                plan_name=plan_name,
                amount=amount,
                pdf_path=pdf_path
            )
            if email_sent:
                sent_at = datetime.now()
        except Exception as e:
            print(f"[ERROR] Failed to send invoice email: {e}")
    
    # Save to database
    result = await db.execute(text("""
        INSERT INTO invoices (
            invoice_id, user_id, subscription_id, plan_name, amount, currency,
            transaction_id, razorpay_payment_id, razorpay_order_id,
            file_path, pdf_generated, email_sent, sent_at,
            customer_name, customer_email, customer_phone, customer_address,
            invoice_date, status
        ) VALUES (
            :invoice_id, :user_id, :subscription_id, :plan_name, :amount, 'INR',
            :transaction_id, :razorpay_payment_id, :razorpay_order_id,
            :file_path, :pdf_generated, :email_sent, :sent_at,
            :customer_name, :customer_email, :customer_phone, :customer_address,
            :invoice_date, 'paid'
        )
        RETURNING id, invoice_id, created_at
    """), {
        'invoice_id': invoice_id,
        'user_id': user_id,
        'subscription_id': subscription_id,
        'plan_name': plan_name,
        'amount': float(amount),
        'transaction_id': transaction_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_order_id': razorpay_order_id,
        'file_path': pdf_path,
        'pdf_generated': pdf_generated,
        'email_sent': email_sent,
        'sent_at': sent_at,
        'customer_name': customer_name,
        'customer_email': customer_email,
        'customer_phone': customer_phone,
        'customer_address': customer_address,
        'invoice_date': invoice_date
    })
    
    invoice_record = result.fetchone()
    
    return {
        'id': invoice_record[0],
        'invoice_id': invoice_record[1],
        'pdf_generated': pdf_generated,
        'email_sent': email_sent,
        'created_at': invoice_record[2]
    }


@router.get("/invoices/{invoice_id}")
async def download_invoice(invoice_id: str, request: Request):
    """
    Download invoice PDF (secured endpoint)
    """
    from fastapi.responses import FileResponse
    
    db = request.app.state.db
    
    # Get invoice record
    result = await db.execute(text("""
        SELECT file_path, customer_email, user_id
        FROM invoices
        WHERE invoice_id = :invoice_id
    """), {'invoice_id': invoice_id})
    
    invoice = result.fetchone()
    
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    
    file_path, customer_email, user_id = invoice
    
    # TODO: Add authentication check - user can only download their own invoices
    # For now, allow download if invoice exists
    
    if not file_path or not Path(file_path).exists():
        raise HTTPException(404, "Invoice PDF not found")
    
    return FileResponse(
        path=file_path,
        media_type='application/pdf',
        filename=f'{invoice_id}.pdf'
    )


@router.get("/invoices")
async def list_invoices(request: Request):
    """
    List all invoices for authenticated user
    """
    # TODO: Add authentication to get user_id from JWT token
    # For now, return all invoices (admin view)
    
    db = request.app.state.db
    
    result = await db.execute(text("""
        SELECT 
            invoice_id, plan_name, amount, currency,
            customer_name, customer_email, invoice_date,
            pdf_generated, email_sent, created_at
        FROM invoices
        ORDER BY created_at DESC
        LIMIT 100
    """))
    
    invoices = []
    for row in result.fetchall():
        invoices.append({
            'invoice_id': row[0],
            'plan_name': row[1],
            'amount': float(row[2]),
            'currency': row[3],
            'customer_name': row[4],
            'customer_email': row[5],
            'invoice_date': row[6].isoformat() if row[6] else None,
            'pdf_generated': row[7],
            'email_sent': row[8],
            'created_at': row[9].isoformat() if row[9] else None
        })
    
    return {
        'ok': True,
        'invoices': invoices,
        'count': len(invoices)
    }
