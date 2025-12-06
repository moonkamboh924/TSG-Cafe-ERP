"""add_payment_method_fields

Revision ID: 20251206154134
Revises: 20251130033300
Create Date: 2025-12-06 15:41:34

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251206154134'
down_revision = '20251130033300'
branch_labels = None
depends_on = None


def upgrade():
    # Add new fields to payment_methods table
    with op.batch_alter_table('payment_methods', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cardholder_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('billing_address', sa.Text(), nullable=True))
        
        # Make provider_payment_method_id nullable (for local payment methods)
        batch_op.alter_column('provider_payment_method_id',
                              existing_type=sa.String(length=100),
                              nullable=True)


def downgrade():
    # Remove new fields from payment_methods table
    with op.batch_alter_table('payment_methods', schema=None) as batch_op:
        batch_op.drop_column('billing_address')
        batch_op.drop_column('cardholder_name')
        
        # Restore provider_payment_method_id to not nullable
        batch_op.alter_column('provider_payment_method_id',
                              existing_type=sa.String(length=100),
                              nullable=False)
