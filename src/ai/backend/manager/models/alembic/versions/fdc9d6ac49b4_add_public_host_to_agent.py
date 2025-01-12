"""add_public_host_to_agent

Revision ID: fdc9d6ac49b4
Revises: fe59ec332c07
Create Date: 2023-04-25 17:36:01.666605

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "fdc9d6ac49b4"
down_revision = "fe59ec332c07"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("agents", sa.Column("public_host", sa.String(length=256), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("agents", "public_host")
    # ### end Alembic commands ###
