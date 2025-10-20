# app/websockets.py
"""
EchoFort Real-Time WebSocket System
Provides live updates for dashboard monitoring
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import Dict, Set
import json
import asyncio
from datetime import datetime

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# Connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.admin_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, user_id: int = None, is_admin: bool = False):
        """Accept WebSocket connection"""
        await websocket.accept()
        
        if is_admin:
            self.admin_connections.add(websocket)
        elif user_id:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: int = None):
        """Remove WebSocket connection"""
        if websocket in self.admin_connections:
            self.admin_connections.remove(websocket)
        
        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def send_to_user(self, user_id: int, message: dict):
        """Send message to specific user's connections"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass
    
    async def send_to_admins(self, message: dict):
        """Send message to all admin connections"""
        for connection in list(self.admin_connections):
            try:
                await connection.send_json(message)
            except:
                self.admin_connections.discard(connection)
    
    async def broadcast(self, message: dict):
        """Broadcast to all connections"""
        for connections in self.active_connections.values():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except:
                    pass
        await self.send_to_admins(message)

# Global connection manager
manager = ConnectionManager()

# User WebSocket endpoint
@router.websocket("/user/{user_id}")
async def user_websocket(websocket: WebSocket, user_id: int):
    """WebSocket for user real-time updates"""
    await manager.connect(websocket, user_id=user_id)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "message": "Connected to EchoFort real-time service"
        })
        
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "type": "echo",
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id=user_id)

# Super Admin WebSocket endpoint
@router.websocket("/admin")
async def admin_websocket(websocket: WebSocket):
    """WebSocket for Super Admin real-time monitoring"""
    await manager.connect(websocket, is_admin=True)
    
    try:
        await websocket.send_json({
            "type": "admin_connected",
            "timestamp": datetime.now().isoformat(),
            "message": "Super Admin monitoring active"
        })
        
        while True:
            data = await websocket.receive_text()
            
            try:
                command = json.loads(data)
                
                if command.get("action") == "broadcast":
                    await manager.broadcast({
                        "type": "admin_broadcast",
                        "message": command.get("message"),
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    await websocket.send_json({
                        "type": "broadcast_sent",
                        "timestamp": datetime.now().isoformat()
                    })
            
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Helper function to send real-time alerts
async def send_scam_alert(user_id: int, alert_data: dict):
    """Send real-time scam alert to user"""
    message = {
        "type": "scam_alert",
        "user_id": user_id,
        "alert": alert_data,
        "timestamp": datetime.now().isoformat()
    }
    
    await manager.send_to_user(user_id, message)
    
    admin_message = {
        "type": "user_scam_alert",
        "user_id": user_id,
        "alert": alert_data,
        "timestamp": datetime.now().isoformat()
    }
    await manager.send_to_admins(admin_message)

# Helper function to send system status
async def send_system_status(status_data: dict):
    """Send system status to all admin connections"""
    message = {
        "type": "system_status",
        "status": status_data,
        "timestamp": datetime.now().isoformat()
    }
    await manager.send_to_admins(message)

# Test endpoint for WebSocket connectivity
@router.get("/test")
async def websocket_test():
    """HTML page to test WebSocket connection"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>EchoFort WebSocket Test</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
            #messages { border: 1px solid #ccc; height: 400px; overflow-y: scroll; padding: 10px; margin: 20px 0; background: #f9f9f9; }
            .message { padding: 5px; margin: 5px 0; border-bottom: 1px solid #eee; }
            button { padding: 10px 20px; margin: 5px; cursor: pointer; }
            input { padding: 10px; width: 300px; }
        </style>
    </head>
    <body>
        <h1>EchoFort WebSocket Test</h1>
        
        <div>
            <input type="number" id="userId" placeholder="User ID" value="1">
            <button onclick="connectUser()">Connect as User</button>
            <button onclick="connectAdmin()">Connect as Admin</button>
            <button onclick="disconnect()">Disconnect</button>
        </div>
        
        <div id="messages"></div>
        
        <div>
            <input type="text" id="messageInput" placeholder="Type message...">
            <button onclick="sendMessage()">Send</button>
        </div>
        
        <script>
            let ws = null;
            
            function addMessage(msg) {
                const div = document.createElement('div');
                div.className = 'message';
                div.textContent = typeof msg === 'object' ? JSON.stringify(msg, null, 2) : msg;
                document.getElementById('messages').appendChild(div);
                div.scrollIntoView();
            }
            
            function connectUser() {
                const userId = document.getElementById('userId').value;
                const wsUrl = `ws://${window.location.host}/ws/user/${userId}`;
                connect(wsUrl);
            }
            
            function connectAdmin() {
                const wsUrl = `ws://${window.location.host}/ws/admin`;
                connect(wsUrl);
            }
            
            function connect(url) {
                if (ws) ws.close();
                
                ws = new WebSocket(url);
                
                ws.onopen = () => addMessage('✅ Connected to ' + url);
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    addMessage('📨 Received: ' + JSON.stringify(data, null, 2));
                };
                ws.onerror = (error) => addMessage('❌ Error: ' + error);
                ws.onclose = () => { addMessage('🔌 Disconnected'); ws = null; };
            }
            
            function disconnect() {
                if (ws) { ws.close(); ws = null; }
            }
            
            function sendMessage() {
                if (!ws) { addMessage('❌ Not connected'); return; }
                const msg = document.getElementById('messageInput').value;
                ws.send(msg);
                addMessage('📤 Sent: ' + msg);
                document.getElementById('messageInput').value = '';
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
