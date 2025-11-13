# TSG Cafe ERP System

A comprehensive Enterprise Resource Planning (ERP) system designed specifically for restaurants and cafes. Built with Flask and modern web technologies.

## 🚀 Live Demo

**Live Application:** [Deploy to Railway](https://railway.app)  
**Admin Login:** MM001 / Sangat@1311  

## ✨ Features

### 🏪 Complete Restaurant Management
- **Point of Sale (POS)** - Fast order processing with receipt printing
- **Menu Management** - Categories, items, pricing, and recipes
- **Inventory Control** - Stock tracking, low stock alerts, supplier management
- **Financial Management** - Expenses, daily closing, profit tracking
- **Sales Analytics** - Comprehensive reports and dashboards
- **User Management** - Role-based access control (RBAC)

### 🔐 Security & Multi-Tenancy
- **Multi-Tenant Architecture** - Support multiple businesses
- **Role-Based Access** - Admin, Manager, Cashier, Inventory, Finance roles
- **Account Security** - Password hashing, account lockout, audit logging
- **Protected Admin System** - Verification codes for sensitive operations

### 📊 Analytics & Reporting
- **Real-time Dashboard** - KPIs, sales charts, activity monitoring
- **Financial Reports** - Daily, weekly, monthly revenue analysis
- **Inventory Reports** - Stock levels, usage patterns
- **Sales Reports** - Transaction history, customer analytics

### 🛠️ Technical Features
- **Responsive Design** - Works on desktop, tablet, and mobile
- **Automatic Backups** - Scheduled database backups with restore
- **Timezone Support** - Multi-timezone handling
- **Audit Logging** - Complete activity tracking
- **Data Integrity** - Foreign key constraints, validation

## 🏗️ Technology Stack

### Backend
- **Flask 3.0** - Python web framework
- **SQLAlchemy 2.0** - ORM with PostgreSQL/SQLite support
- **Flask-Login** - User session management
- **Flask-Migrate** - Database migrations
- **Bcrypt** - Password hashing

### Frontend
- **Bootstrap 5** - Responsive UI framework
- **JavaScript ES6** - Modern client-side functionality
- **Chart.js** - Data visualization
- **Font Awesome** - Icons

### Database
- **PostgreSQL** - Production database (Railway)
- **SQLite** - Development database
- **20 Tables** - Comprehensive data model

### Deployment
- **Railway** - Cloud hosting platform
- **Gunicorn** - WSGI server
- **PostgreSQL** - Managed database

## 📋 System Requirements

### Development
- Python 3.8+
- SQLite (included)
- 512MB RAM
- 100MB storage

### Production
- PostgreSQL database
- 1GB RAM recommended
- 500MB storage
- HTTPS support

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/tsg-cafe-erp.git
cd tsg-cafe-erp
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Application
```bash
python run.py
```

### 4. Access Application
- **URL:** http://127.0.0.1:5000
- **Admin:** MM001 / Sangat@1311

## 🌐 Railway Deployment

### One-Click Deploy
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

### Manual Deployment
1. **Fork this repository**
2. **Connect to Railway**
3. **Add PostgreSQL database**
4. **Set environment variables**
5. **Deploy automatically**

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed instructions.

## ⚙️ Configuration

### Environment Variables
```env
SECRET_KEY=your-secret-key
FLASK_ENV=production
DATABASE_URL=postgresql://...
ERP_NAME=Your Business Name
TIMEZONE=Asia/Karachi
CURRENCY=PKR
TAX_RATE=16
```

### Default Settings
- **Business:** TSG Cafe System
- **Currency:** PKR (Pakistani Rupee)
- **Timezone:** Asia/Karachi
- **Tax Rate:** 16%
- **Language:** English

## 👥 User Roles

| Role | Permissions |
|------|-------------|
| **System Administrator** | Full system access, multi-tenant management |
| **Admin** | Business management, user creation, settings |
| **Manager** | Sales, inventory, reports, limited admin |
| **Cashier** | POS operations, basic dashboard |
| **Inventory** | Stock management, suppliers, purchase orders |
| **Finance** | Expenses, financial reports, daily closing |

## 📊 Database Schema

### Core Tables (20)
- **businesses** - Multi-tenant business entities
- **users** - User accounts with RBAC
- **menu_categories** - Menu organization
- **menu_items** - Products and services
- **inventory_items** - Stock management
- **sales** - Transaction records
- **expenses** - Financial tracking
- **audit_logs** - Activity monitoring

## 🔧 API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/register` - New user registration

### POS System
- `GET /pos/api/menu` - Menu items
- `POST /pos/api/sale` - Create sale
- `GET /pos/api/categories` - Menu categories

### Dashboard
- `GET /api/dashboard/kpis/today` - Today's KPIs
- `GET /api/dashboard/weekly-sales` - Sales chart data
- `GET /api/dashboard/activities` - Recent activities

## 🧪 Testing

### Test Coverage
- **33/33 Tests Passing** (100% success rate)
- **Database Integrity** - Foreign key validation
- **Security Testing** - Authentication, authorization
- **Functionality Testing** - All modules verified

### Run Tests
```bash
python comprehensive_test.py
```

## 📈 Performance

### Metrics
- **Database Size:** ~0.3MB (optimized)
- **Response Time:** <100ms average
- **Memory Usage:** ~50MB
- **Database Indexes:** 20 optimized indexes

### Optimizations
- SQLite WAL mode for development
- PostgreSQL with connection pooling
- Efficient query design
- Proper indexing strategy

## 🔒 Security Features

### Authentication
- ✅ Password hashing (bcrypt)
- ✅ Account lockout (5 attempts)
- ✅ Session management
- ✅ CSRF protection

### Authorization
- ✅ Role-based access control
- ✅ Navigation permissions
- ✅ Protected admin functions
- ✅ Verification codes

### Data Protection
- ✅ Multi-tenant isolation
- ✅ Audit logging
- ✅ Input validation
- ✅ SQL injection prevention

## 📱 Mobile Support

### Responsive Design
- ✅ Mobile-first approach
- ✅ Touch-friendly interface
- ✅ Optimized for tablets
- ✅ Progressive Web App ready

### POS Mobile Features
- Quick order entry
- Touch-based navigation
- Mobile receipt printing
- Offline capability (planned)

## 🔄 Backup & Recovery

### Automatic Backups
- **Frequency:** Daily/Weekly/Monthly
- **Storage:** Local and cloud options
- **Includes:** Database, uploads, logs
- **Restore:** One-click restoration

### Manual Backups
- Admin panel backup creation
- Download backup files
- Restore from uploaded backup
- Database integrity verification

## 📞 Support

### Documentation
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [User Manual](docs/USER_MANUAL.md)
- [API Documentation](docs/API.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

### Community
- **Issues:** GitHub Issues
- **Discussions:** GitHub Discussions
- **Email:** support@tsgcafe.com

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create feature branch
3. Make changes
4. Run tests
5. Submit pull request

### Code Standards
- Python PEP 8 style
- Comprehensive testing
- Documentation updates
- Security considerations

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Flask Team** - Amazing web framework
- **Railway** - Excellent hosting platform
- **Bootstrap** - Beautiful UI components
- **Chart.js** - Data visualization

---

## 📊 Project Stats

![GitHub repo size](https://img.shields.io/github/repo-size/username/tsg-cafe-erp)
![GitHub language count](https://img.shields.io/github/languages/count/username/tsg-cafe-erp)
![GitHub top language](https://img.shields.io/github/languages/top/username/tsg-cafe-erp)

**Built with ❤️ for the restaurant industry**

---

### 🚀 Ready to deploy? Follow the [Deployment Guide](DEPLOYMENT_GUIDE.md)!
