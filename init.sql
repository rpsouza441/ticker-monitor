-- init.sql: Schema inicial do PostgreSQL
-- Executado automaticamente no primeiro startup

-- ════════════════════════════════════════════════════════════════
-- Tabela Master de Tickers
-- ════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS tickers (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    asset_type VARCHAR(50),
    currency VARCHAR(3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_tickers_symbol ON tickers(symbol);


-- ════════════════════════════════════════════════════════════════
-- Preços Atualizados
-- ════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS ticker_prices (
    id SERIAL PRIMARY KEY,
    ticker_id INT NOT NULL REFERENCES tickers(id) ON DELETE CASCADE,
    price DECIMAL(12, 4) NOT NULL,
    volume BIGINT,
    updated_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_ticker_prices_ticker_updated 
    ON ticker_prices(ticker_id, updated_at DESC);


-- ════════════════════════════════════════════════════════════════
-- Dados Fundamentalistas
-- ════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS ticker_fundamentals (
    id SERIAL PRIMARY KEY,
    ticker_id INT NOT NULL REFERENCES tickers(id) ON DELETE CASCADE,
    pe_ratio DECIMAL(10, 2),
    eps DECIMAL(10, 4),
    dividend_yield DECIMAL(10, 4),
    market_cap BIGINT,
    collected_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_ticker_fundamentals_ticker_collected 
    ON ticker_fundamentals(ticker_id, collected_at DESC);


-- ════════════════════════════════════════════════════════════════
-- Histórico OHLCV
-- ════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS ticker_history (
    id SERIAL PRIMARY KEY,
    ticker_id INT NOT NULL REFERENCES tickers(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    open DECIMAL(12, 4),
    high DECIMAL(12, 4),
    low DECIMAL(12, 4),
    close DECIMAL(12, 4),
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker_id, date)
);

CREATE INDEX IF NOT EXISTS ix_ticker_history_ticker_date 
    ON ticker_history(ticker_id, date DESC);


-- ════════════════════════════════════════════════════════════════
-- Rate Limit Events (Rastreamento de Bloqueios)
-- ════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS rate_limit_events (
    id SERIAL PRIMARY KEY,
    ticker_id INT REFERENCES tickers(id) ON DELETE CASCADE,
    blocked_at TIMESTAMP NOT NULL,
    duration_seconds INT,
    retry_count INT NOT NULL,
    resolved_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_rate_limit_ticker_blocked 
    ON rate_limit_events(ticker_id, blocked_at DESC);

CREATE INDEX IF NOT EXISTS ix_rate_limit_status 
    ON rate_limit_events(status, blocked_at DESC);


-- ════════════════════════════════════════════════════════════════
-- Fila de Jobs
-- ════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS job_queue (
    id SERIAL PRIMARY KEY,
    ticker_ids TEXT NOT NULL,  -- JSON array como string
    execution_time TIMESTAMP NOT NULL,
    retry_count INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'PENDING',
    last_attempted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_job_queue_execution_status 
    ON job_queue(execution_time, status);

CREATE INDEX IF NOT EXISTS ix_job_queue_status 
    ON job_queue(status, created_at DESC);


-- ════════════════════════════════════════════════════════════════
-- View: Estatísticas de Rate Limiting por Ticker
-- ════════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW rate_limit_statistics AS
SELECT 
    t.symbol as ticker,
    COUNT(*) as total_blocks,
    COUNT(CASE WHEN rle.status = 'RESOLVED' THEN 1 END) as resolved_blocks,
    COUNT(CASE WHEN rle.status = 'ACTIVE' THEN 1 END) as active_blocks,
    ROUND(AVG(rle.duration_seconds)::numeric, 2) as avg_block_duration_seconds,
    MAX(rle.duration_seconds) as max_block_duration_seconds,
    MAX(rle.blocked_at) as last_block_at,
    MAX(rle.retry_count) as max_retries_in_block
FROM tickers t
LEFT JOIN rate_limit_events rle ON t.id = rle.ticker_id
GROUP BY t.id, t.symbol
ORDER BY total_blocks DESC;


-- ════════════════════════════════════════════════════════════════
-- View: Últimos Preços por Ticker
-- ════════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW latest_ticker_prices AS
SELECT DISTINCT ON (tp.ticker_id)
    t.symbol as ticker,
    tp.price,
    tp.volume,
    tp.updated_at,
    t.currency
FROM ticker_prices tp
JOIN tickers t ON tp.ticker_id = t.id
ORDER BY tp.ticker_id, tp.updated_at DESC;
