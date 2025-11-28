"""add business_id to audit_logs

Revision ID: add_business_id_audit
Revises: 738320292d7c
Create Date: 2025-11-28 21:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_business_id_audit'
down_revision = '738320292d7c'
branch_labels = None
depends_on = None


def upgrade():
    # Add business_id column to audit_logs table
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('business_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_audit_logs_business_id', ['business_id'], unique=False)
        batch_op.create_foreign_key('fk_audit_logs_business_id', 'businesses', ['business_id'], ['id'])


def downgrade():
    # Remove business_id column from audit_logs table
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.drop_constraint('fk_audit_logs_business_id', type_='foreignkey')
        batch_op.drop_index('ix_audit_logs_business_id')
        batch_op.drop_column('business_id')
