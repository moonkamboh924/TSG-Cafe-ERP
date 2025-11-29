# Twilio SMS Setup for Pakistan

## Why Twilio for Pakistan?

TextLocal is being decommissioned (Nov 30, 2025), and most "free" SMS services either:
- Don't work in Pakistan (Fast2SMS - India only)
- Require payment despite claiming free tiers (MSG91)

**Twilio is the best option for Pakistan** because:
- ✅ Works globally including Pakistan
- ✅ $15 free trial credit (good for ~300 SMS to Pakistan)
- ✅ No credit card required for trial
- ✅ Reliable and well-documented
- ✅ Pay-as-you-go after trial (₨10-15 per SMS)

---

## Setup Steps

### 1. Sign Up for Twilio

1. Go to **https://www.twilio.com/try-twilio**
2. Click **"Sign up and start building"**
3. Fill in your details:
   - Email address
   - First name & Last name
   - Password
   - Check "I'm not a robot"
4. Verify your email address
5. Verify your phone number (use your Pakistani mobile number)

### 2. Get Your Credentials

After logging in to the Twilio Console:

1. **Dashboard** → You'll see:
   - **Account SID** (e.g., `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
   - **Auth Token** (click to reveal, e.g., `1234567890abcdef1234567890abcdef`)
   
2. **Get a Phone Number:**
   - Click **"Get a Trial Number"** button
   - Twilio will assign you a US number (e.g., `+1 555-123-4567`)
   - This number will send SMS to Pakistan

### 3. Configure Your Application

1. Create a `.env` file in your project root (copy from `.env.example`):

```bash
# SMS Configuration
SMS_PROVIDER=TWILIO

# Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-32-character-auth-token
TWILIO_PHONE_NUMBER=+15551234567

# Email Configuration (use Gmail)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

2. Replace with your actual credentials from Twilio Console

### 4. Test Your Setup

Run your Flask app and try registration:

```powershell
python run.py
```

Visit: http://localhost:5000/tenant/register

**Important:** When entering your Pakistani mobile number:
- **With country code:** `+923001234567`
- **Without country code:** `3001234567` (system auto-adds +92)

### 5. Verify Trial Number

On first SMS send, Twilio will ask you to **verify the recipient number**:

1. Go to **Phone Numbers** → **Manage** → **Verified Caller IDs**
2. Click **"Add a new number"**
3. Enter your Pakistani mobile number: `+923001234567`
4. You'll receive a verification code via call/SMS
5. Enter the code to verify

After verification, your app can send SMS to that number.

---

## Pricing Information

### Trial Account
- **$15.00 free credit**
- SMS to Pakistan: **~$0.05 per message** (₨14-15)
- **~300 SMS** with trial credit
- Can only send to **verified numbers**

### Paid Account (After Trial)
- **No monthly fees** - pay only for what you use
- SMS to Pakistan: **$0.05** per message
- Receive 1 free phone number included
- No credit card required until trial ends

### Cost Estimation
- **10 users/day:** $0.50/day = $15/month (300 SMS)
- **50 users/day:** $2.50/day = $75/month (1,500 SMS)
- **100 users/day:** $5.00/day = $150/month (3,000 SMS)

---

## Troubleshooting

### Error: "The number you are trying to send to is not verified"

**Solution:** Verify the recipient number in Twilio Console:
1. Go to **Phone Numbers** → **Verified Caller IDs**
2. Add the Pakistani number with +92 country code
3. Complete SMS/call verification

### Error: "Authentication failed"

**Solution:** Check your credentials:
- Ensure `TWILIO_ACCOUNT_SID` starts with `AC`
- Ensure `TWILIO_AUTH_TOKEN` is 32 characters
- No extra spaces in `.env` file

### Error: "Invalid phone number"

**Solution:** Use correct format:
- ✅ Correct: `+923001234567`
- ❌ Wrong: `03001234567` (missing country code)
- ❌ Wrong: `923001234567` (missing + sign)

### SMS Not Received

**Possible reasons:**
1. Number not verified (trial accounts)
2. Insufficient trial credit
3. Network delay (wait 1-2 minutes)
4. Check Twilio Console → **Monitor** → **Logs** → **Messaging** for delivery status

---

## Alternative: After Trial Ends

### Option 1: Upgrade to Paid Account
- Add credit card to Twilio
- Top up as needed (minimum $20 recommended)
- Continue using same setup

### Option 2: Use Local Pakistani SMS Provider
Consider these Pakistani SMS providers:
- **Eocean** - https://eocean.us/
- **SMS.to** - https://sms.to/
- **Twizo Pakistan** - https://www.twizo.com/

These typically offer better rates for Pakistan (₨2-5 per SMS) but require:
- Pakistani business registration
- Sender ID approval
- Bulk purchase minimum

---

## Support

- **Twilio Documentation:** https://www.twilio.com/docs/sms
- **Twilio Console:** https://console.twilio.com/
- **Support:** https://support.twilio.com/

---

## Current Status

✅ **Twilio package installed** (`twilio==8.10.0`)  
✅ **Code updated** to support Twilio as default  
✅ **Config ready** - just add your credentials to `.env`  
⏳ **Next:** Sign up and get your Twilio credentials
