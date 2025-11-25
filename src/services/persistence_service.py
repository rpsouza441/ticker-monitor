"""
Service: PersistenceService
Responsável por persistir TickerData em PostgreSQL
Transações ACID, múltiplas tabelas, sem duplicatas
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from datetime import datetime
from typing import List, Tuple
import logging

from src.domain.ticker_data import (
    TickerData,
    TickerModel,
    TickerPriceModel,
    TickerFundamentalModel,
    TickerHistoryModel,
)
from src.infrastructure.database import get_database

logger = logging.getLogger(__name__)


class PersistenceService:
    """
    Serviço de persistência: salva TickerData em BD com transações.
    Responsabilidades:
    - Inserir/atualizar master de tickers
    - Salvar preços (ticker_prices)
    - Salvar fundamentalistas (ticker_fundamentals)
    - Salvar histórico OHLCV (ticker_history)
    - Garantir ACID
    """
    
    def __init__(self):
        self.db = get_database()
    
    def save_ticker_data(self, ticker_data: TickerData) -> bool:
        """
        Salva um ticker completo em transação ACID.
        
        Args:
            ticker_data: Objeto TickerData com dados completos
        
        Returns:
            bool: True se sucesso
        """
        try:
            with self.db.get_db_transaction() as session:
                # 1. Buscar ou criar ticker no master
                ticker = self._ensure_ticker_exists(session, ticker_data)
                
                # 2. Salvar preço atual
                self._save_price(session, ticker.id, ticker_data)
                
                # 3. Salvar fundamentalistas (se disponível)
                if any([
                    ticker_data.pe_ratio,
                    ticker_data.eps,
                    ticker_data.dividend_yield,
                    ticker_data.market_cap
                ]):
                    self._save_fundamentals(session, ticker.id, ticker_data)
                
                # 4. Salvar histórico OHLCV (se disponível)
                if not ticker_data.history_ohlcv.empty:
                    self._save_history(session, ticker.id, ticker_data)
                
                logger.info(f"✓ Ticker {ticker_data.ticker} salvo com sucesso")
                return True
        
        except SQLAlchemyError as e:
            logger.error(f"✗ Erro ao salvar {ticker_data.ticker}: {e}")
            return False
    
    def save_all(self, ticker_data_list: List[TickerData]) -> Tuple[int, List[str]]:
        """
        Salva múltiplos tickers.
        
        Args:
            ticker_data_list: Lista de TickerData
        
        Returns:
            Tupla: (quantidade salva, lista de que falharam)
        """
        saved_count = 0
        failed_tickers = []
        
        for ticker_data in ticker_data_list:
            if self.save_ticker_data(ticker_data):
                saved_count += 1
            else:
                failed_tickers.append(ticker_data.ticker)
        
        logger.info(
            f"Batch completo: {saved_count} salvos, "
            f"{len(failed_tickers)} falharam"
        )
        
        return saved_count, failed_tickers
    
    def _ensure_ticker_exists(self, session: Session, ticker_data: TickerData) -> TickerModel:
        """
        Busca ticker no master ou cria novo.
        
        Args:
            session: SQLAlchemy session
            ticker_data: Dados do ticker
        
        Returns:
            TickerModel: Objeto do BD
        """
        ticker = session.query(TickerModel).filter_by(
            symbol=ticker_data.ticker
        ).first()
        
        if not ticker:
            ticker = TickerModel(
                symbol=ticker_data.ticker,
                asset_type=ticker_data.asset_type,
                currency=ticker_data.currency,
                created_at=datetime.utcnow()
            )
            session.add(ticker)
            session.flush()  # Gera ID
            logger.debug(f"Novo ticker criado: {ticker_data.ticker}")
        else:
            logger.debug(f"Ticker já existe: {ticker_data.ticker}")
        
        return ticker
    
    def _save_price(self, session: Session, ticker_id: int, ticker_data: TickerData):
        """Salva preço em ticker_prices"""
        price = TickerPriceModel(
            ticker_id=ticker_id,
            price=ticker_data.last_price,
            volume=ticker_data.volume,
            updated_at=ticker_data.last_updated,
            created_at=datetime.utcnow()
        )
        session.add(price)
        logger.debug(f"Preço salvo: {ticker_data.ticker} = {ticker_data.last_price}")
    
    def _save_fundamentals(self, session: Session, ticker_id: int, ticker_data: TickerData):
        """Salva dados fundamentalistas"""
        fundamental = TickerFundamentalModel(
            ticker_id=ticker_id,
            pe_ratio=ticker_data.pe_ratio,
            eps=ticker_data.eps,
            dividend_yield=ticker_data.dividend_yield,
            market_cap=ticker_data.market_cap,
            collected_at=ticker_data.last_updated,
            created_at=datetime.utcnow()
        )
        session.add(fundamental)
        logger.debug(f"Fundamentalistas salvos: {ticker_data.ticker}")
    
    def _save_history(self, session: Session, ticker_id: int, ticker_data: TickerData):
        """Salva histórico OHLCV (ignora duplicatas por data)"""
        for date, row in ticker_data.history_ohlcv.iterrows():
            try:
                history = TickerHistoryModel(
                    ticker_id=ticker_id,
                    date=pd.Timestamp(date).date(),
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=int(row['Volume']),
                    created_at=datetime.utcnow()
                )
                session.merge(history)  # Atualiza se existir, insere se não
            except (ValueError, KeyError) as e:
                logger.debug(f"Erro ao salvar histórico {date}: {e}")
                continue
        
        logger.debug(f"Histórico salvo: {len(ticker_data.history_ohlcv)} dias")
    
    def get_ticker_by_symbol(self, symbol: str) -> TickerModel:
        """Buscar ticker por símbolo"""
        with self.db.get_session() as session:
            return session.query(TickerModel).filter_by(symbol=symbol).first()
    
    def get_latest_price(self, ticker_symbol: str) -> float:
        """Obter preço mais recente"""
        with self.db.get_session() as session:
            ticker = session.query(TickerModel).filter_by(symbol=ticker_symbol).first()
            if not ticker:
                return None
            
            price_record = session.query(TickerPriceModel).filter_by(
                ticker_id=ticker.id
            ).order_by(TickerPriceModel.updated_at.desc()).first()
            
            return price_record.price if price_record else None


import pandas as pd
