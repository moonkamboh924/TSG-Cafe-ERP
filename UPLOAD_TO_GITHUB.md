# 🌐 Upload to GitHub Without Git (Web Method)

If Git installation is taking too long or you prefer not to use command line, here's how to upload your code directly through GitHub's website:

## 📤 Method 1: GitHub Web Upload (Easiest - No Git Needed!)

### Step 1: Create Repository
1. Go to: https://github.com/new
2. **Repository name**: `sc-erp`
3. **Visibility**: Public
4. **DON'T** check "Add a README file"
5. Click **"Create repository"**

### Step 2: Prepare Your Files
1. Create a ZIP file of your project:
   - Go to `d:\SC-ERP - SC`
   - Select all files EXCEPT:
     - `__pycache__` folders
     - `instance` folder
     - `logs` folder
     - `.env` file
     - `*.db` files
   - Right-click → Send to → Compressed (zipped) folder
   - Name it: `sc-erp.zip`

### Step 3: Upload to GitHub
1. On your new GitHub repository page, click **"uploading an existing file"**
2. Drag and drop your ZIP file OR click "choose your files"
3. Wait for upload to complete
4. Add commit message: "Initial commit - SC ERP System"
5. Click **"Commit changes"**

### Step 4: Extract Files (if uploaded as ZIP)
If you uploaded a ZIP, you need to extract it:
1. Click on the ZIP file in GitHub
2. Click "Download"
3. Extract locally
4. Upload individual files/folders back to GitHub

**OR BETTER:** Upload files individually (see Method 2 below)

---

## 📤 Method 2: Upload Files Individually (More Control)

### Step 1: Create Repository (same as above)

### Step 2: Upload Files One by One
1. In your repository, click **"Add file"** → **"Upload files"**
2. Drag these files from `d:\SC-ERP - SC`:
   - All `.py` files (run.py, config.py, logging_config.py)
   - All `.txt` files (requirements.txt, runtime.txt)
   - All `.md` files (README.md, DEPLOYMENT_GUIDE.md, etc.)
   - All `.yaml` files (render.yaml)
   - Procfile
   - .gitignore

3. Then upload folders:
   - `app` folder (entire folder with all contents)
   - `migrations` folder

4. Add commit message: "Initial commit - SC ERP System"
5. Click **"Commit changes"**

### Important: DON'T Upload These
- ❌ `__pycache__` folders
- ❌ `instance` folder
- ❌ `logs` folder
- ❌ `.env` file
- ❌ `*.db` files (erp.db, etc.)

---

## 📤 Method 3: Use GitHub Desktop (Recommended if Git fails)

1. **Download GitHub Desktop**: https://desktop.github.com/
2. Install and sign in
3. Click **"File"** → **"Add local repository"**
4. Browse to: `d:\SC-ERP - SC`
5. Click **"Add repository"**
6. Click **"Publish repository"**
7. Uncheck "Keep this code private"
8. Click **"Publish repository"**
9. Done! ✅

---

## ✅ After Upload - Deploy on Render

Once your code is on GitHub (by any method):

1. Go to: https://render.com/
2. Sign up with your GitHub account
3. Click **"New +"** → **"Web Service"**
4. Connect your `sc-erp` repository
5. Configure:
   - **Build Command**: `pip install -r requirements.txt && flask db upgrade`
   - **Start Command**: `gunicorn run:app`
   - **Plan**: Free
6. Add environment variables:
   - `SECRET_KEY`: (click Generate)
   - `FLASK_ENV`: `production`
   - `ERP_NAME`: `Sangat Cafe`
   - `TIMEZONE`: `Asia/Karachi`
   - `CURRENCY`: `PKR`
7. Click **"Create Web Service"**

### Add Database
1. In Render, click **"New +"** → **"PostgreSQL"**
2. Name: `sc-erp-db`
3. Plan: **Free**
4. Click **"Create Database"**
5. Copy the **"Internal Database URL"**
6. Go to your Web Service → Environment
7. Add: `DATABASE_URL` = (paste database URL)
8. Save

---

## 🎉 Your ERP is Live!

Your site will be at: `https://sc-erp.onrender.com` (or your chosen name)

---

## 🔄 To Update Later

### If using GitHub Web:
1. Go to your repository
2. Click on the file you want to edit
3. Click the pencil icon (Edit)
4. Make changes
5. Click "Commit changes"
6. Wait 2-3 minutes - Render auto-deploys! ✨

### If using GitHub Desktop:
1. Make changes in your local files
2. Open GitHub Desktop
3. Write commit message
4. Click "Commit to main"
5. Click "Push origin"
6. Wait 2-3 minutes - Render auto-deploys! ✨

---

**Choose whichever method is easiest for you!** 🚀
