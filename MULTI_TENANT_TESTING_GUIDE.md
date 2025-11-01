# 🧪 Multi-Tenant Testing Guide

## 🎯 What We're Testing:

### Phase 1 & 2 Complete (60%):
- ✅ Database migration successful
- ✅ Business model created
- ✅ Registration creates new businesses
- ✅ Business-specific settings

### Phase 3 Not Complete Yet (40%):
- ❌ Data isolation (all users can see all data)
- ❌ Business-specific queries

---

## 🧪 Test Scenarios:

### **Test 1: Login with Existing User**
**Expected:** Should work normally
1. Go to: http://127.0.0.1:5000/auth/login
2. Login with: `muhammad.mamoon@tsgcafe.com` / `Sangat@1311`
3. **Result:** Should login successfully
4. **Note:** This user is in "Legacy Business" (ID: 1)

---

### **Test 2: Register New Business**
**Expected:** Creates new business + owner user
1. Go to: http://127.0.0.1:5000/auth/register
2. Fill in form:
   - First Name: Test
   - Last Name: User
   - Full Name: Test User
   - **Business Name: Test Business** (IMPORTANT)
   - Email: test@test.com
   - Phone: +92 300 1234567
   - Address: Test Address
   - Password: Test@1234
   - Confirm Password: Test@1234
3. Click "Register"
4. **Expected Results:**
   - ✅ Success message
   - ✅ New business created in database
   - ✅ User created with business_id = 2
   - ✅ User is marked as owner (is_owner = True)
   - ✅ Business-specific settings created

---

### **Test 3: Check Database**
**After Test 2, check database:**

```sql
-- Check businesses table
SELECT * FROM businesses;
-- Should show:
-- ID 1: Legacy Business (owner: MM001)
-- ID 2: Test Business (owner: test@test.com)

-- Check users table
SELECT id, business_id, email, is_owner, role FROM users;
-- Should show:
-- ID 1: business_id=1, muhammad.mamoon@tsgcafe.com, is_owner=1
-- ID 2: business_id=2, test@test.com, is_owner=1

-- Check system_settings
SELECT business_id, key, value FROM system_settings WHERE key='restaurant_name';
-- Should show:
-- business_id=1, restaurant_name=Sangat Cafe
-- business_id=2, restaurant_name=Test Business
```

---

### **Test 4: Login with New Business User**
1. Logout from current session
2. Login with: `test@test.com` / `Test@1234`
3. **Expected:** Should login successfully
4. **Current Behavior (Phase 3 not done):**
   - ⚠️ Will see ALL data from ALL businesses
   - ⚠️ This is expected - data isolation not implemented yet

---

## ⚠️ Known Issues (Phase 3 Pending):

### **1. Data Not Isolated**
- Users from Business A can see Business B's data
- **Why:** Queries don't filter by business_id yet
- **Fix:** Phase 3 implementation

### **2. Settings Not Business-Specific**
- SystemSetting.get_setting() returns first match
- **Why:** Method doesn't filter by business_id
- **Fix:** Update SystemSetting methods

### **3. Creating Records**
- New records don't get business_id automatically
- **Why:** Create operations not updated
- **Fix:** Add business_id to all create operations

---

## ✅ What Should Work:

1. ✅ Registration creates new business
2. ✅ User assigned to business
3. ✅ Business-specific settings created
4. ✅ is_owner flag set correctly
5. ✅ Employee ID starts at EMP001 per business

---

## ❌ What Won't Work Yet:

1. ❌ Data isolation (see all businesses' data)
2. ❌ Business-specific menu items
3. ❌ Business-specific sales
4. ❌ Business-specific inventory
5. ❌ Business-specific settings retrieval

---

## 🎯 Success Criteria for Phase 1 & 2:

- [x] Migration runs without errors
- [x] Businesses table created
- [x] Existing data migrated to business_id=1
- [x] Registration creates new business
- [x] User gets business_id
- [x] Settings created per business

---

## 📊 Test Results Template:

```
Test 1 - Login Existing User:
[ ] Pass / [ ] Fail
Notes: _______________

Test 2 - Register New Business:
[ ] Pass / [ ] Fail
Business ID Created: ___
User ID Created: ___
Notes: _______________

Test 3 - Database Check:
[ ] Pass / [ ] Fail
Businesses Count: ___
Users Count: ___
Settings per Business: ___

Test 4 - Login New User:
[ ] Pass / [ ] Fail
Notes: _______________
```

---

## 🚀 Next Steps After Testing:

If Tests Pass:
1. ✅ Phase 1 & 2 confirmed working
2. ⏳ Proceed with Phase 3 (Data Isolation)
3. ⏳ Update all queries
4. ⏳ Test isolation

If Tests Fail:
1. ❌ Debug issues
2. ❌ Fix problems
3. ❌ Re-test

---

## 📞 Quick Commands:

**View Businesses:**
```python
from app.models import Business
Business.query.all()
```

**View Users with Business:**
```python
from app.models import User
for u in User.query.all():
    print(f"{u.email} - Business: {u.business_id} - Owner: {u.is_owner}")
```

**View Settings per Business:**
```python
from app.models import SystemSetting
for s in SystemSetting.query.filter_by(key='restaurant_name').all():
    print(f"Business {s.business_id}: {s.value}")
```

---

**Ready to test! Open the browser and follow the test scenarios above.** 🧪
