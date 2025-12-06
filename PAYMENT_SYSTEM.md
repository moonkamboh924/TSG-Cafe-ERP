# Payment Method System Documentation

## Overview
The payment method system supports both **Stripe integration** for production and **local manual mode** for development/testing.

## Features

### Dual-Mode Operation
1. **Stripe Mode** (Production)
   - Requires valid Stripe API keys
   - Full integration with Stripe Payment Methods API
   - Secure tokenization of payment data
   - PCI compliance through Stripe

2. **Local Mode** (Development)
   - No Stripe configuration needed
   - Manual payment method entry
   - Simulates payment storage for testing
   - Does not process real payments

## Configuration

### Stripe Mode
Set these environment variables in `config.py`:
```python
STRIPE_SECRET_KEY = 'sk_test_...'  # or sk_live_...
STRIPE_PUBLISHABLE_KEY = 'pk_test_...'  # or pk_live_...
```

### Local Mode
Leave Stripe keys unset or use placeholder values:
```python
STRIPE_SECRET_KEY = 'your-stripe-secret-key'
STRIPE_PUBLISHABLE_KEY = 'your-stripe-publishable-key'
```

## Database Schema

### PaymentMethod Model
```python
- id: Primary key
- business_id: Foreign key to businesses
- type: Payment type (card, bank_account, manual)
- provider: Payment provider (stripe, manual, paypal)
- provider_payment_method_id: External ID from provider (nullable)
- last4: Last 4 digits of card/account
- brand: Card brand (visa, mastercard, amex, discover)
- exp_month: Expiration month
- exp_year: Expiration year
- cardholder_name: Name on card
- billing_address: Billing address (JSON/text)
- is_default: Whether this is the default payment method
- is_active: Whether this payment method is active
- created_at: Creation timestamp
- updated_at: Last update timestamp
```

## API Endpoints

### Add Payment Method
**Endpoint:** `POST /billing/add-payment-method`

**Stripe Mode Request:**
```json
{
  "type": "card",
  "provider": "stripe",
  "stripe_payment_method_id": "pm_...",
  "set_default": true
}
```

**Local Mode Request:**
```json
{
  "type": "card",
  "provider": "manual",
  "cardholder_name": "John Doe",
  "brand": "visa",
  "last4": "4242",
  "exp_month": 12,
  "exp_year": 2025,
  "set_default": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Payment method added successfully",
  "payment_method": {
    "id": 1,
    "type": "card",
    "provider": "manual",
    "last4": "4242",
    "brand": "visa",
    "exp_month": 12,
    "exp_year": 2025,
    "cardholder_name": "John Doe",
    "is_default": true,
    "is_active": true,
    "is_expired": false
  }
}
```

## Usage Examples

### Python - Adding Payment Method
```python
from app.services.payment_service import PaymentService

# Local mode
payment_data = {
    'type': 'card',
    'provider': 'manual',
    'cardholder_name': 'John Doe',
    'brand': 'visa',
    'last4': '4242',
    'exp_month': 12,
    'exp_year': 2025
}

pm = PaymentService.add_payment_method(
    business_id=1,
    payment_method_data=payment_data,
    set_default=True
)
```

### JavaScript - Frontend Integration

**Stripe Mode:**
```javascript
// Create payment method via Stripe
const {paymentMethod, error} = await stripe.createPaymentMethod({
    type: 'card',
    card: cardElement,
});

// Send to backend
const response = await fetch('/billing/add-payment-method', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        type: 'card',
        provider: 'stripe',
        stripe_payment_method_id: paymentMethod.id,
        set_default: true
    })
});
```

**Local Mode:**
```javascript
// Send manual payment data to backend
const response = await fetch('/billing/add-payment-method', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        type: 'card',
        provider: 'manual',
        cardholder_name: document.getElementById('cardholderName').value,
        brand: document.getElementById('cardBrand').value,
        last4: document.getElementById('last4').value,
        exp_month: parseInt(document.getElementById('expMonth').value),
        exp_year: parseInt(document.getElementById('expYear').value),
        set_default: true
    })
});
```

## Security Considerations

### Stripe Mode
- ✅ PCI compliant through Stripe
- ✅ Card data never touches your server
- ✅ Tokenization handled by Stripe Elements
- ✅ Secure HTTPS communication

### Local Mode
- ⚠️ For development/testing only
- ⚠️ Does not process real payments
- ⚠️ Stores masked payment data (last 4 digits only)
- ⚠️ Not suitable for production use

## Testing

### Manual Testing
1. Start the server: `python run.py`
2. Login to the application
3. Navigate to Billing → Payment Methods
4. Add a test payment method:
   - **Stripe Mode:** Use Stripe test cards (4242 4242 4242 4242)
   - **Local Mode:** Enter any valid format data

### Automated Testing
```python
from app.services.payment_service import PaymentService

# Test local mode
payment_data = {
    'type': 'card',
    'provider': 'manual',
    'cardholder_name': 'Test User',
    'brand': 'visa',
    'last4': '4242',
    'exp_month': 12,
    'exp_year': 2025
}

pm = PaymentService.add_payment_method(1, payment_data, True)
assert pm.brand == 'visa'
assert pm.last4 == '4242'
assert pm.is_default == True
```

## Migration

### Database Migration
Applied migration: `20251206154134_add_payment_method_fields.py`

**Changes:**
- Added `cardholder_name` column (VARCHAR(100))
- Added `billing_address` column (TEXT)
- Made `provider_payment_method_id` nullable

## Service Methods

### PaymentService Class

#### `is_stripe_enabled()` → bool
Returns True if Stripe is properly configured with valid API keys.

#### `get_publishable_key()` → str|None
Returns the Stripe publishable key if available, otherwise None.

#### `add_payment_method(business_id, payment_method_data, set_default)` → PaymentMethod
Main entry point. Routes to Stripe or local mode based on data.

#### `_add_payment_method_stripe(business_id, stripe_pm_id, set_default)` → PaymentMethod
Handles Stripe payment method creation.

#### `_add_payment_method_local(business_id, payment_data, set_default)` → PaymentMethod
Handles local/manual payment method creation.

## Multi-Tenant Support
✅ All payment methods are properly scoped to `business_id`
✅ Queries filtered by current business context
✅ Default payment method per business
✅ Isolated payment data between tenants

## Future Enhancements
- [ ] Payment method deletion/deactivation endpoint
- [ ] Set default payment method endpoint
- [ ] Payment method update (expiry date, etc.)
- [ ] Support for bank accounts and ACH
- [ ] Support for PayPal integration
- [ ] Payment history and transaction records
- [ ] Automatic expiry notifications
- [ ] Card brand logo detection
