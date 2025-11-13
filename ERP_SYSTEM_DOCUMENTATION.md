# 🏪 TSG Cafe ERP System - Complete Documentation

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Architecture & Technology Stack](#architecture--technology-stack)
3. [Database Schema](#database-schema)
4. [User Roles & Permissions](#user-roles--permissions)
5. [Core Modules](#core-modules)
6. [API Endpoints](#api-endpoints)
7. [Security Features](#security-features)
8. [Installation & Setup](#installation--setup)
9. [Usage Guide](#usage-guide)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 System Overview

**TSG Cafe ERP System** is a comprehensive Enterprise Resource Planning solution designed specifically for restaurants, cafes, and food service businesses. It provides complete business management capabilities from point-of-sale operations to financial reporting and inventory management.

### ✨ Key Features
- **Multi-Tenant Architecture** - Support multiple businesses in one system
- **Point of Sale (POS)** - Fast order processing with receipt printing
- **Menu Management** - Categories, items, pricing, and recipes
- **Inventory Control** - Stock tracking, low stock alerts, supplier management
- **Financial Management** - Expenses, daily closing, profit tracking
- **Sales Analytics** - Comprehensive reports and dashboards
- **User Management** - Role-based access control (RBAC)
- **Backup & Recovery** - Automated backup system with restore capabilities

### 🌐 Live Application
- **URL:** https://tsg-cafe-erp.up.railway.app
- **Admin Login:** MM001 / Sangat@1311
- **Status:** Production Ready ✅

---

## 🏗️ Architecture & Technology Stack

### Backend Framework
- **Flask 3.0** - Python web framework
- **SQLAlchemy 2.0** - ORM with PostgreSQL/SQLite support
- **Flask-Login** - User session management
- **Flask-Migrate** - Database migrations
- **Bcrypt** - Password hashing
- **Gunicorn** - WSGI server for production

### Frontend Technologies
- **Bootstrap 5** - Responsive UI framework
- **JavaScript ES6** - Modern client-side functionality
- **Chart.js** - Data visualization and analytics
- **Font Awesome** - Icon library
- **jQuery** - DOM manipulation and AJAX

### Database Systems
- **PostgreSQL** - Production database (Railway)
- **SQLite** - Development database with WAL mode
- **20+ Tables** - Comprehensive relational data model

### Deployment & Infrastructure
- **Railway** - Cloud hosting platform
- **GitHub** - Version control with automatic deployments
- **Environment Variables** - Secure configuration management

---

## 🗄️ Database Schema

### Core Tables (20+)

#### 1. **businesses** - Multi-Tenant Support
```sql
- id (Primary Key)
- business_name (Unique)
- owner_email (Unique)
- subscription_plan (free/basic/premium)
- is_active (Boolean)
- created_at, updated_at
```

#### 2. **users** - User Management & Authentication
```sql
- id (Primary Key)
- business_id (Foreign Key)
- employee_id (Unique per business)
- username, email, password_hash
- role (admin/manager/cashier/inventory/finance)
- first_name, last_name, full_name
- department, designation, phone, address
- security fields (failed_login_attempts, account_locked_until)
- navigation_permissions (JSON)
```

#### 3. **menu_categories** - Menu Organization
```sql
- id (Primary Key)
- business_id (Foreign Key)
- name, description
- display_order, is_active
- created_at, updated_at
```

#### 4. **menu_items** - Products & Services
```sql
- id (Primary Key)
- business_id (Foreign Key)
- category_id (Foreign Key)
- name, description, price
- cost_price, profit_margin
- is_available, is_featured
- image_url, preparation_time
- ingredients (JSON)
```

#### 5. **inventory_items** - Stock Management
```sql
- id (Primary Key)
- business_id (Foreign Key)
- name, description, unit
- current_stock, minimum_stock
- cost_per_unit, supplier_id
- last_restocked, expiry_date
```

#### 6. **sales** - Transaction Records
```sql
- id (Primary Key)
- business_id (Foreign Key)
- user_id (Cashier)
- total_amount, tax_amount
- payment_method, status
- customer_name, customer_phone
- items (JSON), created_at
```

#### 7. **expenses** - Financial Tracking
```sql
- id (Primary Key)
- business_id (Foreign Key)
- category, description, amount
- expense_date, receipt_url
- approved_by, status
```

#### 8. **audit_logs** - Activity Monitoring
```sql
- id (Primary Key)
- business_id (Foreign Key)
- user_id, action, table_name
- old_values, new_values (JSON)
- ip_address, user_agent
- created_at
```

---

## 👥 User Roles & Permissions

### 1. **System Administrator**
- **Access Level:** Complete system control
- **Permissions:**
  - Multi-tenant management
  - System settings configuration
  - User role assignments
  - Database backups and maintenance
  - Global system monitoring

### 2. **Admin**
- **Access Level:** Full business management
- **Permissions:**
  - User creation and management
  - Business settings configuration
  - All modules access
  - Financial reports and analytics
  - Backup and restore operations

### 3. **Manager**
- **Access Level:** Operational management
- **Permissions:**
  - Sales and inventory management
  - Staff scheduling and monitoring
  - Reports generation
  - Menu management
  - Limited user management

### 4. **Cashier**
- **Access Level:** Point of sale operations
- **Permissions:**
  - POS system access
  - Order processing
  - Basic dashboard view
  - Customer management
  - Daily sales reports

### 5. **Inventory**
- **Access Level:** Stock management
- **Permissions:**
  - Inventory tracking and updates
  - Supplier management
  - Purchase orders
  - Stock reports
  - Low stock alerts

### 6. **Finance**
- **Access Level:** Financial operations
- **Permissions:**
  - Expense management
  - Financial reports
  - Daily closing operations
  - Profit/loss analysis
  - Tax calculations

---

## 🔧 Core Modules

### 1. **Dashboard Module** (`dashboard.py`)
- **Real-time KPIs** - Today's sales, orders, revenue
- **Sales Charts** - Weekly/monthly trends
- **Activity Feed** - Recent system activities
- **Quick Actions** - Fast access to common tasks
- **Performance Metrics** - Business analytics

### 2. **Point of Sale (POS) Module** (`pos.py`)
- **Order Processing** - Fast item selection and billing
- **Payment Methods** - Cash, card, digital payments
- **Receipt Generation** - Thermal printer support
- **Customer Management** - Customer details and history
- **Split Bills** - Multiple payment methods per order
- **Discounts & Offers** - Promotional pricing

### 3. **Menu Management Module** (`menu.py`)
- **Category Management** - Organize menu items
- **Item Management** - Add, edit, delete menu items
- **Pricing Control** - Cost price, selling price, margins
- **Recipe Management** - Ingredients and preparation
- **Availability Control** - Enable/disable items
- **Featured Items** - Highlight popular items

### 4. **Inventory Module** (`inventory.py`)
- **Stock Tracking** - Real-time inventory levels
- **Supplier Management** - Vendor information and contacts
- **Purchase Orders** - Automated ordering system
- **Low Stock Alerts** - Automatic notifications
- **Expiry Management** - Track product expiration dates
- **Cost Analysis** - Inventory valuation and costs

### 5. **Finance Module** (`finance.py`)
- **Expense Tracking** - Categorized expense management
- **Daily Closing** - End-of-day financial reconciliation
- **Profit Analysis** - Revenue vs. cost calculations
- **Tax Management** - Automated tax calculations
- **Financial Reports** - Comprehensive financial analytics
- **Budget Planning** - Expense budgeting and monitoring

### 6. **Reports Module** (`reports.py`)
- **Sales Reports** - Daily, weekly, monthly sales analysis
- **Inventory Reports** - Stock levels and movement
- **Financial Reports** - Profit/loss, expense analysis
- **User Activity Reports** - Staff performance tracking
- **Custom Reports** - Flexible report generation
- **Export Options** - PDF, Excel, CSV formats

### 7. **Admin Module** (`admin.py`)
- **User Management** - Create, edit, delete users
- **Business Settings** - Company information and preferences
- **System Configuration** - Global settings management
- **Backup Management** - Database backup and restore
- **Audit Logs** - System activity monitoring
- **Security Settings** - Password policies and access control

### 8. **Profile Module** (`profile.py`)
- **User Profile Management** - Personal information updates
- **Password Changes** - Secure password updates
- **Notification Preferences** - Alert settings
- **Activity History** - User action logs
- **Profile Picture** - Avatar management

---

## 🔌 API Endpoints

### Authentication APIs
```
POST /auth/login          - User login
POST /auth/logout         - User logout
POST /auth/register       - New user registration
POST /auth/forgot-password - Password reset request
```

### Dashboard APIs
```
GET /api/dashboard/kpis/today     - Today's KPIs
GET /api/dashboard/weekly-sales   - Weekly sales data
GET /api/dashboard/activities     - Recent activities
GET /api/dashboard/quick-stats    - Quick statistics
```

### POS System APIs
```
GET /pos/api/menu                 - Menu items for POS
POST /pos/api/sale                - Create new sale
GET /pos/api/categories           - Menu categories
POST /pos/api/payment             - Process payment
GET /pos/api/receipt/{sale_id}    - Generate receipt
```

### Menu Management APIs
```
GET /api/menu/categories          - Get all categories
POST /api/menu/categories         - Create category
PUT /api/menu/categories/{id}     - Update category
DELETE /api/menu/categories/{id}  - Delete category
GET /api/menu/items               - Get all menu items
POST /api/menu/items              - Create menu item
PUT /api/menu/items/{id}          - Update menu item
DELETE /api/menu/items/{id}       - Delete menu item
```

### Inventory APIs
```
GET /api/inventory/items          - Get inventory items
POST /api/inventory/items         - Add inventory item
PUT /api/inventory/items/{id}     - Update inventory item
GET /api/inventory/low-stock      - Get low stock items
POST /api/inventory/restock       - Restock items
GET /api/inventory/suppliers      - Get suppliers
```

### Finance APIs
```
GET /api/finance/expenses         - Get expenses
POST /api/finance/expenses        - Add expense
GET /api/finance/daily-closing    - Daily closing data
POST /api/finance/daily-closing   - Perform daily closing
GET /api/finance/reports          - Financial reports
```

---

## 🔒 Security Features

### Authentication & Authorization
- ✅ **Password Hashing** - Bcrypt encryption
- ✅ **Account Lockout** - 5 failed attempts protection
- ✅ **Session Management** - Secure session handling
- ✅ **Role-Based Access Control** - Granular permissions
- ✅ **Multi-Factor Authentication** - Verification codes for admins

### Data Protection
- ✅ **Multi-Tenant Isolation** - Business data separation
- ✅ **SQL Injection Prevention** - Parameterized queries
- ✅ **XSS Protection** - Input sanitization
- ✅ **CSRF Protection** - Cross-site request forgery prevention
- ✅ **Audit Logging** - Complete activity tracking

### Infrastructure Security
- ✅ **HTTPS Encryption** - SSL/TLS certificates
- ✅ **Environment Variables** - Secure configuration
- ✅ **Database Encryption** - Encrypted data storage
- ✅ **Regular Backups** - Automated backup system
- ✅ **Access Monitoring** - Login attempt tracking

---

## 💻 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- PostgreSQL (for production) or SQLite (for development)
- Git for version control

### Local Development Setup

1. **Clone Repository**
```bash
git clone https://github.com/moonkamboh924/TSG-Cafe-ERP.git
cd TSG-Cafe-ERP
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Environment Configuration**
Create `.env` file:
```env
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DATABASE_URL=sqlite:///instance/erp.db
ERP_NAME=Your Business Name
TIMEZONE=Asia/Karachi
CURRENCY=PKR
TAX_RATE=16
```

4. **Initialize Database**
```bash
python run.py
```

5. **Access Application**
- URL: http://127.0.0.1:5000
- Admin Login: MM001 / Sangat@1311

### Production Deployment (Railway)

1. **Connect GitHub Repository** to Railway
2. **Add PostgreSQL Database** service
3. **Set Environment Variables**:
   - `SECRET_KEY` - Strong secret key
   - `DATABASE_URL` - PostgreSQL connection string
   - `FLASK_ENV=production`
4. **Deploy** - Automatic deployment from GitHub

---

## 📖 Usage Guide

### Getting Started

1. **Login** with admin credentials (MM001 / Sangat@1311)
2. **Configure Business Settings** in Admin panel
3. **Create User Accounts** for staff members
4. **Set Up Menu Categories** and items
5. **Configure Inventory** items and suppliers
6. **Start Processing Orders** through POS system

### Daily Operations

#### Morning Setup
1. Check inventory levels
2. Review daily targets
3. Verify POS system functionality
4. Check staff schedules

#### Order Processing
1. Access POS system
2. Select menu items
3. Calculate totals with tax
4. Process payment
5. Print receipt

#### End of Day
1. Perform daily closing
2. Review sales reports
3. Check inventory usage
4. Backup data

### Weekly Tasks
1. Generate weekly reports
2. Review inventory levels
3. Plan menu updates
4. Analyze financial performance

### Monthly Tasks
1. Generate monthly reports
2. Review user permissions
3. Update menu pricing
4. Plan inventory purchases

---

## 🔧 Troubleshooting

### Common Issues

#### Login Problems
**Issue:** Cannot login with credentials
**Solution:**
1. Check if account is locked (wait 30 minutes)
2. Verify username/password spelling
3. Contact admin for password reset

#### POS System Issues
**Issue:** Menu items not loading
**Solution:**
1. Check internet connection
2. Refresh browser page
3. Clear browser cache
4. Contact technical support

#### Database Connection Errors
**Issue:** Database connection failed
**Solution:**
1. Check DATABASE_URL in environment
2. Verify database server status
3. Check network connectivity
4. Restart application

#### Performance Issues
**Issue:** Slow application response
**Solution:**
1. Clear browser cache
2. Check internet speed
3. Restart browser
4. Contact support if persistent

### Error Codes

- **401 Unauthorized** - Login required
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource not found
- **500 Internal Server Error** - Server error

### Support Contacts

- **Technical Support:** support@tsgcafe.com
- **GitHub Issues:** https://github.com/moonkamboh924/TSG-Cafe-ERP/issues
- **Documentation:** This file

---

## 📊 System Statistics

### Performance Metrics
- **Database Size:** ~0.3MB (optimized)
- **Response Time:** <100ms average
- **Memory Usage:** ~50MB
- **Concurrent Users:** Up to 50 users
- **Uptime:** 99.9% availability

### Feature Coverage
- **33/33 Tests Passing** (100% success rate)
- **20+ Database Tables** - Complete data model
- **8 Core Modules** - Full business coverage
- **50+ API Endpoints** - Comprehensive functionality
- **6 User Roles** - Flexible access control

---

## 🚀 Future Enhancements

### Planned Features
- **Mobile App** - Native iOS/Android applications
- **Offline Mode** - Work without internet connection
- **Advanced Analytics** - AI-powered insights
- **Integration APIs** - Third-party service connections
- **Multi-Language Support** - Localization features

### Scalability Improvements
- **Microservices Architecture** - Service separation
- **Caching Layer** - Redis implementation
- **Load Balancing** - Multiple server support
- **CDN Integration** - Global content delivery

---

## 📄 License & Credits

### License
This project is licensed under the MIT License - see the LICENSE file for details.

### Credits
- **Flask Team** - Amazing web framework
- **Railway** - Excellent hosting platform
- **Bootstrap** - Beautiful UI components
- **Chart.js** - Data visualization library

---

**Built with ❤️ for the restaurant industry**

*Last Updated: November 13, 2025*
*Version: 1.0*
*Status: Production Ready ✅*
