"""add_business_code_to_business

Revision ID: 794a1cf25072
Revises: 20251206154134
Create Date: 2025-12-06 16:59:51.732524

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '794a1cf25072'
down_revision = '20251206154134'
branch_labels = None
depends_on = None


def upgrade():
    # Add business_code column
    op.add_column('businesses', sa.Column('business_code', sa.String(length=50), nullable=True))
    
    # Create unique index
    op.create_index(op.f('ix_businesses_business_code'), 'businesses', ['business_code'], unique=True)
    
    # Generate business codes for existing businesses
    from sqlalchemy import text
    conn = op.get_bind()
    
    # Get all existing businesses ordered by ID
    result = conn.execute(text("SELECT id, business_name FROM businesses ORDER BY id"))
    businesses = result.fetchall()
    
    import re
    
    for idx, (business_id, business_name) in enumerate(businesses, start=1):
        # Extract letters only and convert to uppercase
        letters_only = re.sub(r'[^A-Za-z]', '', business_name).upper()
        
        if not letters_only:
            abbreviation = 'BIZ'
        else:
            # Create abbreviation from business name
            words = re.findall(r'[A-Z][a-z]*', business_name.title())
            
            if len(words) >= 2:
                # Use first letter of each word
                abbreviation = ''.join(word[0] for word in words if word)
            elif len(letters_only) >= 3:
                # Use first 3-4 letters
                abbreviation = letters_only[:4]
            else:
                # Use all letters and pad if needed
                abbreviation = letters_only.ljust(3, 'X')
        
        # Limit abbreviation to 4 characters max
        abbreviation = abbreviation[:4]
        
        # Generate code: ABBREVIATION + 3-digit padded number
        business_code = f"{abbreviation}{idx:03d}"
        
        # Update the business with the generated code
        conn.execute(
            text("UPDATE businesses SET business_code = :code WHERE id = :id"),
            {"code": business_code, "id": business_id}
        )


def downgrade():
    # Remove index and column
    op.drop_index(op.f('ix_businesses_business_code'), table_name='businesses')
    op.drop_column('businesses', 'business_code')
