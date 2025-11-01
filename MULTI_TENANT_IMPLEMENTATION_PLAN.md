# 🏗️ Multi-Tenant ERP Implementation Plan

## Overview
Transform single-tenant ERP into multi-tenant system where each registered business has isolated data.

## Architecture Changes

### 1. New Database Models

#### Business Model (New)
```python
class Business(db.Model):
    id = primary_key
    business_name = unique, not null
    owner_email = unique, not null (first registered user)
    owner_id = foreign_key(users.id)
    subscription_plan = 'free', 'basic', 'premium'
    is_active = boolean
    created_at = datetime
```

#### PasswordResetRequest Model (New)
```python
class PasswordResetRequest(db.Model):
    id = primary_key
    user_id = foreign_key(users.id)
    status = 'pending', 'approved', 'rejected', 'completed'
    requested_at = datetime
    admin_notes = text
    new_password_hash = text (set by admin)
```

### 2. Update Existing Models

Add `business_id` to ALL data models:
- User
- MenuItem
- MenuCategory
- InventoryItem
- Sale
- SaleLine
- Expense
- Supplier
- PurchaseOrder
- BillTemplate
- SystemSetting (per-business settings)

### 3. Registration Flow

**New User Registration:**
1. User enters email, password, business name
2. System creates:
   - New Business record
   - New User record (owner)
   - User gets:
     - Role: 'admin'
     - Department: 'Management'
     - Designation: 'Owner'
     - is_protected: True (cannot change own role)
3. Seed initial data for this business:
   - Menu categories
   - System settings
   - Bill template

**Sub-Account Creation (by Owner):**
1. Owner creates employee accounts
2. Assigns role, department, designation
3. Employee gets access based on permissions

### 4. Forgot Password System

**User Side:**
1. User clicks "Forgot Password"
2. Enters registered email
3. System checks if email exists
4. Creates PasswordResetRequest with status='pending'
5. Shows message: "Your request has been submitted. You will receive your new password within 12-24 hours."

**Admin Panel (Super Admin):**
1. View all password reset requests
2. Verify user identity
3. Generate new temporary password
4. Mark request as 'approved'
5. User gets notification in their panel
6. User can login with temporary password
7. System forces password change on first login

### 5. Data Isolation

**Query Filtering:**
- Every query must filter by `business_id`
- Use Flask-Login's `current_user.business_id`
- Create decorator: `@require_business_context`

**Example:**
```python
# Before
MenuItem.query.all()

# After
MenuItem.query.filter_by(business_id=current_user.business_id).all()
```

### 6. Migration Strategy

**For Existing Data:**
1. Create default Business (id=1, name="Legacy Business")
2. Update all existing records: business_id = 1
3. Assign all existing users to business_id = 1

## Implementation Steps

### Phase 1: Database Schema (1 hour)
- [ ] Create Business model
- [ ] Create PasswordResetRequest model
- [ ] Add business_id to all models
- [ ] Create migration script

### Phase 2: Registration System (30 min)
- [ ] Update registration route
- [ ] Create business on registration
- [ ] Seed initial data for new business
- [ ] Set owner permissions

### Phase 3: Data Isolation (1 hour)
- [ ] Create business context decorator
- [ ] Update all queries with business_id filter
- [ ] Update all routes
- [ ] Test data isolation

### Phase 4: Forgot Password (30 min)
- [ ] Create forgot password page
- [ ] Create password reset request system
- [ ] Create admin panel for requests
- [ ] Add notification system

### Phase 5: Testing (30 min)
- [ ] Test multi-business registration
- [ ] Test data isolation
- [ ] Test forgot password flow
- [ ] Test sub-account creation

## Total Estimated Time: 3-4 hours

## Risks
- Data migration complexity
- Query performance with business_id filter
- Existing code dependencies
- Testing coverage

## Recommendation
Implement in stages, test thoroughly at each stage before proceeding.
