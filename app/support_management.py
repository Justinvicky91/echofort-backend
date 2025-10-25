"""
Support Ticket Management API for Employee Dashboard
Provides endpoints for viewing, replying to, and managing customer support tickets
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import text
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/support", tags=["Support Management"])


# Pydantic Models
class ReplyRequest(BaseModel):
    message: str
    status: Optional[str] = None  # open, in_progress, resolved, closed


class StatusUpdate(BaseModel):
    status: str  # open, in_progress, resolved, closed


class AssignTicket(BaseModel):
    ticket_id: int
    employee_id: int


class AddNote(BaseModel):
    note: str


# Helper function to send email via SendGrid
async def send_email_to_customer(to_email: str, subject: str, message: str, from_email: str = "support@echofort.ai"):
    """Send email to customer using SendGrid"""
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    
    try:
        email_message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=f"Re: {subject}",
            html_content=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0;">EchoFort Support</h1>
                </div>
                <div style="padding: 30px; background: #f9fafb;">
                    <p style="color: #374151; line-height: 1.6; white-space: pre-wrap;">{message}</p>
                    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                    <p style="color: #6b7280; font-size: 14px;">
                        Best regards,<br>
                        EchoFort Support Team<br>
                        <a href="https://echofort.ai" style="color: #667eea;">echofort.ai</a>
                    </p>
                </div>
                <div style="background: #1f2937; padding: 20px; text-align: center;">
                    <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                        © 2025 EchoFort. All rights reserved.
                    </p>
                </div>
            </div>
            """
        )
        
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sg.send(email_message)
        
        logger.info(f"Email sent to {to_email}. Status: {response.status_code}")
        return response.status_code in [200, 202]
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


# 1. GET /admin/support/stats - Dashboard Statistics
@router.get("/stats")
async def get_support_stats(request: Request):
    """Get support dashboard statistics"""
    try:
        db = request.app.state.db
        
        # Get open tickets count
        open_tickets_query = text("SELECT COUNT(*) FROM support_tickets WHERE status IN ('open', 'in_progress')")
        open_tickets = (await db.execute(open_tickets_query)).scalar() or 0
        
        # Get resolved today count
        resolved_today_query = text("""
            SELECT COUNT(*) FROM support_tickets 
            WHERE status = 'resolved' 
            AND DATE(updated_at) = CURRENT_DATE
        """)
        resolved_today = (await db.execute(resolved_today_query)).scalar() or 0
        
        # Calculate average response time (in minutes)
        # This is a simplified calculation - you can make it more sophisticated
        avg_response_query = text("""
            SELECT AVG(EXTRACT(EPOCH FROM (updated_at - created_at)) / 60) 
            FROM support_tickets 
            WHERE status != 'open' 
            AND updated_at > created_at
        """)
        avg_response_time = (await db.execute(avg_response_query)).scalar() or 0
        
        # Get total tickets for satisfaction calculation
        total_resolved_query = text("SELECT COUNT(*) FROM support_tickets WHERE status = 'resolved'")
        total_resolved = (await db.execute(total_resolved_query)).scalar() or 1
        
        # Simplified satisfaction score (you can implement actual customer feedback later)
        satisfaction_score = min(95, 80 + (resolved_today * 2))
        
        return {
            "ok": True,
            "open_tickets": int(open_tickets),
            "avg_response_time": int(avg_response_time),
            "resolved_today": int(resolved_today),
            "satisfaction_score": int(satisfaction_score)
        }
    except Exception as e:
        logger.error(f"Failed to get support stats: {e}")
        return {
            "ok": False,
            "open_tickets": 0,
            "avg_response_time": 0,
            "resolved_today": 0,
            "satisfaction_score": 0
        }


# 2. GET /admin/support/tickets - List All Tickets
@router.get("/tickets")
async def get_tickets(request: Request, status: str = "all", priority: str = "all", limit: int = 50):
    """Get list of support tickets with optional filters"""
    try:
        db = request.app.state.db
        
        # Build query with filters
        query = "SELECT * FROM support_tickets WHERE 1=1"
        params = {}
        
        if status != "all":
            query += " AND status = :status"
            params["status"] = status
        
        if priority != "all":
            query += " AND priority = :priority"
            params["priority"] = priority
        
        query += " ORDER BY created_at DESC LIMIT :limit"
        params["limit"] = limit
        
        result = await db.execute(text(query), params)
        tickets = result.fetchall()
        
        # Convert to dict
        tickets_list = []
        for ticket in tickets:
            tickets_list.append({
                "id": ticket[0],
                "customer_email": ticket[1],
                "customer_name": ticket[2],
                "subject": ticket[3],
                "message": ticket[4],
                "status": ticket[5],
                "priority": ticket[6],
                "category": ticket[7],
                "created_at": str(ticket[8]),
                "updated_at": str(ticket[9]),
                "assigned_to": ticket[10],
                "from_email": ticket[11] if len(ticket) > 11 else ticket[1],
                "from_name": ticket[12] if len(ticket) > 12 else ticket[2],
                "auto_response_sent": ticket[17] if len(ticket) > 17 else False
            })
        
        return {
            "ok": True,
            "tickets": tickets_list,
            "total": len(tickets_list)
        }
    except Exception as e:
        logger.error(f"Failed to get tickets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch tickets: {str(e)}")


