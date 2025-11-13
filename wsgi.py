"""
WSGI entry point for TSG Cafe ERP System - Multi-tenant
"""
from run import app

# Expose application for Gunicorn
application = app

if __name__ == "__main__":
    app.run()
