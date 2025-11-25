"""
Service: RateLimitService
Responsável por rastrear e gerenciar eventos de rate limiting
Registra bloqueios, calcula estatísticas, monitora padrões
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging

from src.domain.rate_limit_tracker import RateLimitTracker, RateLimitStatistics
from src.domain.ticker_data import TickerModel, RateLimitEventModel
from src.infrastructure.database import get_database

logger = logging.getLogger(__name__)


class RateLimitService:
    """
    Serviço de rastreamento de rate limiting.
    Responsabilidades:
    - Registrar eventos de bloqueio
    - Calcular estatísticas agregadas
    - Monitorar padrões de bloqueio
    - Identificar tickers problemáticos
    """
    
    def __init__(self):
        self.db = get_database()
    
    def log_block_event(
        self,
        ticker: str,
        retry_count: int
    ) -> RateLimitTracker:
        """
        Registra um novo evento de bloqueio.
        
        Args:
            ticker: Símbolo do ticker
            retry_count: Número de tentativas até bloqueio
        
        Returns:
            RateLimitTracker: Objeto do evento
        """
        try:
            with self.db.get_db_transaction() as session:
                # Buscar ticker_id
                ticker_model = session.query(TickerModel).filter_by(symbol=ticker).first()
                if not ticker_model:
                    logger.warning(f"Ticker {ticker} não encontrado ao registrar bloqueio")
                    ticker_id = None
                else:
                    ticker_id = ticker_model.id
                
                # Criar evento de bloqueio
                now = datetime.utcnow()
                event = RateLimitEventModel(
                    ticker_id=ticker_id,
                    blocked_at=now,
                    retry_count=retry_count,
                    status='ACTIVE',
                    created_at=now
                )
                session.add(event)
                session.flush()
                
                tracker = RateLimitTracker(
                    ticker=ticker,
                    blocked_at=now,
                    retry_count=retry_count,
                    status='ACTIVE'
                )
                
                logger.warning(
                    f"⏸ Rate limit registrado: {ticker} "
                    f"(tentativa {retry_count})"
                )
                
                return tracker
        
        except Exception as e:
            logger.error(f"Erro ao registrar bloqueio: {e}")
            raise
    
    def log_fetch_attempt(
        self,
        ticker: str,
        success: bool,
        retry_count: int = 0,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Registra uma tentativa de fetch (sucesso ou falha).
        
        Args:
            ticker: Símbolo do ticker (ou "BATCH" para batch requests)
            success: Se a tentativa foi bem-sucedida
            retry_count: Número da tentativa
            error_message: Mensagem de erro, se houver
        
        Returns:
            bool: True se registrado com sucesso
        """
        try:
            with self.db.get_db_transaction() as session:
                # Buscar ticker_id (pode ser None para "BATCH")
                ticker_id = None
                if ticker != "BATCH":
                    ticker_model = session.query(TickerModel).filter_by(symbol=ticker).first()
                    if ticker_model:
                        ticker_id = ticker_model.id
                
                # Determinar status baseado no sucesso e mensagem de erro
                if success:
                    status = 'SUCCESS'
                elif error_message and ('429' in error_message or 'Too Many Requests' in error_message):
                    status = 'RATE_LIMITED'
                else:
                    status = 'FAILED'
                
                # Criar evento
                now = datetime.utcnow()
                event = RateLimitEventModel(
                    ticker_id=ticker_id,
                    blocked_at=now if status == 'RATE_LIMITED' else None,
                    retry_count=retry_count,
                    status=status,
                    created_at=now
                )
                session.add(event)
                
                if status == 'SUCCESS':
                    logger.debug(f"✓ Fetch attempt logged: {ticker} (retry {retry_count})")
                elif status == 'RATE_LIMITED':
                    logger.warning(f"⏸ Rate limit logged: {ticker} (retry {retry_count})")
                else:
                    logger.debug(f"✗ Failed fetch logged: {ticker} - {error_message}")
                
                return True
        
        except Exception as e:
            logger.error(f"Erro ao registrar tentativa: {e}")
            return False

    def log_resolution(
        self,
        event_id: int,
        resolved_at: Optional[datetime] = None
    ) -> bool:
        """
        Marca um bloqueio como resolvido.
        
        Args:
            event_id: ID do evento
            resolved_at: Quando foi resolvido (padrão: agora)
        
        Returns:
            bool: True se sucesso
        """
        try:
            if resolved_at is None:
                resolved_at = datetime.utcnow()
            
            with self.db.get_db_transaction() as session:
                event = session.query(RateLimitEventModel).filter_by(id=event_id).first()
                if not event:
                    logger.warning(f"Evento {event_id} não encontrado")
                    return False
                
                event.resolved_at = resolved_at
                event.status = 'RESOLVED'
                event.duration_seconds = int((resolved_at - event.blocked_at).total_seconds())
                
                logger.info(
                    f"✓ Bloqueio resolvido: {event.duration_seconds}s de duração"
                )
                
                return True
        
        except Exception as e:
            logger.error(f"Erro ao marcar resolução: {e}")
            return False
    
    def get_statistics(self, ticker: str) -> RateLimitStatistics:
        """
        Obtém estatísticas de bloqueio para um ticker.
        
        Args:
            ticker: Símbolo do ticker
        
        Returns:
            RateLimitStatistics: Objeto com estatísticas
        """
        try:
            with self.db.get_session() as session:
                ticker_model = session.query(TickerModel).filter_by(symbol=ticker).first()
                
                if not ticker_model:
                    stats = RateLimitStatistics(ticker=ticker)
                    return stats
                
                events = session.query(RateLimitEventModel).filter_by(
                    ticker_id=ticker_model.id
                ).all()
                
                total_blocks = len(events)
                total_duration = sum(
                    (e.duration_seconds or 0) for e in events if e.status == 'RESOLVED'
                )
                max_retries = max((e.retry_count for e in events), default=0)
                last_block = max(
                    (e.blocked_at for e in events), default=None
                )
                
                stats = RateLimitStatistics(
                    ticker=ticker,
                    total_blocks=total_blocks,
                    total_duration_seconds=total_duration,
                    last_block_at=last_block,
                    max_retries_in_block=max_retries
                )
                stats.calculate_averages()
                
                return stats
        
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return RateLimitStatistics(ticker=ticker)
    
    def get_active_blocks(self) -> List[RateLimitTracker]:
        """
        Retorna todos os bloqueios ativos.
        
        Returns:
            List de RateLimitTracker
        """
        try:
            with self.db.get_session() as session:
                events = session.query(RateLimitEventModel).filter_by(
                    status='ACTIVE'
                ).all()
                
                trackers = []
                for event in events:
                    ticker_model = session.query(TickerModel).filter_by(
                        id=event.ticker_id
                    ).first()
                    ticker_symbol = ticker_model.symbol if ticker_model else "UNKNOWN"
                    
                    tracker = RateLimitTracker(
                        ticker=ticker_symbol,
                        blocked_at=event.blocked_at,
                        retry_count=event.retry_count,
                        status=event.status
                    )
                    trackers.append(tracker)
                
                return trackers
        
        except Exception as e:
            logger.error(f"Erro ao obter bloqueios ativos: {e}")
            return []
    
    def is_ticker_blocked(self, ticker: str) -> bool:
        """
        Verifica se um ticker está atualmente bloqueado.
        
        Args:
            ticker: Símbolo do ticker
        
        Returns:
            bool: True se bloqueado
        """
        active = self.get_active_blocks()
        return any(t.ticker == ticker for t in active)
    
    def get_all_statistics(self) -> Dict[str, RateLimitStatistics]:
        """
        Obtém estatísticas de TODOS os tickers.
        
        Returns:
            Dicionário: {ticker: RateLimitStatistics}
        """
        try:
            with self.db.get_session() as session:
                tickers = session.query(TickerModel).all()
                
                stats_dict = {}
                for ticker_model in tickers:
                    stats = self.get_statistics(ticker_model.symbol)
                    if stats.total_blocks > 0:  # Apenas com bloqueios
                        stats_dict[ticker_model.symbol] = stats
                
                return stats_dict
        
        except Exception as e:
            logger.error(f"Erro ao obter todas as estatísticas: {e}")
            return {}
