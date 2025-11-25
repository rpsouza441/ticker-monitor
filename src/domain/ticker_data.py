"""
Modelos de Domínio: Entidades do sistema
"""

from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger, ForeignKey, Index
from sqlalchemy.orm import declarative_base
from datetime import datetime
from typing import Optional, Dict, Any
import pandas as pd

Base = declarative_base()


# ════════════════════════════════════════════════════════════════
# MODELOS PYDANTIC (Serialização/API)
# ════════════════════════════════════════════════════════════════

class TickerDataSchema(BaseModel):
    """Schema Pydantic para TickerData - usado em APIs e serialização"""
    
    ticker: str
    last_price: float
    volume: int
    currency: str
    asset_type: str  # EQUITY, ETF, MUTUALFUND, CRYPTOCURRENCY
    last_updated: datetime
    
    # Fundamentalistas (opcionais)
    pe_ratio: Optional[float] = None
    eps: Optional[float] = None
    dividend_yield: Optional[float] = None
    market_cap: Optional[int] = None
    
    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════════
# MODELOS SQLALCHEMY (Persistência)
# ════════════════════════════════════════════════════════════════

class TickerModel(Base):
    """Master de tickers"""
    __tablename__ = "tickers"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    asset_type = Column(String(50), nullable=True)  # EQUITY, ETF, etc
    currency = Column(String(3), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TickerPriceModel(Base):
    """Preços atualizados"""
    __tablename__ = "ticker_prices"
    __table_args__ = (
        Index('ix_ticker_id_updated', 'ticker_id', 'updated_at', unique=False),
    )
    
    id = Column(Integer, primary_key=True)
    ticker_id = Column(Integer, ForeignKey('tickers.id'), nullable=False)
    price = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TickerFundamentalModel(Base):
    """Dados fundamentalistas"""
    __tablename__ = "ticker_fundamentals"
    __table_args__ = (
        Index('ix_ticker_id_collected', 'ticker_id', 'collected_at', unique=False),
    )
    
    id = Column(Integer, primary_key=True)
    ticker_id = Column(Integer, ForeignKey('tickers.id'), nullable=False)
    pe_ratio = Column(Float, nullable=True)
    eps = Column(Float, nullable=True)
    dividend_yield = Column(Float, nullable=True)
    market_cap = Column(BigInteger, nullable=True)
    collected_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TickerHistoryModel(Base):
    """Histórico OHLCV"""
    __tablename__ = "ticker_history"
    __table_args__ = (
        Index('ix_ticker_id_date', 'ticker_id', 'date', unique=True),
    )
    
    id = Column(Integer, primary_key=True)
    ticker_id = Column(Integer, ForeignKey('tickers.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class RateLimitEventModel(Base):
    """Rastreamento de bloqueios (Rate Limiting)"""
    __tablename__ = "rate_limit_events"
    __table_args__ = (
        Index('ix_ticker_id_blocked', 'ticker_id', 'blocked_at', unique=False),
    )
    
    id = Column(Integer, primary_key=True)
    ticker_id = Column(Integer, ForeignKey('tickers.id'), nullable=True)
    blocked_at = Column(DateTime, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    retry_count = Column(Integer, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)  # ACTIVE, RESOLVED
    created_at = Column(DateTime, default=datetime.utcnow)


class JobQueueModel(Base):
    """Fila de jobs para processamento"""
    __tablename__ = "job_queue"
    __table_args__ = (
        Index('ix_execution_time_status', 'execution_time', 'status', unique=False),
    )
    
    id = Column(Integer, primary_key=True)
    ticker_ids = Column(String, nullable=False)  # JSON array como string
    execution_time = Column(DateTime, nullable=False)
    retry_count = Column(Integer, default=0)
    status = Column(String(20), default='PENDING')  # PENDING, PROCESSING, COMPLETED, FAILED
    last_attempted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ════════════════════════════════════════════════════════════════
# CLASSE DE DOMÍNIO (Lógica de negócio)
# ════════════════════════════════════════════════════════════════

class TickerData:
    """
    Objeto de domínio para TickerData.
    Encapsula dados completos de um ticker com validações.
    """
    
    def __init__(
        self,
        ticker: str,
        last_price: float,
        volume: int,
        currency: str,
        asset_type: str,
        last_updated: datetime,
        pe_ratio: Optional[float] = None,
        eps: Optional[float] = None,
        dividend_yield: Optional[float] = None,
        market_cap: Optional[int] = None,
        history_ohlcv: Optional[pd.DataFrame] = None
    ):
        self.ticker = ticker
        self.last_price = last_price
        self.volume = volume
        self.currency = currency
        self.asset_type = asset_type
        self.last_updated = last_updated
        
        # Fundamentalistas
        self.pe_ratio = pe_ratio
        self.eps = eps
        self.dividend_yield = dividend_yield
        self.market_cap = market_cap
        
        # Histórico
        self.history_ohlcv = history_ohlcv or pd.DataFrame()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'ticker': self.ticker,
            'last_price': self.last_price,
            'volume': self.volume,
            'currency': self.currency,
            'asset_type': self.asset_type,
            'last_updated': self.last_updated.isoformat(),
            'pe_ratio': self.pe_ratio,
            'eps': self.eps,
            'dividend_yield': self.dividend_yield,
            'market_cap': self.market_cap,
        }
    
    def to_schema(self) -> TickerDataSchema:
        """Converte para Pydantic Schema"""
        return TickerDataSchema(
            ticker=self.ticker,
            last_price=self.last_price,
            volume=self.volume,
            currency=self.currency,
            asset_type=self.asset_type,
            last_updated=self.last_updated,
            pe_ratio=self.pe_ratio,
            eps=self.eps,
            dividend_yield=self.dividend_yield,
            market_cap=self.market_cap,
        )
    
    def __repr__(self) -> str:
        return (
            f"TickerData(ticker={self.ticker}, price={self.last_price}, "
            f"volume={self.volume}, currency={self.currency})"
        )
