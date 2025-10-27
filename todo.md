# EchoFort Backend TODO

## 🔐 Super Admin Authentication Enhancement
- [ ] Implement three-factor authentication for super admin
  - [ ] Username + Password (existing)
  - [ ] Email OTP verification (new)
  - [ ] WhatsApp OTP verification (new)
- [ ] Create/update super admin account with credentials:
  - Username: Echofort_Super_Admin_91
  - Password: EchoFort@9176$
  - Email: vicky.jvsap@gmail.com
  - WhatsApp: +919361440568

## 📋 Comprehensive Admin System Audit
- [ ] Phase 1: Super Admin Login & Dashboard
  - [ ] Test super admin login with three-factor auth
  - [ ] Verify all super admin dashboard sections
  - [ ] Test all features pin-to-pin (every button, form, link)
  - [ ] Check permissions and access control

- [ ] Phase 2: Employee Management
  - [ ] Create test users for ALL roles:
    - [ ] Admin
    - [ ] Marketing
    - [ ] Customer Support
    - [ ] Accounting
    - [ ] HR
  - [ ] Test each employee login
  - [ ] Verify role-based access control

- [ ] Phase 3: Employee Dashboard Testing
  - [ ] Test WhatsApp dashboard section
  - [ ] Test Q section (queue management)
  - [ ] Test ticket Q section for emails
  - [ ] Verify all features work end-to-end

- [ ] Phase 4: Backend Verification
  - [ ] Match all frontend features with backend APIs
  - [ ] Verify database tables and schemas
  - [ ] Check API endpoints for each feature
  - [ ] Test data flow from frontend → backend → database

## 🔄 Auto-Refresh Features (From Previous Issues)
- [ ] Set up scam alerts auto-update (every 12 hours)
- [ ] Set up YouTube videos auto-update (every 30 minutes)
- [ ] Configure cron jobs or scheduled tasks

## 📧 Email Verification
- [ ] Test OTP email delivery end-to-end
- [ ] Verify SendGrid API key and quota
- [ ] Test with multiple email providers (Gmail, Outlook, etc.)

