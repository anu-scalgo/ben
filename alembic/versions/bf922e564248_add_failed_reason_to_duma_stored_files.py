"""add_failed_reason_to_duma_stored_files

Revision ID: bf922e564248
Revises: 8c1df4b018aa
Create Date: 2026-01-21 10:46:03.418625

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf922e564248'
down_revision: Union[str, None] = '8c1df4b018aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add failed_reason column to duma_stored_files table
    op.add_column('duma_stored_files', sa.Column('failed_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove failed_reason column from duma_stored_files table
    op.drop_column('duma_stored_files', 'failed_reason')

