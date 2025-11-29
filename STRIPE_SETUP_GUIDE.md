# 🚀 STRIPE PAYMENT SETUP GUIDE

## Complete setup instructions for Stripe payment integration

---

## 📋 Prerequisites

- Active Stripe account (create at https://stripe.com)
- Access to your Stripe Dashboard
- Python environment with requirements installed

---

## 🎯 Step 1: Create Stripe Account

1. Go to https://stripe.com
2. Click **"Sign Up"**
3. Complete registration (free, no credit card required for testing)
4. Verify your email address

---

## 🔑 Step 2: Get Your API Keys

### For Development (Test Mode):

1. Log in to Stripe Dashboard: https://dashboard.stripe.com
2. Make sure you're in **TEST MODE** (toggle in left sidebar)
3. Go to **Developers → API Keys**: https://dashboard.stripe.com/test/apikeys
4. You'll see two keys:

   **Publishable Key** (starts with `pk_test_`)
   - Safe to use in frontend/JavaScript
   - Example: `pk_test_51abc123...`
   - Click "Reveal test key" if hidden

   **Secret Key** (starts with `sk_test_`)
   - **NEVER expose this publicly**
   - Used for backend operations only
   - Click "Reveal test key" → Copy it

5. **IMPORTANT**: Keep these keys secret!

---

## 📝 Step 3: Configure Your Application

### 1. Create .env file from template:

```bash
cp .env.example .env
```

### 2. Edit .env and add your Stripe keys:

```env
# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE
STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET
```

**Example:**
```env
STRIPE_PUBLISHABLE_KEY=pk_test_51abc123xyz...
STRIPE_SECRET_KEY=sk_test_51abc123xyz...
STRIPE_WEBHOOK_SECRET=whsec_123xyz...
```

---

## 🔗 Step 4: Setup Stripe Webhooks (Important!)

Webhooks allow Stripe to notify your app when payments succeed or fail.

### Local Development (Using Stripe CLI):

1. **Install Stripe CLI**: https://stripe.com/docs/stripe-cli

   **Windows:**
   ```powershell
   # Download from: https://github.com/stripe/stripe-cli/releases
   # Extract and add to PATH
   ```

   **Mac:**
   ```bash
   brew install stripe/stripe-cli/stripe
   ```

   **Linux:**
   ```bash
   curl -s https://stripe.com/install-stripe-cli.sh | bash
   ```

2. **Login to Stripe CLI:**
   ```bash
   stripe login
   ```

3. **Forward webhooks to your local server:**
   ```bash
   stripe listen --forward-to localhost:5000/billing/webhook
   ```

4. **Copy the webhook signing secret** (starts with `whsec_`) and add to .env:
   ```env
   STRIPE_WEBHOOK_SECRET=whsec_YOUR_SECRET_HERE
   ```

### Production Deployment:

1. Go to Stripe Dashboard → **Developers → Webhooks**
2. Click **"Add endpoint"**
3. Enter your production URL: `https://yourdomain.com/billing/webhook`
4. Select events to listen to:
   - `payment_intent.succeeded`
   - `invoice.paid`
   - `invoice.payment_failed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. Copy the **Signing secret** and add to production environment variables

---

## 🧪 Step 5: Test Your Setup

### 1. Start your Flask app:
```bash
python run.py
```

### 2. In another terminal, start Stripe webhook forwarding:
```bash
stripe listen --forward-to localhost:5000/billing/webhook
```

### 3. Test the payment flow:

1. Register a new business account
2. Go to **Billing** section
3. Click **"Add Payment Method"**
4. Use Stripe test card numbers:

   **Successful Payment:**
   ```
   Card Number: 4242 4242 4242 4242
   Expiry: Any future date (e.g., 12/25)
   CVC: Any 3 digits (e.g., 123)
   ZIP: Any 5 digits (e.g., 12345)
   ```

   **Declined Payment:**
   ```
   Card Number: 4000 0000 0000 0002
   ```

   **Requires Authentication:**
   ```
   Card Number: 4000 0027 6000 3184
   ```

   More test cards: https://stripe.com/docs/testing

5. Complete the payment
6. Check Stripe Dashboard → **Payments** to see the test transaction

---

## 💰 How the Payment Flow Works

### New User Registration:
```
1. User registers → Selects plan (Cafe/Restaurant/Hotel)
2. System creates account → Status: "trial"
3. User gets 14 days FREE trial
4. Full access to all plan features
```

### During Trial (Days 1-14):
```
1. User has full access
2. System sends reminder emails:
   - Day 7: "7 days left"
   - Day 12: "2 days left"
   - Day 14: "Trial ending today"
```

### Trial Ending (Day 14):
```
1. User logs in → Sees payment modal
2. Must add payment method to continue
3. Redirect to /billing/payment-method
```

### Adding Payment Method:
```
1. User enters card details (Stripe Elements)
2. Stripe creates payment method
3. Card saved to business account
4. Subscription created and activated
5. Status changes: "trial" → "active"
```

### Recurring Billing:
```
1. Stripe automatically charges on billing date
2. Webhook notifies your app: "invoice.paid"
3. System creates invoice record
4. Receipt emailed to user
5. Next billing date calculated
```

### Failed Payment:
```
1. Stripe attempts charge → Fails
2. Webhook: "invoice.payment_failed"
3. Status: "active" → "past_due"
4. Email sent to user
5. System retries according to Stripe settings
6. After retries: Status → "suspended"
```

---

## 📊 Stripe Dashboard Features

### Key Sections:

**Payments**: View all transactions
**Customers**: See all business customers
**Subscriptions**: Manage recurring billing
**Invoices**: View and send invoices
**Webhooks**: Monitor webhook events
**Logs**: Debug API calls

---

## 🔒 Security Best Practices

1. **Never commit .env file**
   ```bash
   # Add to .gitignore
   .env
   ```

2. **Use environment variables in production**
   - Railway: Add in Settings → Variables
   - Heroku: `heroku config:set STRIPE_SECRET_KEY=sk_...`

3. **Verify webhook signatures** (already implemented in PaymentService)

4. **Use HTTPS in production** (required by Stripe)

5. **Rotate keys periodically**

---

## 💸 Pricing & Fees

### Stripe Pricing:
- **No monthly fees**
- **No setup fees**
- **Transaction fee**: 2.9% + $0.30 per successful charge
- **International cards**: +1.5%
- **Currency conversion**: +1%

### Example:
```
Sale: $29 (Cafe plan)
Stripe fee: $1.14 (2.9% + $0.30)
You receive: $27.86
```

### Payout Schedule:
- **Default**: 2-7 business days to your bank
- **Instant payouts**: Available in some countries (0.5% fee)

---

## 🌍 International Usage

### Stripe supports 135+ currencies and works in 45+ countries

**Transfer to Payoneer:**
1. Money goes to Stripe account
2. Transfer from Stripe to your bank/Payoneer
3. Payoneer withdrawal to local bank

---

## 🆘 Troubleshooting

### Issue: "Stripe not configured"
**Solution**: Check STRIPE_SECRET_KEY in .env

### Issue: Webhook not receiving events
**Solution**: 
1. Make sure `stripe listen` is running
2. Check STRIPE_WEBHOOK_SECRET is set
3. Verify endpoint URL in Stripe Dashboard

### Issue: Payment fails with "Invalid API Key"
**Solution**: 
1. Verify key starts with `sk_test_` or `sk_live_`
2. Ensure no spaces before/after key in .env
3. Restart Flask app after changing .env

### Issue: "No such customer"
**Solution**: Business might not have Stripe customer ID. Delete and re-register.

---

## 📚 Additional Resources

- **Stripe Documentation**: https://stripe.com/docs
- **API Reference**: https://stripe.com/docs/api
- **Test Cards**: https://stripe.com/docs/testing
- **Webhooks Guide**: https://stripe.com/docs/webhooks
- **Support**: https://support.stripe.com

---

## ✅ Verification Checklist

Before going live, ensure:

- [ ] Stripe account verified
- [ ] Live API keys obtained
- [ ] Production webhook endpoint configured
- [ ] Webhook signature verification working
- [ ] SSL certificate installed (HTTPS)
- [ ] Test successful payment
- [ ] Test failed payment
- [ ] Test subscription cancellation
- [ ] Error handling in place
- [ ] Email notifications working
- [ ] Payout bank account connected

---

## 🚀 Going to Production

### 1. Switch to Live Mode:
1. Stripe Dashboard → Toggle to **LIVE MODE**
2. Get new API keys (start with `pk_live_` and `sk_live_`)
3. Update production environment variables
4. Configure production webhook endpoint

### 2. Activate Your Account:
1. Go to **Settings → Account details**
2. Complete business verification
3. Add bank account for payouts
4. Review and accept terms

### 3. Deploy:
```bash
# Update production .env
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

---

## 💡 Tips

1. **Start with Test Mode** - No real money involved
2. **Monitor Stripe Dashboard** - Watch for failed payments
3. **Set up email alerts** - Get notified of important events
4. **Test webhook locally** - Use Stripe CLI before deploying
5. **Handle errors gracefully** - Always have fallback UI
6. **Keep keys secure** - Never expose in code or repositories

---

## 🎉 You're All Set!

Your payment system is now ready to accept payments. Users can:
- Start with 14-day free trial
- Add payment methods securely
- Subscribe to plans (Cafe/Restaurant/Hotel)
- View invoices and billing history
- Manage subscriptions

Questions? Check Stripe documentation or contact support!
