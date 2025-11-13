#!/usr/bin/env python3
"""
WSGI entry point for TSG Cafe ERP System
This file is used by Gunicorn to serve the Flask application
"""

import os
import sys

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask application
from run import app

# This is what Gunicorn will use
application = app

if __name__ == "__main__":
    # For direct execution
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
