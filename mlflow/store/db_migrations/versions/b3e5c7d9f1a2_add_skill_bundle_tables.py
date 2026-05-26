"""add skill bundle tables

Create Date: 2026-05-21 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "b3e5c7d9f1a2"
down_revision = "9d09ea94b2ac"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "skill_bundles",
        sa.Column(
            "workspace",
            sa.String(length=63),
            nullable=False,
            server_default=sa.text("'default'"),
        ),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.String(length=5000), nullable=True),
        sa.Column("created_by", sa.String(length=256), nullable=True),
        sa.Column("last_updated_by", sa.String(length=256), nullable=True),
        sa.Column("creation_timestamp", sa.BigInteger(), nullable=True),
        sa.Column("last_updated_timestamp", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("workspace", "name", name="skill_bundles_pk"),
    )

    op.create_table(
        "skill_bundle_items",
        sa.Column("workspace", sa.String(length=63), nullable=False),
        sa.Column("bundle_name", sa.String(length=256), nullable=False),
        sa.Column("skill_name", sa.String(length=256), nullable=False),
        sa.Column("version", sa.String(length=256), nullable=False),
        sa.PrimaryKeyConstraint(
            "workspace", "bundle_name", "skill_name", name="skill_bundle_items_pk"
        ),
        sa.ForeignKeyConstraint(
            ["workspace", "bundle_name"],
            ["skill_bundles.workspace", "skill_bundles.name"],
            name="skill_bundle_items_bundle_fk",
            ondelete="CASCADE",
        ),
    )


def downgrade():
    op.drop_table("skill_bundle_items")
    op.drop_table("skill_bundles")
