"""Add iCafe audit tables (icafe_sessions, audit_discrepancies)

Revision ID: 9i8h7g6f5e4d
Revises: 3c4d5e6f7g8h
Create Date: 2026-03-13

"""
from alembic import op
import sqlalchemy as sa

revision = '9i8h7g6f5e4d'
down_revision = '3c4d5e6f7g8h'
branch_labels = None
depends_on = None


def upgrade():
    # --- icafe_sessions ---
    op.create_table(
        'icafe_sessions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('club_id', sa.Integer(), sa.ForeignKey('clubs.id'), nullable=False, index=True),
        sa.Column('icafe_session_id', sa.String(), nullable=False, index=True),
        sa.Column('icafe_pc_id', sa.String(), nullable=False, index=True),
        sa.Column('icafe_pc_name', sa.String(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('icafe_price', sa.Integer(), nullable=True),
        sa.Column('icafe_paid', sa.Integer(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True),
    )

    # --- audit_discrepancies ---
    op.create_table(
        'audit_discrepancies',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('club_id', sa.Integer(), sa.ForeignKey('clubs.id'), nullable=False, index=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('discrepancy_type', sa.String(), nullable=False, index=True),
        sa.Column('booking_id', sa.Integer(), sa.ForeignKey('bookings.id'), nullable=True),
        sa.Column('icafe_session_id', sa.Integer(), sa.ForeignKey('icafe_sessions.id'), nullable=True),
        sa.Column('da_amount', sa.Integer(), nullable=True),
        sa.Column('icafe_amount', sa.Integer(), nullable=True),
        sa.Column('shadow_amount', sa.Integer(), nullable=True),
        sa.Column('session_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pc_name', sa.String(), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), default=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_note', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
    )


def downgrade():
    op.drop_table('audit_discrepancies')
    op.drop_table('icafe_sessions')
