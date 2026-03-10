"""Add loyalty and bar features

Revision ID: 2b3c4d5e6f7g
Revises: a1b2c3d4e5f6
Create Date: 2026-03-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2b3c4d5e6f7g'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add fields to users table using batch operations for SQLite compatibility
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('loyalty_level', sa.String(), server_default='Начинающий', nullable=True))
        batch_op.add_column(sa.Column('bonus_points', sa.Integer(), server_default='0', nullable=True))
        batch_op.add_column(sa.Column('balance', sa.Integer(), server_default='0', nullable=True))

    # 2. Add bar_items table
    op.create_table(
        'bar_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('club_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), server_default='Напитки', nullable=True),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('is_available', sa.Boolean(), server_default='true', nullable=True),
        sa.ForeignKeyConstraint(['club_id'], ['clubs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bar_items_id'), 'bar_items', ['id'], unique=False)

    # 3. Add bar_orders table
    op.create_table(
        'bar_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('club_id', sa.Integer(), nullable=False),
        sa.Column('pc_name', sa.String(), nullable=False),
        sa.Column('items', sa.JSON(), nullable=False),
        sa.Column('total_price', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), server_default='NEW', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['club_id'], ['clubs.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bar_orders_id'), 'bar_orders', ['id'], unique=False)
    op.create_index(op.f('ix_bar_orders_user_id'), 'bar_orders', ['user_id'], unique=False)


def downgrade() -> None:
    # 3. Drop bar_orders table
    op.drop_index(op.f('ix_bar_orders_user_id'), table_name='bar_orders')
    op.drop_index(op.f('ix_bar_orders_id'), table_name='bar_orders')
    op.drop_table('bar_orders')

    # 2. Drop bar_items table
    op.drop_index(op.f('ix_bar_items_id'), table_name='bar_items')
    op.drop_table('bar_items')

    # 1. Drop fields from users table
    op.drop_column('users', 'balance')
    op.drop_column('users', 'bonus_points')
    op.drop_column('users', 'loyalty_level')
