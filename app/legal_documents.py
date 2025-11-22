"""
Legal Documents API
Provides Terms of Service and Privacy Policy endpoints
Required for DPDP Act 2023 compliance
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime

router = APIRouter()

# Terms of Service content
TERMS_OF_SERVICE = """
# EchoFort Terms of Service

**Last Updated:** November 15, 2025

## 1. Acceptance of Terms

By accessing or using EchoFort's services, you agree to be bound by these Terms of Service and all applicable laws and regulations.

## 2. Description of Service

EchoFort provides AI-powered scam protection, call screening, family safety, and digital security services through our mobile application and web platform.

## 3. User Obligations

- You must be at least 18 years old to use our services
- You must provide accurate and complete information
- You are responsible for maintaining the confidentiality of your account
- You must not use our services for illegal purposes

## 4. Privacy and Data Protection

We comply with the Digital Personal Data Protection Act, 2023 (DPDP Act). Please review our Privacy Policy for details on how we collect, use, and protect your data.

## 5. Call Recording

- Call recording features require explicit consent
- Recordings are encrypted and stored securely
- You are responsible for complying with local call recording laws
- EchoFort is not liable for unauthorized use of recordings

## 6. AI-Powered Features

- Our AI systems provide scam detection and risk assessment
- AI predictions are not 100% accurate and should not be solely relied upon
- Final decisions regarding calls and messages remain your responsibility

## 7. Subscription and Payments

- Subscription fees are charged in advance
- Refunds are subject to our Refund Policy
- We use secure payment gateways (Razorpay, Stripe)
- Prices may change with 30 days notice

## 8. Family Safety Features

- GPS tracking requires consent from all family members
- Parents/guardians are responsible for monitoring children's device usage
- Screen time limits are enforced based on WHO guidelines

## 9. Legal Assistance

- Auto-generated complaints are templates only
- We do not provide legal advice
- You should consult a lawyer for legal matters
- EchoFort is not responsible for outcomes of complaints filed

## 10. Limitation of Liability

EchoFort is not liable for:
- Damages arising from use or inability to use our services
- Unauthorized access to your data
- Actions of third parties
- Losses due to scams not detected by our AI

## 11. Termination

We reserve the right to suspend or terminate your account for:
- Violation of these Terms
- Fraudulent activity
- Abuse of our services
- Non-payment of subscription fees

## 12. Changes to Terms

We may update these Terms at any time. Continued use of our services constitutes acceptance of updated Terms.

## 13. Governing Law

These Terms are governed by the laws of India. Disputes shall be subject to the exclusive jurisdiction of courts in Mumbai, Maharashtra.

## 14. Contact

For questions about these Terms, contact us at:
- Email: legal@echofort.ai
- Phone: +91-XXXXXXXXXX
- Address: Mumbai, Maharashtra, India

---

© 2025 EchoFort. All rights reserved.
"""

# Privacy Policy content
PRIVACY_POLICY = """
# EchoFort Privacy Policy

**Last Updated:** November 15, 2025

## 1. Introduction

EchoFort ("we", "our", "us") is committed to protecting your privacy and complying with the Digital Personal Data Protection Act, 2023 (DPDP Act).

## 2. Data We Collect

### 2.1 Personal Information
- Name, email address, phone number
- Date of birth (for age verification)
- Government ID (for KYC verification)
- Profile photo (optional)

### 2.2 Call Data
- Incoming call numbers
- Call duration and timestamps
- Call recordings (with explicit consent)
- AI-generated transcripts and analysis

### 2.3 Location Data
- GPS coordinates (for family safety features)
- Geofence zones
- Location history (30 days)

### 2.4 Device Information
- Device model and OS version
- App version
- Device permissions
- Crash logs and diagnostics

### 2.5 Usage Data
- Features used
- Screen time
- App interactions
- Error logs

## 3. How We Use Your Data

### 3.1 Core Services
- Scam detection and call screening
- AI-powered risk assessment
- Family safety and GPS tracking
- Legal complaint generation

### 3.2 Service Improvement
- AI model training
- Bug fixes and optimization
- Feature development
- Performance monitoring

### 3.3 Communication
- Service updates
- Security alerts
- Subscription notifications
- Marketing (with consent)

## 4. Data Sharing

### 4.1 We DO NOT sell your data

### 4.2 We share data with:
- **Payment Processors:** Razorpay, Stripe, PayPal (for payments)
- **Cloud Services:** AWS, Google Cloud (for storage)
- **Analytics:** Firebase, Sentry (for app performance)
- **AI Services:** OpenAI (for Whisper transcription)

### 4.3 Legal Requirements
We may disclose data to:
- Law enforcement (with valid legal request)
- Courts (with subpoena)
- Regulatory authorities (for compliance)

