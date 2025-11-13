#!/usr/bin/env python3
"""
Simple Railway deployment test script
This bypasses all complex app logic to test basic Railway functionality
"""
import os
import sys
from flask import Flask, jsonify

# Create minimal Flask app
app = Flask(__name__)

@app.route('/')
def root():
    return '''
    <h1>🚀 Railway Test - TSG Cafe ERP</h1>
    <p><strong>Status:</strong> ✅ Railway deployment working!</p>
    <p><strong>Python Version:</strong> {}</p>
    <p><strong>PORT:</strong> {}</p>
    <p><strong>DATABASE_URL:</strong> {}</p>
    <p><a href="/health">Health Check</a></p>
    <p><a href="/env">Environment Variables</a></p>
    '''.format(
        sys.version,
        os.environ.get('PORT', 'Not set'),
        'Set' if os.environ.get('DATABASE_URL') else 'Not set'
    )

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'TSG Cafe ERP - Railway Test',
        'python_version': sys.version,
        'port': os.environ.get('PORT'),
        'database_url_set': bool(os.environ.get('DATABASE_URL'))
    })

@app.route('/env')
def env_vars():
    # Show safe environment variables
    safe_vars = {}
    for key, value in os.environ.items():
        if 'PASSWORD' not in key.upper() and 'SECRET' not in key.upper() and 'KEY' not in key.upper():
            safe_vars[key] = value
        else:
            safe_vars[key] = '[HIDDEN]'
    
    return jsonify(safe_vars)

@app.route('/db-test')
def db_test():
    try:
        import psycopg2
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            # Test connection
            conn = psycopg2.connect(db_url)
            conn.close()
            return jsonify({'database': 'connected', 'type': 'postgresql'})
        else:
            return jsonify({'database': 'no_url', 'type': 'none'})
    except Exception as e:
        return jsonify({'database': 'error', 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Railway test server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
