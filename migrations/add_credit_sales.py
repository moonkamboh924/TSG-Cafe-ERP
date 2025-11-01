"""
Database migration to add credit sales functionality
"""

from app import create_app
from app.extensions import db
from app.models import CreditSale, CreditPayment

def upgrade():
    """Add credit sales tables"""
    app = create_app()
    
    with app.app_context():
        # Create the credit sales tables
        db.create_all()
        print("✅ Credit sales tables created successfully")

def downgrade():
    """Remove credit sales tables"""
    app = create_app()
    
    with app.app_context():
        # Drop the credit sales tables
        db.session.execute('DROP TABLE IF EXISTS credit_payments')
        db.session.execute('DROP TABLE IF EXISTS credit_sales')
        db.session.commit()
        print("✅ Credit sales tables removed successfully")

if __name__ == '__main__':
    upgrade()
