# 🚀 Multi-Tenant Implementation - Step by Step

## Current Status: STARTING IMPLEMENTATION

---

## Phase 1: Database Schema (30 minutes)

### Step 1.1: Add Business Model ✅
- Create `Business` table
- Fields: id, business_name, owner_email, owner_id, subscription_plan, is_active, created_at

### Step 1.2: Add business_id to User Model
- Add `business_id` column (foreign key to businesses.id)
- Add `is_owner` flag
- Remove unique constraints (email, username, employee_id become unique per business)

### Step 1.3: Add business_id to ALL Data Models
Models to update:
- [x] User
- [ ] MenuCategory
- [ ] MenuItem  
- [ ] InventoryItem
- [ ] Supplier
- [ ] PurchaseOrder
- [ ] Sale
- [ ] Expense
- [ ] DailyClosing
- [ ] BillTemplate
- [ ] SystemSetting
- [ ] CreditSale

### Step 1.4: Create Migration Script
- Script to add business_id columns
- Create default business for existing data
- Update all existing records with business_id = 1

---

## Phase 2: Registration System (20 minutes)

### Step 2.1: Update Registration Route
- Create Business on first user registration
- Set user as owner (is_owner = True)
- Assign role = 'admin'
- Set designation = 'Owner'
- Department = 'Management'

### Step 2.2: Seed Initial Data for New Business
- Create default menu categories
- Create default system settings
- Create default bill template

---

## Phase 3: Data Isolation (45 minutes)

### Step 3.1: Create Business Context Helper
```python
def get_current_business_id():
    return current_user.business_id if current_user.is_authenticated else None
```

### Step 3.2: Update ALL Queries
Routes to update:
- [ ] POS routes
- [ ] Menu routes
- [ ] Inventory routes
- [ ] Finance routes
- [ ] Reports routes
- [ ] Admin routes

Pattern:
```python
# Before
MenuItem.query.all()

# After  
MenuItem.query.filter_by(business_id=current_user.business_id).all()
```

### Step 3.3: Update Create Operations
Add business_id when creating records:
```python
new_item = MenuItem(
    business_id=current_user.business_id,
    # ... other fields
)
```

---

## Phase 4: Sub-Account Management (15 minutes)

### Step 4.1: Update User Creation
- Owner can create sub-accounts
- All sub-accounts get same business_id
- Sub-accounts cannot change their business_id

### Step 4.2: Prevent Cross-Business Access
- Users can only see/edit users in their business
- System administrator can see all businesses

---

## Phase 5: Testing (30 minutes)

### Test Cases:
1. Register new business → Creates business + owner
2. Owner creates employee → Same business_id
3. Business A cannot see Business B's data
4. System administrator can see all businesses
5. Menu items are isolated per business
6. Sales are isolated per business
7. Settings are per-business

---

## Phase 6: Migration Strategy

### For Existing Data:
1. Create "Legacy Business" (id=1)
2. Assign all existing users to business_id=1
3. Assign all existing data to business_id=1
4. System works as before for existing users
5. New registrations create new businesses

---

## Estimated Total Time: 2.5 hours

## Risk Mitigation:
- Backup database before migration
- Test on local first
- Deploy in stages
- Keep rollback plan ready

---

## Next Steps:
1. ✅ Create this plan
2. ⏳ Add Business model
3. ⏳ Update User model
4. ⏳ Create migration script
5. ⏳ Test locally
6. ⏳ Deploy to production
