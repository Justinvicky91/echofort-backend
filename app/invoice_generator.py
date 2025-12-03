"""
Invoice Generation Module
BLOCK INVOICE-EMAIL Phase 2
Handles HTML invoice generation, PDF conversion, and invoice API endpoints
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from sqlalchemy import text
import os


class InvoiceCreate(BaseModel):
    email: str
    plan: str
    amount: float


def generate_invoice_html(
    invoice_number: str,
    order_id: str,
    payment_id: str,
    amount: int,  # in paise
    currency: str,
    is_internal_test: bool,
    created_at: datetime,
    user_email: Optional[str] = None,
    user_name: Optional[str] = None,
) -> str:
    """
    Generate HTML invoice with EchoFort branding
    
    Args:
        invoice_number: Unique invoice number (e.g., INV-202512-00001)
        order_id: Razorpay order ID
        payment_id: Razorpay payment ID
        amount: Amount in paise (100 paise = ₹1)
        currency: Currency code (INR)
        is_internal_test: True for ₹1 internal tests
        created_at: Invoice creation timestamp
        user_email: Customer email (optional)
        user_name: Customer name (optional)
    
    Returns:
        HTML string for invoice
    """
    
    # Convert paise to rupees
    amount_rupees = amount / 100
    
    # Format date
    date_str = created_at.strftime("%B %d, %Y at %I:%M %p")
    
    # Internal test badge
    test_badge = """
    <div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; padding: 12px; margin: 20px 0; text-align: center;">
        <span style="color: #92400e; font-weight: bold; font-size: 14px;">
            🧪 INTERNAL TEST PAYMENT
        </span>
    </div>
    """ if is_internal_test else ""
    
    # Customer info section
    customer_section = ""
    if user_name or user_email:
        customer_section = f"""
        <div style="margin: 20px 0;">
            <h3 style="color: #1f2937; font-size: 14px; font-weight: 600; margin-bottom: 8px;">BILLED TO</h3>
            {f'<p style="margin: 4px 0; color: #4b5563;">{user_name}</p>' if user_name else ''}
            {f'<p style="margin: 4px 0; color: #4b5563;">{user_email}</p>' if user_email else ''}
        </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Invoice {invoice_number} - EchoFort</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: #f9fafb;
                padding: 40px 20px;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                text-align: center;
            }}
            .header h1 {{
                font-size: 32px;
                margin-bottom: 8px;
            }}
            .header p {{
                font-size: 16px;
                opacity: 0.9;
            }}
            .content {{
                padding: 40px;
            }}
            .invoice-meta {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 30px;
                flex-wrap: wrap;
            }}
            .invoice-meta div {{
                margin-bottom: 15px;
            }}
            .label {{
                color: #6b7280;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 4px;
            }}
            .value {{
                color: #1f2937;
                font-size: 16px;
                font-weight: 500;
            }}
            .invoice-number {{
                font-size: 24px;
                font-weight: bold;
                color: #667eea;
            }}
            .divider {{
                height: 1px;
                background: #e5e7eb;
                margin: 30px 0;
            }}
            .amount-section {{
                background: #f9fafb;
                border-radius: 8px;
                padding: 24px;
                margin: 20px 0;
            }}
            .amount-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 12px;
            }}
            .amount-label {{
                color: #6b7280;
                font-size: 14px;
            }}
            .amount-value {{
                color: #1f2937;
                font-size: 14px;
                font-weight: 500;
            }}
            .total-row {{
                border-top: 2px solid #e5e7eb;
                padding-top: 12px;
                margin-top: 12px;
            }}
            .total-label {{
                color: #1f2937;
                font-size: 18px;
                font-weight: 700;
            }}
            .total-value {{
                color: #667eea;
                font-size: 24px;
                font-weight: 700;
            }}
            .footer {{
                background: #f9fafb;
                padding: 30px 40px;
                text-align: center;
                color: #6b7280;
                font-size: 14px;
                border-top: 1px solid #e5e7eb;
            }}
            .footer p {{
                margin: 8px 0;
            }}
            .footer a {{
                color: #667eea;
                text-decoration: none;
            }}
            @media print {{
                body {{
                    background: white;
                    padding: 0;
                }}
                .container {{
                    box-shadow: none;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🛡️ EchoFort</h1>
                <p>India's Most Advanced Scam Protection Platform</p>
            </div>
            
            <div class="content">
                {test_badge}
                
                <div class="invoice-meta">
                    <div>
                        <div class="label">Invoice Number</div>
                        <div class="invoice-number">{invoice_number}</div>
                    </div>
                    <div>
                        <div class="label">Invoice Date</div>
                        <div class="value">{date_str}</div>
                    </div>
                </div>
                
                <div class="divider"></div>
                
                <div style="display: flex; justify-content: space-between; flex-wrap: wrap;">
                    <div style="margin-bottom: 20px;">
                        <h3 style="color: #1f2937; font-size: 14px; font-weight: 600; margin-bottom: 8px;">FROM</h3>
                        <p style="margin: 4px 0; color: #4b5563; font-weight: 600;">EchoFort Technologies</p>
                        <p style="margin: 4px 0; color: #4b5563;">Protecting India from Scams</p>
                        <p style="margin: 4px 0; color: #4b5563;">support@echofort.ai</p>
                    </div>
                    
                    {customer_section}
                </div>
                
                <div class="divider"></div>
                
                <h3 style="color: #1f2937; font-size: 16px; font-weight: 600; margin-bottom: 16px;">Payment Details</h3>
                
                <div style="margin-bottom: 20px;">
                    <div style="display: flex; justify-content: space-between; padding: 8px 0;">
                        <span class="label">Order ID</span>
                        <span class="value" style="font-family: monospace;">{order_id}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 8px 0;">
                        <span class="label">Payment ID</span>
                        <span class="value" style="font-family: monospace;">{payment_id}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 8px 0;">
                        <span class="label">Payment Method</span>
                        <span class="value">Razorpay</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 8px 0;">
                        <span class="label">Currency</span>
                        <span class="value">{currency}</span>
                    </div>
                </div>
                
                <div class="amount-section">
                    <div class="amount-row">
                        <span class="amount-label">{'Internal Test Payment' if is_internal_test else 'Subscription Payment'}</span>
                        <span class="amount-value">₹{amount_rupees:.2f}</span>
                    </div>
                    <div class="amount-row">
                        <span class="amount-label">Tax (Included)</span>
                        <span class="amount-value">₹0.00</span>
                    </div>
                    <div class="amount-row total-row">
                        <span class="total-label">Total Amount</span>
                        <span class="total-value">₹{amount_rupees:.2f}</span>
                    </div>
                </div>
                
                <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 16px; border-radius: 4px; margin: 20px 0;">
                    <p style="color: #1e40af; font-size: 14px; margin: 0;">
                        <strong>✓ Payment Successful</strong><br>
                        Your payment has been processed successfully. Thank you for choosing EchoFort!
                    </p>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>EchoFort Technologies</strong></p>
                <p>Protecting India from Scams with AI-Powered Security</p>
                <p>
                    <a href="https://echofort.ai">echofort.ai</a> | 
                    <a href="mailto:support@echofort.ai">support@echofort.ai</a>
                </p>
                <p style="margin-top: 16px; font-size: 12px; color: #9ca3af;">
                    This is a computer-generated invoice. No signature required.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


async def convert_html_to_pdf(html_content: str, output_path: str) -> bool:
    """
    Convert HTML to PDF using weasyprint
    
    Args:
        html_content: HTML string
        output_path: Path to save PDF file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from weasyprint import HTML
        
        # Generate PDF
        HTML(string=html_content).write_pdf(output_path)
        return True
        
    except Exception as e:
        print(f"❌ PDF generation failed: {str(e)}")
        return False


# Router endpoints removed - use invoice_api.py instead
