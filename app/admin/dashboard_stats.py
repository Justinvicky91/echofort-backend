from fastapi import APIRouter

router = APIRouter()

@router.get("/admin/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics for Super Admin"""
    
    # Return mock data for now - will be replaced with real database queries later
    return {
        "success": True,
        "stats": {
            "total_revenue": 0,
            "revenue_change": 24,
            "active_users": 1,  # Super Admin
            "users_change": 100,
            "subscriptions": 0,
            "subscriptions_change": 0,
            "threats_blocked": 0,
            "threats_change": 0,
            "total_employees": 1,  # Super Admin
            "total_customers": 0,
            "pending_tickets": 0,
            "new_users_this_week": 1
        },
        "insights": [
            {
                "type": "revenue",
                "title": "Revenue Optimization",
                "message": "Family Pack subscriptions show 34% higher retention. Consider promotional campaign.",
                "priority": "high"
            },
            {
                "type": "threat",
                "title": "Threat Detection",
                "message": "Digital Arrest scams increased 45% this week. Auto-alert system activated.",
                "priority": "critical"
            },
            {
                "type": "info",
                "title": "Welcome to EchoFort",
                "message": "Your Super Admin dashboard is ready! Next steps: Configure payment gateways and create employee accounts.",
                "priority": "normal"
            }
        ]
    }

