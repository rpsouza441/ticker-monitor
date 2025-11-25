"""
Primeira Migration: Criar tabelas iniciais
Equivalente ao V001__init.sql no Flyway

Auto-gerada pelo Alembic (alembic revision --autogenerate -m "initial")
"""

from alembic import op
import sqlalchemy as sa


# Identificador único da migration
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fazer upgrade (CREATE TABLE)"""
    
    # Criar tabela: tickers (master)
    op.create_table(
        'tickers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('asset_type', sa.String(length=50), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol')
    )
    op.create_index('ix_tickers_symbol', 'tickers', ['symbol'], unique=False)
    
    # Criar tabela: ticker_prices
    op.create_table(
        'ticker_prices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker_id', sa.Integer(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('volume', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ticker_id'], ['tickers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ticker_prices_ticker_updated', 'ticker_prices', 
                   ['ticker_id', 'updated_at'], unique=False)
    
    # Criar tabela: ticker_fundamentals
    op.create_table(
        'ticker_fundamentals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker_id', sa.Integer(), nullable=False),
        sa.Column('pe_ratio', sa.Float(), nullable=True),
        sa.Column('eps', sa.Float(), nullable=True),
        sa.Column('dividend_yield', sa.Float(), nullable=True),
        sa.Column('market_cap', sa.BigInteger(), nullable=True),
        sa.Column('collected_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ticker_id'], ['tickers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ticker_fundamentals_ticker_collected', 'ticker_fundamentals',
                   ['ticker_id', 'collected_at'], unique=False)
    
    # Criar tabela: ticker_history (OHLCV)
    op.create_table(
        'ticker_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('open', sa.Float(), nullable=False),
        sa.Column('high', sa.Float(), nullable=False),
        sa.Column('low', sa.Float(), nullable=False),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('volume', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ticker_id'], ['tickers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker_id', 'date')
    )
    op.create_index('ix_ticker_history_ticker_date', 'ticker_history',
                   ['ticker_id', 'date'], unique=False)
    
    # Criar tabela: rate_limit_events
    op.create_table(
        'rate_limit_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker_id', sa.Integer(), nullable=True),
        sa.Column('blocked_at', sa.DateTime(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ticker_id'], ['tickers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_rate_limit_ticker_blocked', 'rate_limit_events',
                   ['ticker_id', 'blocked_at'], unique=False)
    op.create_index('ix_rate_limit_status', 'rate_limit_events',
                   ['status', 'blocked_at'], unique=False)
    
    # Criar tabela: job_queue
    op.create_table(
        'job_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker_ids', sa.String(), nullable=False),
        sa.Column('execution_time', sa.DateTime(), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('last_attempted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_job_queue_execution_status', 'job_queue',
                   ['execution_time', 'status'], unique=False)
    op.create_index('ix_job_queue_status', 'job_queue',
                   ['status', 'created_at'], unique=False)


def downgrade() -> None:
    """Fazer downgrade (DROP TABLE) - rollback automático"""
    
    # Remover índices
    op.drop_index('ix_job_queue_status', table_name='job_queue')
    op.drop_index('ix_job_queue_execution_status', table_name='job_queue')
    op.drop_index('ix_rate_limit_status', table_name='rate_limit_events')
    op.drop_index('ix_rate_limit_ticker_blocked', table_name='rate_limit_events')
    op.drop_index('ix_ticker_history_ticker_date', table_name='ticker_history')
    op.drop_index('ix_ticker_fundamentals_ticker_collected', table_name='ticker_fundamentals')
    op.drop_index('ix_ticker_prices_ticker_updated', table_name='ticker_prices')
    op.drop_index('ix_tickers_symbol', table_name='tickers')
    
    # Remover tabelas (ordem reversa de dependências)
    op.drop_table('job_queue')
    op.drop_table('rate_limit_events')
    op.drop_table('ticker_history')
    op.drop_table('ticker_fundamentals')
    op.drop_table('ticker_prices')
    op.drop_table('tickers')