# 3. GET /admin/support/ticket/{ticket_id}/conversation - Get Conversation History
@router.get("/ticket/{ticket_id}/conversation")
async def get_ticket_conversation(ticket_id: int, request: Request):
    """Get conversation history for a ticket"""
    try:
        db = request.app.state.db
        
        # Get original ticket message
        ticket_query = text("SELECT customer_email, customer_name, subject, message, created_at FROM support_tickets WHERE id = :ticket_id")
        ticket = (await db.execute(ticket_query, {"ticket_id": ticket_id})).fetchone()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        messages = []
        
        # Add original customer message
        messages.append({
            "id": f"ticket_{ticket_id}",
            "from": "customer",
            "from_name": ticket[1] or "Customer",
            "message": ticket[3],
            "created_at": str(ticket[4]),
            "is_employee": False
        })
        
        # Get all responses from ticket_responses table
        responses_query = text("""
            SELECT id, from_type, from_name, message, created_at 
            FROM ticket_responses 
            WHERE ticket_id = :ticket_id 
            ORDER BY created_at ASC
        """)
        responses = (await db.execute(responses_query, {"ticket_id": ticket_id})).fetchall()
        
        for response in responses:
            messages.append({
                "id": response[0],
                "from": response[1],  # 'customer', 'support', 'system'
                "from_name": response[2],
                "message": response[3],
                "created_at": str(response[4]),
                "is_employee": response[1] in ['support', 'system']
            })
        
        return {
            "ok": True,
            "messages": messages,
            "total": len(messages)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation for ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch conversation: {str(e)}")


# 4. POST /admin/support/ticket/{ticket_id}/reply - Send Reply to Customer
@router.post("/ticket/{ticket_id}/reply")
async def reply_to_ticket(ticket_id: int, reply: ReplyRequest, request: Request):
    """Send reply to customer and save to database"""
    try:
        db = request.app.state.db
        
        # Get ticket details
        ticket_query = text("SELECT customer_email, customer_name, subject FROM support_tickets WHERE id = :ticket_id")
        ticket = (await db.execute(ticket_query, {"ticket_id": ticket_id})).fetchone()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        customer_email = ticket[0]
        customer_name = ticket[1]
        subject = ticket[2]
        
        # Save reply to database
        insert_reply_query = text("""
            INSERT INTO ticket_responses (ticket_id, from_type, from_name, message, created_at)
            VALUES (:ticket_id, 'support', 'Support Team', :message, NOW())
            RETURNING id
        """)
        reply_id = (await db.execute(
            insert_reply_query,
            {"ticket_id": ticket_id, "message": reply.message}
        )).scalar()
        
        logger.info(f"Reply saved to database with ID {reply_id}")
        
        # Update ticket status if provided
        if reply.status:
            update_status_query = text("""
                UPDATE support_tickets 
                SET status = :status, updated_at = NOW() 
                WHERE id = :ticket_id
            """)
            await db.execute(update_status_query, {"status": reply.status, "ticket_id": ticket_id})
            logger.info(f"Ticket {ticket_id} status updated to {reply.status}")
        else:
            # Default: update to in_progress if currently open
            update_status_query = text("""
                UPDATE support_tickets 
                SET status = CASE WHEN status = 'open' THEN 'in_progress' ELSE status END,
                    updated_at = NOW() 
                WHERE id = :ticket_id
            """)
            await db.execute(update_status_query, {"ticket_id": ticket_id})
        
        # Send email to customer
        email_sent = await send_email_to_customer(
            to_email=customer_email,
            subject=subject,
            message=reply.message
        )
        
        if email_sent:
            logger.info(f"Reply email sent to {customer_email}")
        else:
            logger.warning(f"Failed to send reply email to {customer_email}, but reply saved to database")
        
        return {
            "ok": True,
            "email_sent": email_sent,
            "reply_id": reply_id,
            "message": "Reply sent successfully" if email_sent else "Reply saved but email failed to send"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send reply to ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send reply: {str(e)}")


# 5. PUT /admin/support/ticket/{ticket_id}/status - Update Ticket Status
@router.put("/ticket/{ticket_id}/status")
async def update_ticket_status(ticket_id: int, status_update: StatusUpdate, request: Request):
    """Update ticket status"""
    try:
        db = request.app.state.db
        
        # Validate status
        valid_statuses = ['open', 'in_progress', 'resolved', 'closed']
        if status_update.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        
        # Update status
        update_query = text("""
            UPDATE support_tickets 
            SET status = :status, updated_at = NOW() 
            WHERE id = :ticket_id
            RETURNING id
        """)
        result = await db.execute(update_query, {"status": status_update.status, "ticket_id": ticket_id})
        
        if not result.scalar():
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        logger.info(f"Ticket {ticket_id} status updated to {status_update.status}")
        
        return {
            "ok": True,
            "message": f"Ticket status updated to {status_update.status}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update ticket {ticket_id} status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")


# 6. POST /admin/support/ticket/assign - Assign Ticket to Employee
@router.post("/ticket/assign")
async def assign_ticket(assignment: AssignTicket, request: Request):
    """Assign ticket to an employee"""
    try:
        db = request.app.state.db
        
        # Check if ticket exists
        ticket_query = text("SELECT id FROM support_tickets WHERE id = :ticket_id")
        ticket = (await db.execute(ticket_query, {"ticket_id": assignment.ticket_id})).fetchone()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Update ticket assignment
        update_query = text("""
            UPDATE support_tickets 
            SET assigned_to = :employee_id, updated_at = NOW() 
            WHERE id = :ticket_id
        """)
        await db.execute(update_query, {"employee_id": assignment.employee_id, "ticket_id": assignment.ticket_id})
        
        # Record assignment in ticket_assignments table (if exists)
        try:
            assignment_query = text("""
                INSERT INTO ticket_assignments (ticket_id, employee_id, assigned_at)
                VALUES (:ticket_id, :employee_id, NOW())
            """)
            await db.execute(assignment_query, {
                "ticket_id": assignment.ticket_id,
                "employee_id": assignment.employee_id
            })
        except:
            # Table might not exist, skip
            pass
        
        logger.info(f"Ticket {assignment.ticket_id} assigned to employee {assignment.employee_id}")
        
        return {
            "ok": True,
            "message": "Ticket assigned successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign ticket {assignment.ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to assign ticket: {str(e)}")


# 7. POST /admin/support/ticket/{ticket_id}/note - Add Internal Note
@router.post("/ticket/{ticket_id}/note")
async def add_ticket_note(ticket_id: int, note_data: AddNote, request: Request):
    """Add internal note to ticket (not visible to customer)"""
    try:
        db = request.app.state.db
        
        # Check if ticket exists
        ticket_query = text("SELECT id FROM support_tickets WHERE id = :ticket_id")
        ticket = (await db.execute(ticket_query, {"ticket_id": ticket_id})).fetchone()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Add note to ticket_responses with from_type='internal'
        insert_note_query = text("""
            INSERT INTO ticket_responses (ticket_id, from_type, from_name, message, created_at)
            VALUES (:ticket_id, 'internal', 'Internal Note', :note, NOW())
            RETURNING id
        """)
        note_id = (await db.execute(
            insert_note_query,
            {"ticket_id": ticket_id, "note": note_data.note}
        )).scalar()
        
        logger.info(f"Internal note added to ticket {ticket_id}")
        
        return {
            "ok": True,
            "note_id": note_id,
            "message": "Note added successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add note to ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add note: {str(e)}")


# BONUS: DELETE /admin/support/ticket/{ticket_id} - Soft Delete Ticket
@router.delete("/ticket/{ticket_id}")
async def delete_ticket(ticket_id: int, request: Request):
    """Soft delete a ticket (mark as deleted, don't actually remove)"""
    try:
        db = request.app.state.db
        
        # Soft delete by updating status to 'deleted'
        delete_query = text("""
            UPDATE support_tickets 
            SET status = 'deleted', updated_at = NOW() 
            WHERE id = :ticket_id
            RETURNING id
        """)
        result = await db.execute(delete_query, {"ticket_id": ticket_id})
        
        if not result.scalar():
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        logger.info(f"Ticket {ticket_id} soft deleted")
        
        return {
            "ok": True,
            "message": "Ticket deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete ticket: {str(e)}")

