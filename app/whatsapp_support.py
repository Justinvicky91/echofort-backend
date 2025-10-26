"""
WhatsApp Support Integration
Handles WhatsApp messages via Twilio and creates support tickets
"""

import os
import httpx
from fastapi import APIRouter, Request, HTTPException
from datetime import datetime
from typing import Optional

router = APIRouter()

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Receive WhatsApp messages from Twilio
    Creates support tickets from WhatsApp messages
    """
    try:
        db = request.app.state.db
        
        # Parse Twilio webhook data (form-encoded)
        form_data = await request.form()
        
        # Extract WhatsApp message data
        from_number = form_data.get("From", "")  # whatsapp:+919876543210
        to_number = form_data.get("To", "")      # whatsapp:+14155238886
        message_body = form_data.get("Body", "")
        message_sid = form_data.get("MessageSid", "")
        profile_name = form_data.get("ProfileName", "")
        
        # Clean phone number (remove "whatsapp:" prefix)
        customer_phone = from_number.replace("whatsapp:", "").strip()
        customer_name = profile_name or customer_phone
        
        if not customer_phone or not message_body:
            return {"error": "Missing required fields"}
        
        # Check if ticket already exists for this phone number
        existing_ticket = db.execute(
            """
            SELECT id, status FROM support_tickets 
            WHERE customer_phone = %s AND status != 'closed'
            ORDER BY created_at DESC LIMIT 1
            """,
            (customer_phone,)
        ).fetchone()
        
        if existing_ticket:
            # Add message to existing ticket
            ticket_id = existing_ticket[0]
            
            db.execute(
                """
                INSERT INTO support_messages 
                (ticket_id, from_type, from_name, message, whatsapp_message_sid, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                """,
                (ticket_id, "customer", customer_name, message_body, message_sid)
            )
            db.commit()
            
            return {
                "ok": True,
                "ticket_id": ticket_id,
                "message": "Message added to existing ticket"
            }
        
        else:
            # Create new ticket
            db.execute(
                """
                INSERT INTO support_tickets 
                (customer_phone, customer_name, subject, message, 
                 source, status, priority, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (
                    customer_phone,
                    customer_name,
                    f"WhatsApp inquiry from {customer_name}",
                    message_body,
                    "whatsapp",
                    "open",
                    "medium"
                )
            )
            
            # Get the new ticket ID
            ticket_id = db.execute("SELECT LAST_INSERT_ID()").fetchone()[0]
            
            # Add initial message
            db.execute(
                """
                INSERT INTO support_messages 
                (ticket_id, from_type, from_name, message, whatsapp_message_sid, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                """,
                (ticket_id, "customer", customer_name, message_body, message_sid)
            )
            
            db.commit()
            
            # Send auto-response via WhatsApp
            await send_whatsapp_message(
                to_number=customer_phone,
                message="Thank you for contacting EchoFort Support! 🛡️\n\nYour ticket has been created and our team will respond shortly.\n\nTicket ID: #" + str(ticket_id)
            )
            
            return {
                "ok": True,
                "ticket_id": ticket_id,
                "auto_response_sent": True,
                "message": "WhatsApp ticket created successfully"
            }
    
    except Exception as e:
        print(f"Error processing WhatsApp webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/support/ticket/{ticket_id}/whatsapp-reply")
async def send_whatsapp_reply(
    ticket_id: int,
    request: Request
):
    """
    Send WhatsApp reply to customer
    """
    try:
        db = request.app.state.db
        data = await request.json()
        message = data.get("message", "")
        employee_name = data.get("employee_name", "Support Agent")
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Get ticket info
        ticket = db.execute(
            """
            SELECT customer_phone, customer_name, source 
            FROM support_tickets 
            WHERE id = %s
            """,
            (ticket_id,)
        ).fetchone()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        customer_phone, customer_name, source = ticket
        
        if source != "whatsapp":
            raise HTTPException(status_code=400, detail="This is not a WhatsApp ticket")
        
        # Send WhatsApp message
        success = await send_whatsapp_message(
            to_number=customer_phone,
            message=message
        )
        
        if success:
            # Save message to database
            db.execute(
                """
                INSERT INTO support_messages 
                (ticket_id, from_type, from_name, message, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                """,
                (ticket_id, "employee", employee_name, message)
            )
            
            # Update ticket status
            db.execute(
                """
                UPDATE support_tickets 
                SET status = 'in_progress', updated_at = NOW()
                WHERE id = %s
                """,
                (ticket_id,)
            )
            
            db.commit()
            
            return {
                "ok": True,
                "whatsapp_sent": True,
                "message": "WhatsApp reply sent successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send WhatsApp message")
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error sending WhatsApp reply: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def send_whatsapp_message(to_number: str, message: str) -> bool:
    """
    Send WhatsApp message via Twilio API
    """
    try:
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            print("Twilio credentials not configured")
            return False
        
        # Ensure phone number has whatsapp: prefix
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"
        
        # Twilio API endpoint
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
        
        # Prepare request data
        data = {
            "From": TWILIO_WHATSAPP_NUMBER,
            "To": to_number,
            "Body": message
        }
        
        # Send request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                data=data,
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
                timeout=10.0
            )
            
            if response.status_code == 201:
                print(f"WhatsApp message sent to {to_number}")
                return True
            else:
                print(f"Failed to send WhatsApp message: {response.text}")
                return False
    
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")
        return False


@router.get("/admin/support/whatsapp-stats")
async def get_whatsapp_stats(request: Request):
    """
    Get WhatsApp support statistics
    """
    try:
        db = request.app.state.db
        
        # Total WhatsApp tickets
        total = db.execute(
            "SELECT COUNT(*) FROM support_tickets WHERE source = 'whatsapp'"
        ).fetchone()[0]
        
        # Open WhatsApp tickets
        open_tickets = db.execute(
            "SELECT COUNT(*) FROM support_tickets WHERE source = 'whatsapp' AND status = 'open'"
        ).fetchone()[0]
        
        # Resolved today
        resolved_today = db.execute(
            """
            SELECT COUNT(*) FROM support_tickets 
            WHERE source = 'whatsapp' 
            AND status = 'resolved' 
            AND DATE(updated_at) = CURDATE()
            """
        ).fetchone()[0]
        
        return {
            "total_whatsapp_tickets": total,
            "open_whatsapp_tickets": open_tickets,
            "resolved_today": resolved_today
        }
    
    except Exception as e:
        print(f"Error getting WhatsApp stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

