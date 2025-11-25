"""
Modelo de Domínio: Rate Limit Tracker
Rastreamento separado de bloqueios e eventos de rate limiting
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Index
from sqlalchemy.orm import declarative_base
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

Base = declarative_base()


class RateLimitTracker:
    """
    Objeto de domínio para rastreamento de rate limiting.
    Responsável apenas por gerenciar bloqueios de acesso.
    Separado de TickerData por responsabilidade única.
    """
    
    def __init__(
        self,
        ticker: str,
        blocked_at: datetime,
        retry_count: int,
        duration_seconds: Optional[int] = None,
        resolved_at: Optional[datetime] = None,
        status: str = "ACTIVE"
    ):
        self.ticker = ticker
        self.blocked_at = blocked_at
        self.retry_count = retry_count
        self.duration_seconds = duration_seconds
        self.resolved_at = resolved_at
        self.status = status  # ACTIVE ou RESOLVED
    
    def is_resolved(self) -> bool:
        """Verifica se o bloqueio foi resolvido"""
        return self.status == "RESOLVED" and self.resolved_at is not None
    
    def resolve(self, resolved_at: datetime):
        """Marca bloqueio como resolvido e calcula duração"""
        self.status = "RESOLVED"
        self.resolved_at = resolved_at
        self.duration_seconds = int((resolved_at - self.blocked_at).total_seconds())
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'ticker': self.ticker,
            'blocked_at': self.blocked_at.isoformat(),
            'retry_count': self.retry_count,
            'duration_seconds': self.duration_seconds,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'status': self.status,
        }
    
    def __repr__(self) -> str:
        return (
            f"RateLimitTracker(ticker={self.ticker}, "
            f"blocked_at={self.blocked_at}, status={self.status}, "
            f"duration={self.duration_seconds}s)"
        )


@dataclass
class RateLimitStatistics:
    """Estatísticas agregadas de rate limiting"""
    
    ticker: str
    total_blocks: int = 0
    total_duration_seconds: float = 0.0
    average_duration_seconds: float = 0.0
    last_block_at: Optional[datetime] = None
    max_retries_in_block: int = 0
    
    def calculate_averages(self):
        """Recalcula médias"""
        if self.total_blocks > 0:
            self.average_duration_seconds = self.total_duration_seconds / self.total_blocks
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'ticker': self.ticker,
            'total_blocks': self.total_blocks,
            'total_duration_seconds': self.total_duration_seconds,
            'average_duration_seconds': self.average_duration_seconds,
            'last_block_at': self.last_block_at.isoformat() if self.last_block_at else None,
            'max_retries_in_block': self.max_retries_in_block,
        }
