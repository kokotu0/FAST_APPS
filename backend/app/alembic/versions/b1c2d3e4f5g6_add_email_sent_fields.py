"""add email sent fields to form publish

Revision ID: b1c2d3e4f5g6
Revises: a709f6aea024
Create Date: 2025-11-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5g6'
down_revision = '26a64d83f39e'
branch_labels = None
depends_on = None


def upgrade():
    # FormPublishTable에 이메일 전송 관련 필드 추가
    op.add_column('formpublishtable', sa.Column('is_email_sent', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('formpublishtable', sa.Column('email_sent_at', sa.DateTime(), nullable=True))
    op.add_column('formpublishtable', sa.Column('email_sent_count', sa.Integer(), nullable=True, server_default='0'))
    
    # 기존 데이터 업데이트 (null을 false/0으로)
    op.execute("UPDATE formpublishtable SET is_email_sent = false WHERE is_email_sent IS NULL")
    op.execute("UPDATE formpublishtable SET email_sent_count = 0 WHERE email_sent_count IS NULL")


def downgrade():
    op.drop_column('formpublishtable', 'email_sent_count')
    op.drop_column('formpublishtable', 'email_sent_at')
    op.drop_column('formpublishtable', 'is_email_sent')