## 5. Your Rights (DPDP Act 2023)

### 5.1 Right to Access
- View all data we have about you
- Download your data in portable format

### 5.2 Right to Correction
- Update inaccurate information
- Complete incomplete data

### 5.3 Right to Erasure
- Request deletion of your data
- Account closure and data removal

### 5.4 Right to Consent Withdrawal
- Withdraw consent for data processing
- Opt-out of non-essential features

### 5.5 Right to Nominate
- Nominate someone to manage your data after death

## 6. Data Security

### 6.1 Encryption
- End-to-end encryption for call recordings
- AES-256 encryption for stored data
- TLS 1.3 for data in transit

### 6.2 Access Control
- Multi-factor authentication
- Role-based access control
- IP whitelisting for admin access

### 6.3 Monitoring
- 24/7 security monitoring
- Intrusion detection systems
- Regular security audits

## 7. Data Retention

- **Call Recordings:** 90 days (or until deleted)
- **Location History:** 30 days
- **Account Data:** Until account deletion
- **Legal Compliance:** As required by law

## 8. Children's Privacy

- Our services are not for children under 13
- Parental consent required for users 13-18
- Child protection features require parental setup

## 9. International Transfers

- Data is primarily stored in India
- Cloud backups may be in other regions
- All transfers comply with DPDP Act requirements

## 10. Cookies and Tracking

- We use cookies for authentication
- Analytics cookies (with consent)
- You can disable cookies in browser settings

## 11. Third-Party Services

- We integrate with WhatsApp, Telegram (for message scanning)
- We use Google Maps (for GPS features)
- We use payment gateways (for subscriptions)

## 12. Data Breach Notification

In case of a data breach, we will:
- Notify affected users within 72 hours
- Report to Data Protection Board of India
- Take immediate remedial action

## 13. Consent Management

- Explicit consent for call recording
- Opt-in for marketing communications
- Granular consent for each feature
- Easy consent withdrawal

## 14. Contact Data Protection Officer

For privacy concerns, contact our DPO:
- Email: dpo@echofort.ai
- Phone: +91-XXXXXXXXXX
- Address: Mumbai, Maharashtra, India

## 15. Grievance Redressal

- File complaints at: grievance@echofort.ai
- Response within 30 days
- Escalate to Data Protection Board if unresolved

## 16. Changes to Privacy Policy

- We will notify you of material changes
- Continued use implies acceptance
- You can reject changes by closing your account

---

© 2025 EchoFort. All rights reserved.
"""


@router.get("/legal/terms")
async def get_terms_of_service():
    """
    Get Terms of Service
    Public endpoint - no authentication required
    """
    return JSONResponse(
        content={
            "ok": True,
            "document": "terms_of_service",
            "version": "1.0",
            "last_updated": "2025-11-15",
            "content": TERMS_OF_SERVICE,
            "content_type": "markdown",
        }
    )


@router.get("/legal/privacy")
async def get_privacy_policy():
    """
    Get Privacy Policy
    Public endpoint - no authentication required
    """
    return JSONResponse(
        content={
            "ok": True,
            "document": "privacy_policy",
            "version": "1.0",
            "last_updated": "2025-11-15",
            "content": PRIVACY_POLICY,
            "content_type": "markdown",
        }
    )


@router.get("/legal/refund")
async def get_refund_policy():
    """
    Get Refund Policy
    Public endpoint - no authentication required
    """
    refund_policy = """
# EchoFort Refund Policy

**Last Updated:** November 15, 2025

## 1. 24-Hour Money-Back Guarantee

- Full refund if requested within 24 hours of first subscription
- No questions asked
- Refund processed within 5-7 business days

## 2. Subscription Cancellation

- Cancel anytime from app settings
- No refund for remaining subscription period
- Access continues until end of billing cycle

## 3. Service Issues

- Refund if service is unavailable for 48+ hours
- Partial refund for major feature failures
- Contact support@echofort.ai for claims

## 4. Refund Process

- Request via app or email refund@echofort.ai
- Provide order ID and reason
- Refund to original payment method
- Processing time: 5-7 business days

## 5. Non-Refundable

- Subscription renewals (after 24 hours)
- Promotional discounts
- Third-party service fees

## 6. Contact

For refund requests:
- Email: refund@echofort.ai
- Phone: +91-XXXXXXXXXX

---

© 2025 EchoFort. All rights reserved.
"""
    
    return JSONResponse(
        content={
            "ok": True,
            "document": "refund_policy",
            "version": "1.0",
            "last_updated": "2025-11-15",
            "content": refund_policy,
            "content_type": "markdown",
        }
    )
