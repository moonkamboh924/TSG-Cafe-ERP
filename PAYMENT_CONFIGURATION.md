# Payment System Configuration Guide

## Current Status
✅ Payment system is fully functional  
✅ Test data has been removed  
✅ Ready for production configuration  

## Quick Start

### Option 1: Local Development Mode (Current)
**No configuration needed!** The system automatically runs in local mode when Stripe is not configured.

**What you can do:**
- Add payment methods manually via the UI
- Test subscription billing flows
- Develop and test without real payments
- All payment data stored locally

**Access:** Navigate to **Billing → Payment Methods**

---

### Option 2: Production Mode with Stripe

#### Step 1: Get Stripe API Keys
1. Sign up at https://stripe.com (if you haven't already)
2. Go to **Developers → API Keys**
3. Copy your keys:
   - **Test Mode**: Use for testing with test cards
   - **Live Mode**: Use for real payments (requires account activation)

#### Step 2: Configure Environment Variables

**For Railway Deployment:**
```bash
# In Railway dashboard, go to Variables
STRIPE_SECRET_KEY=sk_test_your_key_here  # or sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here  # or pk_live_...
```

**For Local Development:**
Edit `config.py`:
```python
class Config:
    # ... existing config ...
    
    # Stripe Configuration
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', 'sk_test_your_key_here')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', 'pk_test_your_key_here')
```

Or set environment variables:
```bash
# Windows PowerShell
$env:STRIPE_SECRET_KEY="sk_test_your_key_here"
$env:STRIPE_PUBLISHABLE_KEY="pk_test_your_key_here"

# Windows CMD
set STRIPE_SECRET_KEY=sk_test_your_key_here
set STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here
```

#### Step 3: Restart Application
```bash
python run.py
```

The system will automatically detect Stripe configuration and switch to Stripe mode!

---

## Testing with Stripe Test Cards

When using Stripe Test Mode, use these test card numbers:

| Card Number | Brand | Result |
|------------|-------|--------|
| 4242 4242 4242 4242 | Visa | Success |
| 5555 5555 5555 4444 | Mastercard | Success |
| 3782 822463 10005 | American Express | Success |
| 6011 1111 1111 1117 | Discover | Success |
| 4000 0000 0000 0002 | Visa | Card declined |
| 4000 0000 0000 9995 | Visa | Insufficient funds |

- **CVV**: Use any 3 digits (or 4 for Amex)
- **Expiry**: Use any future date
- **ZIP**: Use any 5 digits

More test cards: https://stripe.com/docs/testing

---

## Verification

### Check if Stripe is Enabled
```python
from app.services.payment_service import PaymentService

print(f"Stripe enabled: {PaymentService.is_stripe_enabled()}")
```

### Expected Behavior

**Local Mode (No Stripe):**
- ✅ Shows manual payment entry form
- ✅ Info banner: "Development Mode"
- ✅ Can add payment methods without API calls
- ✅ No real payment processing

**Stripe Mode (Configured):**
- ✅ Shows Stripe Elements card input
- ✅ Info banner: "Secure Payment"
- ✅ PCI-compliant card tokenization
- ✅ Real payment processing capability

---

## Troubleshooting

### "Invalid API Key" Error
- ❌ Check that your Stripe keys are correct
- ❌ Ensure no extra spaces in environment variables
- ❌ Verify you're using the right mode (test vs live)
- ❌ Check that keys start with `sk_test_` or `sk_live_`

### Stripe Not Detecting
- ❌ Restart the application after setting environment variables
- ❌ Check `config.py` is loading the variables correctly
- ❌ Verify keys are not set to placeholder values

### Payment Methods Not Saving
- ❌ Check browser console for JavaScript errors
- ❌ Verify database is writable
- ❌ Check server logs for errors
- ❌ Ensure multi-tenant context is set (logged in)

---

## Production Checklist

Before going live with real payments:

- [ ] Activate your Stripe account (complete verification)
- [ ] Switch to **Live Mode** keys (`sk_live_...` and `pk_live_...`)
- [ ] Enable HTTPS on your domain
- [ ] Configure Stripe webhooks (for subscription events)
- [ ] Set up proper error monitoring
- [ ] Test complete payment flow with small amounts
- [ ] Review Stripe dashboard for payment settings
- [ ] Configure payment method types (cards, ACH, etc.)
- [ ] Set up email notifications for payment events
- [ ] Review and update terms of service

---

## Support & Resources

- **Stripe Documentation**: https://stripe.com/docs
- **Payment System Docs**: See `PAYMENT_SYSTEM.md`
- **Test Mode**: Always test thoroughly before going live
- **API Reference**: https://stripe.com/docs/api

---

## Summary

Your payment system is **production-ready** and works in two modes:

1. **Local Mode** (default): For development without Stripe
2. **Stripe Mode**: For production with real payments

Simply add Stripe keys when you're ready, and the system automatically switches modes. No code changes needed! 🚀
