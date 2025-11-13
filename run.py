import os
from app import create_app

# Create Flask application
app = create_app()

if __name__ == '__main__':
    # For development - get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'production') == 'development'
    
    print("Starting TSG Cafe ERP System...")
    print(f"Running on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
