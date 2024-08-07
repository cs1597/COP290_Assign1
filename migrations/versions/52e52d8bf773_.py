"""empty message

Revision ID: 52e52d8bf773
Revises: 4d774d812bb5
Create Date: 2024-01-31 23:55:58.545337

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '52e52d8bf773'
down_revision = '4d774d812bb5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('balance', sa.Integer(), nullable=True))
        batch_op.drop_column('watchlist')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('watchlist', sa.TEXT(), server_default=sa.text("'[]'"), nullable=True))
        batch_op.drop_column('balance')

    # ### end Alembic commands ###
