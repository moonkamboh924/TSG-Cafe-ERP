import os
import sys

print("=" * 50)
print("TSG Cafe ERP System - Multi-tenant")
print("=" * 50)

# Debug environment
print(f"Python version: {sys.version}")
print(f"PORT: {os.environ.get('PORT', 'Not set')}")
print(f"DATABASE_URL: {'Set' if os.environ.get('DATABASE_URL') else 'Not set'}")
print(f"FLASK_ENV: {os.environ.get('FLASK_ENV', 'Not set')}")

try:
    from app import create_app
    print("[OK] App module imported successfully")
    
    # Create Flask application
    app = create_app()
    print("[OK] Flask application created successfully")
    
except Exception as e:
    print(f"[ERROR] Error creating Flask app: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if __name__ == '__main__':
    # For development - get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'production') == 'development'
    
    print(f"Starting server on port {port} (debug={debug})")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=debug)
    except Exception as e:
        print(f"[ERROR] Error starting server: {str(e)}")
        import traceback
        traceback.print_exc()
