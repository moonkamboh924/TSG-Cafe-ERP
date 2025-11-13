#!/usr/bin/env python3
"""
Simple test app to diagnose Railway deployment
"""
import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1>TSG ERP - Simple Test</h1>
    <p>Status: Working!</p>
    <p><a href="/info">System Info</a></p>
    <p><a href="/health">Health Check</a></p>
    '''

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'port': os.environ.get('PORT', 'Not set'),
        'database_url': 'Set' if os.environ.get('DATABASE_URL') else 'Not set'
    })

@app.route('/info')
def info():
    return jsonify({
        'python_version': os.sys.version,
        'environment_variables': {
            'PORT': os.environ.get('PORT'),
            'DATABASE_URL': 'Set' if os.environ.get('DATABASE_URL') else 'Not set',
            'FLASK_ENV': os.environ.get('FLASK_ENV')
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
