"""add_business_name_history_table

Revision ID: 5d69d6a621a9
Revises: 794a1cf25072
Create Date: 2025-12-06 17:56:28.983277

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5d69d6a621a9'
down_revision = '794a1cf25072'
branch_labels = None
depends_on = None


def upgrade():
    # Create business_name_history table
    op.create_table('business_name_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('business_name', sa.String(length=200), nullable=False),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.Column('changed_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_business_name_history_business_id'), 'business_name_history', ['business_id'], unique=False)
    op.create_index(op.f('ix_business_name_history_business_name'), 'business_name_history', ['business_name'], unique=False)
    
    # Populate with existing business names
    from sqlalchemy import text
    conn = op.get_bind()
    
    # Get all existing businesses
    result = conn.execute(text("SELECT id, business_name, created_at FROM businesses"))
    businesses = result.fetchall()
    
    for business_id, business_name, created_at in businesses:
        conn.execute(
            text("INSERT INTO business_name_history (business_id, business_name, changed_at) VALUES (:business_id, :business_name, :changed_at)"),
            {"business_id": business_id, "business_name": business_name, "changed_at": created_at}
        )


def downgrade():
    op.drop_index(op.f('ix_business_name_history_business_name'), table_name='business_name_history')
    op.drop_index(op.f('ix_business_name_history_business_id'), table_name='business_name_history')
    op.drop_table('business_name_history')
