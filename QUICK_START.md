# 🎯 QUICK START: What You Need to Do

## ⏱️ 5-Minute Setup

### 1. Create Stripe Account (2 minutes)
```
→ Go to: https://stripe.com
→ Click "Sign Up"
→ Enter email, password
→ Verify email
✅ Done!
```

### 2. Get API Keys (1 minute)
```
→ Login to Stripe Dashboard
→ Make sure you're in TEST MODE (toggle left sidebar)
→ Go to: Developers → API Keys
→ Copy TWO keys:
   1. Publishable key (pk_test_...)
   2. Secret key (sk_test_... - click "Reveal")
```

### 3. Add Keys to .env file (2 minutes)
```bash
# Open .env file (or create from .env.example)
# Add these lines:

STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE
STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_temporary_can_skip_for_now
```

**Example .env:**
```env
STRIPE_PUBLISHABLE_KEY=pk_test_51abc123xyz789...
STRIPE_SECRET_KEY=sk_test_51abc123xyz789...
STRIPE_WEBHOOK_SECRET=whsec_123
```

### 4. Restart Server
```powershell
# Stop current server (Ctrl+C)
python run.py
```

---

## ✅ That's It! You're Ready to Test

### Test the Payment System:

1. **Go to**: http://localhost:5000
2. **Register** a new business
3. **Select**: Cafe plan (or any plan)
4. Complete registration → You're in TRIAL mode (14 days free)
5. **Go to**: Billing section (in dashboard menu)
6. **Click**: "Add Payment Method"
7. **Use test card**:
   ```
   Card: 4242 4242 4242 4242
   Expiry: 12/25
   CVC: 123
   ZIP: 12345
   ```
8. **Submit** → Payment method added!
9. **Subscribe** to upgrade from trial

---

## 🧪 Stripe Test Cards

**Always Works:**
```
4242 4242 4242 4242
```

**Always Fails:**
```
4000 0000 0000 0002
```

**Requires 3D Secure:**
```
4000 0027 6000 3184
```

More: https://stripe.com/docs/testing

---

## 📊 Monitor Payments

### Stripe Dashboard:
```
→ https://dashboard.stripe.com/test/payments
→ See all test transactions
→ View customer details
→ Check subscription status
```

---

## 🔄 For Production (Later)

When you're ready to go live:

1. **Switch to Live Mode** in Stripe Dashboard
2. Get **Live API keys** (pk_live_ and sk_live_)
3. Update .env with live keys
4. **Verify your business** in Stripe
5. **Add bank account** for payouts

---

## 💰 Money Flow

```
Customer Card
    ↓
Stripe (holds money)
    ↓ (2-7 days)
Your Bank Account
    ↓
Transfer to Payoneer (if needed)
```

---

## 🆘 Quick Troubleshooting

**Problem: Payment page shows error**
→ Check .env has correct Stripe keys
→ Restart Flask server

**Problem: "Stripe not configured"**
→ Make sure STRIPE_SECRET_KEY is set in .env
→ No spaces before/after the key

**Problem: Can't see transactions**
→ Make sure you're in TEST MODE in Stripe Dashboard

---

## 📞 Need Help?

1. Check `STRIPE_SETUP_GUIDE.md` for detailed instructions
2. Stripe Documentation: https://stripe.com/docs
3. Test in TEST MODE first (no real money)

---

## 🎉 You're All Set!

Your payment system is now:
✅ Installed
✅ Configured
✅ Ready to test
✅ Secure (PCI compliant through Stripe)

Just add your Stripe keys and restart the server!
