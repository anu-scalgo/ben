"""Script to run Alembic migrations."""

import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic.config import Config
from alembic import command


def run_migration(message: str = None, autogenerate: bool = True):
    """Run Alembic migration."""
    alembic_cfg = Config("alembic.ini")

    if message:
        # Create new migration
        command.revision(
            alembic_cfg,
            autogenerate=autogenerate,
            message=message,
        )
    else:
        # Apply migrations
        command.upgrade(alembic_cfg, "head")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Alembic migrations")
    parser.add_argument(
        "--create",
        type=str,
        help="Create a new migration with the given message",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply pending migrations",
    )
    parser.add_argument(
        "--downgrade",
        type=int,
        help="Downgrade by N revisions",
    )

    args = parser.parse_args()

    alembic_cfg = Config("alembic.ini")

    if args.create:
        command.revision(alembic_cfg, autogenerate=True, message=args.create)
    elif args.downgrade:
        command.downgrade(alembic_cfg, f"-{args.downgrade}")
    else:
        command.upgrade(alembic_cfg, "head")

