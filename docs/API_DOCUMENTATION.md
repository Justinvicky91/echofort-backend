# EchoFort API Documentation

## Base URL
```
Production: https://api.echofort.ai
```

## Authentication

All authenticated endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

### Get JWT Token
1. Request OTP: `POST /auth/otp/request`
2. Verify OTP: `POST /auth/otp/verify`

---

## Authentication Endpoints

### Request OTP
```http
POST /auth/otp/request
Content-Type: application/json

{
  "phone_number": "+919876543210",
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "OTP sent successfully"
}
```

### Verify OTP
```http
POST /auth/otp/verify
Content-Type: application/json

{
  "phone_number": "+919876543210",
  "otp": "123456"
}
```

**Response:**
```json
{
  "success": true,
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": {
    "id": "user_123",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

---

## User Profile Endpoints

### Get User Profile
```http
GET /api/user/profile
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "user_123",
  "name": "John Doe",
  "email": "user@example.com",
  "phone": "+919876543210",
  "avatar_url": "https://...",
  "bio": "User bio",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Update User Profile
```http
PUT /api/user/profile
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Jane Doe",
  "bio": "Updated bio"
}
```

### Upload Avatar
```http
POST /api/user/avatar
Authorization: Bearer <token>
Content-Type: multipart/form-data

avatar: <file>
```

---

## Call Protection Endpoints

### Analyze Call (Whisper AI)
```http
POST /api/calls/analyze
Authorization: Bearer <token>
Content-Type: application/json

{
  "phone_number": "+919876543210",
  "audio_url": "https://...",
  "duration": 120
}
```

**Response:**
```json
{
  "call_id": "call_123",
  "analysis": {
    "intent": "loan_harassment",
    "trust_score": 2.5,
    "emotion": "aggressive",
    "transcript": "...",
    "red_flags": ["threatening language", "fake authority"],
    "recommendation": "block"
  }
}
```

### Get Recent Calls
```http
GET /api/calls/recent?limit=20&offset=0
Authorization: Bearer <token>
```

**Response:**
```json
{
  "calls": [
    {
      "id": "call_123",
      "phone_number": "+919876543210",
      "timestamp": "2024-01-01T12:00:00Z",
      "duration": 120,
      "trust_score": 2.5,
      "intent": "loan_harassment",
      "status": "blocked"
    }
  ],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

---

## Scam Detection Endpoints

### Analyze Image/Screenshot
```http
POST /api/ai/image/analyze
Authorization: Bearer <token>
Content-Type: multipart/form-data

image: <file>
```

**Response:**
```json
{
  "scam_detected": true,
  "confidence": 0.92,
  "scam_type": "fake_payment_request",
  "red_flags": ["suspicious QR code", "urgent language"],
  "recommendation": "Do not proceed"
}
```

### Analyze URL/Link
```http
POST /api/scan/analyze
Authorization: Bearer <token>
Content-Type: application/json

{
  "url": "https://suspicious-site.com",
  "source": "whatsapp"
}
```

**Response:**
```json
{
  "url": "https://suspicious-site.com",
  "risk_level": "high",
  "scam_type": "phishing",
  "confidence": 0.88,
  "details": "Known phishing domain",
  "recommendation": "block"
}
```

---

## Family & GPS Endpoints

### Get Family Members
```http
GET /api/family/members
Authorization: Bearer <token>
```

**Response:**
```json
{
  "members": [
    {
      "id": "member_123",
      "name": "Mom",
      "phone": "+919876543210",
      "role": "parent",
      "location": {
        "lat": 28.6139,
        "lng": 77.2090,
        "timestamp": "2024-01-01T12:00:00Z"
      }
    }
  ]
}
```

### Update Location
```http
POST /api/family/location
Authorization: Bearer <token>
Content-Type: application/json

{
  "lat": 28.6139,
  "lng": 77.2090
}
```

### Get Safe Zones
```http
GET /api/family/safe-zones
Authorization: Bearer <token>
```

**Response:**
```json
{
  "zones": [
    {
      "id": "zone_123",
      "name": "Home",
      "lat": 28.6139,
      "lng": 77.2090,
      "radius": 500,
      "notifications_enabled": true
    }
  ]
}
```

---

## Legal Aid Endpoints

### Create Legal Complaint
```http
POST /api/legal/complaint
Authorization: Bearer <token>
Content-Type: application/json

{
  "scam_type": "loan_harassment",
  "incident_date": "2024-01-01",
  "description": "...",
  "evidence_ids": ["call_123", "msg_456"]
}
```

**Response:**
```json
{
  "case_id": "case_123",
  "complaint_text": "Auto-generated complaint...",
  "authority": "Cyber Crime Cell",
  "email_draft": "...",
  "status": "draft"
}
```

### Get Evidence Vault
```http
GET /api/legal/vault
Authorization: Bearer <token>
```

**Response:**
```json
{
  "evidence": [
    {
      "id": "ev_123",
      "type": "call_recording",
      "timestamp": "2024-01-01T12:00:00Z",
      "file_url": "https://...",
      "associated_case": "case_123"
    }
  ]
}
```

---

## Subscription Endpoints

### Get Subscription Status
```http
GET /api/subscriptions/status
Authorization: Bearer <token>
```

**Response:**
```json
{
  "plan": "family",
  "status": "active",
  "expires_at": "2025-01-01T00:00:00Z",
  "features": ["whisper_ai", "geofencing", "legal_aid"]
}
```

### Create Payment Order
```http
POST /api/payments/create-order
Authorization: Bearer <token>
Content-Type: application/json

{
  "plan": "family",
  "billing_cycle": "monthly"
}
```

**Response:**
```json
{
  "order_id": "order_123",
  "amount": 79900,
  "currency": "INR",
  "razorpay_key": "rzp_...",
  "razorpay_order_id": "order_..."
}
```

---

## DPDP Compliance Endpoints

### Accept Terms
```http
POST /auth/accept-terms
Authorization: Bearer <token>
Content-Type: application/json

{
  "terms_version": "1.0",
  "privacy_version": "1.0"
}
```

### Export User Data
```http
GET /api/dpdp/export
Authorization: Bearer <token>
```

**Response:** ZIP file with all user data

### Delete User Data
```http
DELETE /api/dpdp/delete
Authorization: Bearer <token>
```

---

## Error Responses

All endpoints return errors in this format:
```json
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "Authentication token is invalid or expired"
  }
}
```

### Common Error Codes
- `INVALID_TOKEN`: JWT token is invalid or expired
- `UNAUTHORIZED`: User not authorized for this action
- `NOT_FOUND`: Resource not found
- `VALIDATION_ERROR`: Request validation failed
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `SERVER_ERROR`: Internal server error

---

## Rate Limiting

- **Free Plan:** 100 requests/hour
- **Personal Plan:** 1000 requests/hour
- **Family Plan:** 5000 requests/hour

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

---

## Webhooks

Subscribe to events:
```http
POST /api/webhooks/subscribe
Authorization: Bearer <token>
Content-Type: application/json

{
  "url": "https://your-server.com/webhook",
  "events": ["call.analyzed", "scam.detected"]
}
```

Webhook payload:
```json
{
  "event": "call.analyzed",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "call_id": "call_123",
    "trust_score": 2.5
  }
}
```

---

## SDKs

- **JavaScript/TypeScript:** `npm install @echofort/sdk`
- **Python:** `pip install echofort-sdk`
- **Flutter/Dart:** `flutter pub add echofort_sdk`

---

## Support

- **Email:** api@echofort.ai
- **Docs:** https://docs.echofort.ai
- **Status:** https://status.echofort.ai
