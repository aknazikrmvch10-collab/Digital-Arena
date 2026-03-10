"""Add financial fields to bookings

Revision ID: 3c4d5e6f7g8h
Revises: 2b3c4d5e6f7g
Create Date: 2026-03-10 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c4d5e6f7g8h'
down_revision: Union[str, Sequence[str], None] = '2b3c4d5e6f7g'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add financial columns to bookings table
    op.add_column('bookings', sa.Column('total_price', sa.Integer(), nullable=True))
    op.add_column('bookings', sa.Column('discount_amount', sa.Integer(), server_default='0', nullable=True))
    op.add_column('bookings', sa.Column('earned_points', sa.Integer(), server_default='0', nullable=True))


def downgrade() -> None:
    # Drop financial columns from bookings table
    op.drop_column('bookings', 'earned_points')
    op.drop_column('bookings', 'discount_amount')
    op.drop_column('bookings', 'total_price')
