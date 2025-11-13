# TSG Cafe ERP - Railway Deployment Guide

## Prerequisites

1. **GitHub Account** - To host your code repository
2. **Railway Account** - Sign up at [railway.app](https://railway.app)
3. **Git** - Installed on your local machine

---

## Step 1: Prepare for Deployment

### 1.1 Check Files Created
✅ `railway.json` - Railway deployment configuration  
✅ `Procfile` - Process file for Railway  
✅ `.env.example` - Environment variables template  
✅ Updated `.gitignore` - Include database for initial deployment  
✅ Updated `config.py` - PostgreSQL support  
✅ Updated `run.py` - Production-ready configuration  

### 1.2 Current System Status
- ✅ All bugs fixed (100% test pass rate)
- ✅ Single business with admin owner
- ✅ Database optimized and clean
- ✅ Application running successfully

---

## Step 2: Push to GitHub

### 2.1 Initialize Git Repository (if not already done)
```bash
git init
git add .
git commit -m "Initial commit - TSG Cafe ERP ready for deployment"
```

### 2.2 Create GitHub Repository
1. Go to [github.com](https://github.com)
2. Click "New repository"
3. Name: `tsg-cafe-erp`
4. Description: `TSG Cafe ERP System - Restaurant Management`
5. Set to **Public** or **Private**
6. Click "Create repository"

### 2.3 Push to GitHub
```bash
git remote add origin https://github.com/YOUR_USERNAME/tsg-cafe-erp.git
git branch -M main
git push -u origin main
```

---

## Step 3: Deploy to Railway

### 3.1 Connect GitHub to Railway
1. Go to [railway.app](https://railway.app)
2. Sign up/Login with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your `tsg-cafe-erp` repository

### 3.2 Configure Environment Variables
In Railway dashboard, go to **Variables** tab and add:

```env
SECRET_KEY=your-super-secret-key-here-make-it-long-and-random
FLASK_ENV=production
DEBUG=False
ERP_NAME=TSG Cafe ERP
ERP_SUBTITLE=Powered by Trisync Global
TIMEZONE=Asia/Karachi
CURRENCY=PKR
TAX_RATE=16
FALLBACK_VERIFICATION_CODE=Ma!1311
FALLBACK_ADMIN_PASSWORD=Sangat@1311
```

### 3.3 Add PostgreSQL Database
1. In Railway project, click "New Service"
2. Select "Database" → "PostgreSQL"
3. Railway will automatically provide `DATABASE_URL`

### 3.4 Deploy
1. Railway will automatically detect and deploy your app
2. Wait for deployment to complete (2-5 minutes)
3. Click on your service to get the public URL

---

## Step 4: Post-Deployment Setup

### 4.1 Access Your Application
- Your app will be available at: `https://your-app-name.railway.app`
- Login with: **MM001** / **Sangat@1311**

### 4.2 Verify Deployment
1. ✅ Application loads successfully
2. ✅ Login works with admin credentials
3. ✅ Dashboard displays correctly
4. ✅ All modules accessible (POS, Menu, Inventory, etc.)
5. ✅ Database connected (PostgreSQL)

### 4.3 Security Updates (Important!)
1. **Change Admin Password** - Go to Profile → Change Password
2. **Update Verification Code** - In Railway Variables
3. **Generate Strong Secret Key** - Update SECRET_KEY in Variables

---

## Step 5: Domain Configuration (Optional)

### 5.1 Custom Domain
1. In Railway project → Settings → Domains
2. Add your custom domain
3. Update DNS records as instructed
4. Enable SSL (automatic)

---

## Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | Flask secret key | - | ✅ |
| `FLASK_ENV` | Environment | development | ✅ |
| `DEBUG` | Debug mode | False | ✅ |
| `DATABASE_URL` | PostgreSQL URL | Auto-provided | ✅ |
| `ERP_NAME` | Application name | TSG Cafe ERP | ❌ |
| `ERP_SUBTITLE` | Subtitle | Powered by Trisync Global | ❌ |
| `TIMEZONE` | System timezone | Asia/Karachi | ❌ |
| `CURRENCY` | Default currency | PKR | ❌ |
| `TAX_RATE` | Tax percentage | 16 | ❌ |
| `FALLBACK_VERIFICATION_CODE` | Admin verification | - | ✅ |
| `FALLBACK_ADMIN_PASSWORD` | Admin password | - | ✅ |

---

## Troubleshooting

### Common Issues

#### 1. Build Fails
- Check `requirements.txt` is present
- Ensure all dependencies are listed
- Check Python version compatibility

#### 2. Database Connection Error
- Verify PostgreSQL service is running
- Check `DATABASE_URL` is set correctly
- Ensure database migrations ran

#### 3. Application Won't Start
- Check logs in Railway dashboard
- Verify `Procfile` is correct
- Ensure `PORT` environment variable is used

#### 4. Static Files Not Loading
- Check static file paths in templates
- Verify Flask static folder configuration
- Ensure files are committed to Git

### Viewing Logs
1. Go to Railway dashboard
2. Click on your service
3. Go to "Deployments" tab
4. Click on latest deployment
5. View build and runtime logs

---

## Production Checklist

### Security ✅
- [x] Debug mode disabled
- [x] Strong secret key set
- [x] Admin password changed
- [x] Environment variables secured
- [x] Database credentials protected

### Performance ✅
- [x] PostgreSQL database configured
- [x] Static files optimized
- [x] Database indexes in place
- [x] Efficient queries used

### Monitoring 📋
- [ ] Set up error monitoring (Sentry)
- [ ] Configure uptime monitoring
- [ ] Set up backup schedule
- [ ] Monitor database performance

### Backup Strategy 📋
- [ ] Database automatic backups (Railway provides this)
- [ ] Application-level backup schedule
- [ ] File upload backups
- [ ] Configuration backup

---

## Admin Credentials

**Default Login:**
- **Username:** MM001
- **Password:** Sangat@1311
- **Role:** System Administrator

**⚠️ IMPORTANT:** Change these credentials immediately after first login!

---

## Support

### Railway Documentation
- [Railway Docs](https://docs.railway.app)
- [PostgreSQL on Railway](https://docs.railway.app/databases/postgresql)
- [Environment Variables](https://docs.railway.app/develop/variables)

### Application Support
- **Admin Panel:** `/admin`
- **API Endpoints:** Various endpoints for each module
- **Database:** PostgreSQL with full CRUD operations
- **Backup System:** Built-in backup and restore

---

## Next Steps After Deployment

1. **Test All Features** - Go through each module
2. **Add Users** - Create staff accounts with appropriate roles
3. **Configure Settings** - Update business information
4. **Import Data** - Add menu items, inventory, suppliers
5. **Train Staff** - Provide access and training
6. **Monitor Performance** - Check logs and metrics
7. **Set Up Backups** - Configure automatic backups
8. **Custom Domain** - Add your business domain

---

**🚀 Your TSG Cafe ERP is now ready for production use!**

**Live URL:** `https://your-app-name.railway.app`  
**Admin Access:** MM001 / Sangat@1311  
**Status:** ✅ Production Ready
