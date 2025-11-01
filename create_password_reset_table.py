"""
Create password_reset_requests table
Run this script to create the missing table
"""

from app import create_app
from app.extensions import db
from sqlalchemy import text

def create_password_reset_table():
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("CREATING PASSWORD RESET REQUESTS TABLE")
        print("=" * 60)
        
        try:
            # Check if table exists
            result = db.session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='password_reset_requests'"
            ))
            exists = result.fetchone()
            
            if exists:
                print("✓ Table already exists. Dropping and recreating...")
                db.session.execute(text("DROP TABLE IF EXISTS password_reset_requests"))
                db.session.commit()
            
            # Create table
            print("Creating password_reset_requests table...")
            db.session.execute(text("""
                CREATE TABLE password_reset_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    admin_notes TEXT,
                    new_password_set BOOLEAN NOT NULL DEFAULT 0,
                    approved_at DATETIME,
                    approved_by_id INTEGER,
                    user_notified BOOLEAN NOT NULL DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (approved_by_id) REFERENCES users(id)
                )
            """))
            db.session.commit()
            
            print("✓ Table created successfully!")
            
            # Verify
            result = db.session.execute(text("SELECT COUNT(*) FROM password_reset_requests"))
            count = result.scalar()
            print(f"✓ Table verified. Current records: {count}")
            
            print("\n" + "=" * 60)
            print("✅ PASSWORD RESET TABLE CREATED SUCCESSFULLY!")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    create_password_reset_table()
