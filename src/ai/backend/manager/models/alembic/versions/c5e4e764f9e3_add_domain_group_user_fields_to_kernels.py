"""add domain, group, user fields to kernels

Revision ID: c5e4e764f9e3
Revises: 6f1c1b83870a
Create Date: 2019-05-28 10:22:56.904061

"""
import textwrap

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import text

from ai.backend.manager.models.base import GUID, ForeignKeyIDColumn, IDColumn, convention

# revision identifiers, used by Alembic.
revision = "c5e4e764f9e3"
down_revision = "6f1c1b83870a"
branch_labels = None
depends_on = None


def upgrade():
    metadata = sa.MetaData(naming_convention=convention)
    # partial tables for data migration
    groups = sa.Table(
        "groups",
        metadata,
        IDColumn("id"),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=512)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column(
            "domain_name",
            sa.String(length=64),
            sa.ForeignKey("domains.name", onupdate="CASCADE", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    users = sa.Table(
        "users",
        metadata,
        IDColumn("uuid"),
    )
    kernels = sa.Table(
        "kernels",
        metadata,
        IDColumn(),
        sa.Column("access_key", sa.String(length=20), sa.ForeignKey("keypairs.access_key")),
    )
    keypairs = sa.Table(
        "keypairs",
        metadata,
        sa.Column("user_id", sa.String(length=256), index=True),
        sa.Column("access_key", sa.String(length=20), primary_key=True),
        ForeignKeyIDColumn("user", "users.uuid", nullable=False),
    )

    op.add_column("kernels", sa.Column("domain_name", sa.String(length=64), nullable=True))
    op.add_column("kernels", sa.Column("group_id", GUID(), nullable=True))
    op.add_column("kernels", sa.Column("user_uuid", GUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_kernels_group_id_groups"), "kernels", "groups", ["group_id"], ["id"]
    )
    op.create_foreign_key(
        op.f("fk_kernels_user_uuid_users"), "kernels", "users", ["user_uuid"], ["uuid"]
    )
    op.create_foreign_key(
        op.f("fk_kernels_domain_name_domains"), "kernels", "domains", ["domain_name"], ["name"]
    )

    # Create default group in the default domain.
    # Assumption: "default" domain must exist
    connection = op.get_bind()
    query = sa.insert(groups).values(
        name="default", description="Default group", is_active=True, domain_name="default"
    )
    query = textwrap.dedent("""\
        INSERT INTO groups (name, description, is_active, domain_name)
        VALUES ('default', 'Default group', True, 'default')
        ON CONFLICT (name, domain_name) DO NOTHING
        RETURNING id;
    """)
    result = connection.execute(text(query)).first()
    gid = result.id if hasattr(result, "id") else None
    if gid is None:  # group already exists
        query = textwrap.dedent("""\
            SELECT id FROM groups where name = 'default' and domain_name = 'default';
        """)
        gid = connection.execute(text(query)).first().id

    # Fill in kernels' domain_name, group_id, and user_uuid.
    query = sa.select([kernels.c.id, kernels.c.access_key]).select_from(kernels)
    all_kernels = connection.execute(query).fetchall()
    for kernel in all_kernels:
        # Get kernel's keypair (access_key).
        query = (
            sa.select([keypairs.c.user])
            .select_from(keypairs)
            .where(keypairs.c.access_key == kernel["access_key"])
        )
        kp = connection.execute(query).first()
        # Update kernel information.
        query = """\
            UPDATE kernels SET domain_name = 'default', group_id = '%s', user_uuid = '%s'
            WHERE id = '%s';
        """ % (
            gid,
            kp.user,
            kernel["id"],
        )
        connection.execute(query)

    # Associate every users with the default group.
    # NOTE: this operation is not undoable unless you drop groups table.
    query = sa.select([users.c.uuid]).select_from(users)
    all_users = connection.execute(query).fetchall()
    for user in all_users:
        query = """\
            INSERT INTO association_groups_users (group_id, user_id)
            VALUES ('%s', '%s')
            ON CONFLICT (group_id, user_id) DO NOTHING;
        """ % (
            gid,
            user.uuid,
        )
        connection.execute(text(query))

    # Make kernel's new fields non-nullable.
    op.alter_column("kernels", column_name="domain_name", nullable=False)
    op.alter_column("kernels", column_name="group_id", nullable=False)
    op.alter_column("kernels", column_name="user_uuid", nullable=False)


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(op.f("fk_kernels_domain_name_domains"), "kernels", type_="foreignkey")
    op.drop_constraint(op.f("fk_kernels_user_uuid_users"), "kernels", type_="foreignkey")
    op.drop_constraint(op.f("fk_kernels_group_id_groups"), "kernels", type_="foreignkey")
    op.drop_column("kernels", "user_uuid")
    op.drop_column("kernels", "group_id")
    op.drop_column("kernels", "domain_name")
    # ### end Alembic commands ###
