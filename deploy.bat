@echo off
echo ============================================================
echo TSG Cafe ERP - Railway Deployment Script
echo ============================================================
echo.

echo 1. Checking Git status...
git status
echo.

echo 2. Adding all files to Git...
git add .
echo.

echo 3. Committing changes...
set /p commit_msg="Enter commit message (or press Enter for default): "
if "%commit_msg%"=="" set commit_msg=Deploy TSG Cafe ERP to Railway

git commit -m "%commit_msg%"
echo.

echo 4. Current remotes:
git remote -v
echo.

echo 5. Ready to push to GitHub!
echo.
echo Next steps:
echo 1. Create a GitHub repository named 'tsg-cafe-erp'
echo 2. Run: git remote add origin https://github.com/YOUR_USERNAME/tsg-cafe-erp.git
echo 3. Run: git push -u origin main
echo 4. Go to railway.app and deploy from GitHub
echo.

echo ============================================================
echo Deployment preparation completed!
echo ============================================================
pause
