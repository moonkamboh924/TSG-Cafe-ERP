"""add subscription system

Revision ID: 20251130033300
Revises: 738320292d7c
Create Date: 2025-11-30 03:33:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251130033300'
down_revision = '738320292d7c'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to businesses table
    op.add_column('businesses', sa.Column('trial_end_date', sa.DateTime(), nullable=True))
    op.add_column('businesses', sa.Column('subscription_status', sa.String(length=20), nullable=False, server_default='trial'))
    
    # Create subscriptions table
    op.create_table('subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('plan', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('billing_cycle', sa.String(length=20), nullable=False, server_default='monthly'),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('next_billing_date', sa.DateTime(), nullable=True),
        sa.Column('trial_end_date', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('payment_method_id', sa.String(length=100), nullable=True),
        sa.Column('last_payment_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscriptions_business_id'), 'subscriptions', ['business_id'], unique=False)
    
    # Create invoices table
    op.create_table('invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('payment_status', sa.String(length=20), nullable=False, server_default='unpaid'),
        sa.Column('billing_period_start', sa.DateTime(), nullable=False),
        sa.Column('billing_period_end', sa.DateTime(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=False),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('transaction_id', sa.String(length=100), nullable=True),
        sa.Column('payment_details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invoice_number')
    )
    op.create_index(op.f('ix_invoices_business_id'), 'invoices', ['business_id'], unique=False)
    op.create_index(op.f('ix_invoices_invoice_number'), 'invoices', ['invoice_number'], unique=False)
    op.create_index(op.f('ix_invoices_subscription_id'), 'invoices', ['subscription_id'], unique=False)
    
    # Create payment_methods table
    op.create_table('payment_methods',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('provider_payment_method_id', sa.String(length=100), nullable=False),
        sa.Column('last4', sa.String(length=4), nullable=True),
        sa.Column('brand', sa.String(length=20), nullable=True),
        sa.Column('exp_month', sa.Integer(), nullable=True),
        sa.Column('exp_year', sa.Integer(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create plan_features table
    op.create_table('plan_features',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan', sa.String(length=20), nullable=False),
        sa.Column('feature_key', sa.String(length=50), nullable=False),
        sa.Column('feature_value', sa.String(length=100), nullable=False),
        sa.Column('feature_type', sa.String(length=20), nullable=False, server_default='limit'),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plan', 'feature_key', name='unique_plan_feature')
    )
    op.create_index(op.f('ix_plan_features_plan'), 'plan_features', ['plan'], unique=False)


def downgrade():
    # Drop tables
    op.drop_table('plan_features')
    op.drop_table('payment_methods')
    op.drop_index(op.f('ix_invoices_subscription_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_invoice_number'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_business_id'), table_name='invoices')
    op.drop_table('invoices')
    op.drop_index(op.f('ix_subscriptions_business_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
    
    # Drop columns from businesses table
    op.drop_column('businesses', 'subscription_status')
    op.drop_column('businesses', 'trial_end_date')
