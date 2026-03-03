"""add club_zone_setting

Revision ID: a1b2c3d4e5f6
Revises: f4a15e181f30
Create Date: 2026-03-03 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f4a15e181f30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create club_zone_settings table."""
    op.create_table(
        'club_zone_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('club_id', sa.Integer(), nullable=False),
        sa.Column('zone_name', sa.String(), nullable=False),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['club_id'], ['clubs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_club_zone_settings_id'), 'club_zone_settings', ['id'], unique=False)
    op.create_index(op.f('ix_club_zone_settings_club_id'), 'club_zone_settings', ['club_id'], unique=False)
    op.create_index(op.f('ix_club_zone_settings_zone_name'), 'club_zone_settings', ['zone_name'], unique=False)


def downgrade() -> None:
    """Drop club_zone_settings table."""
    op.drop_index(op.f('ix_club_zone_settings_zone_name'), table_name='club_zone_settings')
    op.drop_index(op.f('ix_club_zone_settings_club_id'), table_name='club_zone_settings')
    op.drop_index(op.f('ix_club_zone_settings_id'), table_name='club_zone_settings')
    op.drop_table('club_zone_settings')
