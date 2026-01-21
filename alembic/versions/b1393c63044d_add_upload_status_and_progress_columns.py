"""add_upload_status_and_progress_columns

Revision ID: b1393c63044d
Revises: bf922e564248
Create Date: 2026-01-21 12:38:42.767640

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1393c63044d'
down_revision: Union[str, None] = 'bf922e564248'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if upload_status column exists before adding
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('duma_stored_files')]
    
    if 'upload_status' not in columns:
        # Add upload_status column with default value 'pending'
        op.add_column('duma_stored_files', 
            sa.Column('upload_status', sa.String(), nullable=True, server_default='pending')
        )
        # Set existing rows to 'completed' status (they were uploaded before this feature)
        op.execute("UPDATE duma_stored_files SET upload_status = 'completed' WHERE upload_status = 'pending'")
    
    if 'upload_progress' not in columns:
        # Add upload_progress column with default value 0
        op.add_column('duma_stored_files', 
            sa.Column('upload_progress', sa.Integer(), nullable=False, server_default='0')
        )


def downgrade() -> None:
    # Check if columns exist before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('duma_stored_files')]
    
    if 'upload_progress' in columns:
        op.drop_column('duma_stored_files', 'upload_progress')
    if 'upload_status' in columns:
        op.drop_column('duma_stored_files', 'upload_status')

