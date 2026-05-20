"""add skill registry tables

Create Date: 2026-05-20 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "9d09ea94b2ac"
down_revision = "da6fb0208061"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "skills",
        sa.Column(
            "workspace",
            sa.String(length=63),
            nullable=False,
            server_default=sa.text("'default'"),
        ),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column(
            "kind",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'skill'"),
        ),
        sa.Column("description", sa.String(length=5000), nullable=True),
        sa.Column("last_registered_version", sa.String(length=256), nullable=True),
        sa.Column("latest_version", sa.String(length=256), nullable=True),
        sa.Column("created_by", sa.String(length=256), nullable=True),
        sa.Column("last_updated_by", sa.String(length=256), nullable=True),
        sa.Column("creation_timestamp", sa.BigInteger(), nullable=True),
        sa.Column("last_updated_timestamp", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("workspace", "name", name="skills_pk"),
    )

    op.create_table(
        "skill_versions",
        sa.Column("workspace", sa.String(length=63), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("version", sa.String(length=256), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=True),
        sa.Column("source", sa.String(length=2048), nullable=True),
        sa.Column("subpath", sa.String(length=2048), nullable=True),
        sa.Column("content_digest", sa.String(length=512), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column("run_id", sa.String(length=32), nullable=True),
        sa.Column("created_by", sa.String(length=256), nullable=True),
        sa.Column("last_updated_by", sa.String(length=256), nullable=True),
        sa.Column("creation_timestamp", sa.BigInteger(), nullable=True),
        sa.Column("last_updated_timestamp", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("workspace", "name", "version", name="skill_versions_pk"),
        sa.ForeignKeyConstraint(
            ["workspace", "name"],
            ["skills.workspace", "skills.name"],
            name="skill_versions_skill_fk",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "skill_tags",
        sa.Column("workspace", sa.String(length=63), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("key", sa.String(length=256), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("workspace", "name", "key", name="skill_tags_pk"),
        sa.ForeignKeyConstraint(
            ["workspace", "name"],
            ["skills.workspace", "skills.name"],
            name="skill_tags_skill_fk",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "skill_version_tags",
        sa.Column("workspace", sa.String(length=63), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("version", sa.String(length=256), nullable=False),
        sa.Column("key", sa.String(length=256), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint(
            "workspace", "name", "version", "key", name="skill_version_tags_pk"
        ),
        sa.ForeignKeyConstraint(
            ["workspace", "name", "version"],
            ["skill_versions.workspace", "skill_versions.name", "skill_versions.version"],
            name="skill_version_tags_version_fk",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "skill_aliases",
        sa.Column("workspace", sa.String(length=63), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("alias", sa.String(length=256), nullable=False),
        sa.Column("version", sa.String(length=256), nullable=False),
        sa.PrimaryKeyConstraint("workspace", "name", "alias", name="skill_aliases_pk"),
        sa.ForeignKeyConstraint(
            ["workspace", "name"],
            ["skills.workspace", "skills.name"],
            name="skill_aliases_skill_fk",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "skill_alias_history",
        sa.Column("workspace", sa.String(length=63), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("alias", sa.String(length=256), nullable=False),
        sa.Column("old_version", sa.String(length=256), nullable=True),
        sa.Column("new_version", sa.String(length=256), nullable=True),
        sa.Column("changed_by", sa.String(length=256), nullable=True),
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint(
            "workspace", "name", "alias", "timestamp", name="skill_alias_history_pk"
        ),
        sa.ForeignKeyConstraint(
            ["workspace", "name"],
            ["skills.workspace", "skills.name"],
            name="skill_alias_history_skill_fk",
            ondelete="CASCADE",
        ),
    )


def downgrade():
    op.drop_table("skill_alias_history")
    op.drop_table("skill_aliases")
    op.drop_table("skill_version_tags")
    op.drop_table("skill_tags")
    op.drop_table("skill_versions")
    op.drop_table("skills")
