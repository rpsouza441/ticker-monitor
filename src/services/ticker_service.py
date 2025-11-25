"""
Service: TickerService
Responsável por buscar dados do yfinance e criar objetos TickerData
"""

import yfinance as yf
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import time
import logging
from urllib3.exceptions import ConnectTimeoutError, ReadTimeoutError
from requests.exceptions import RequestException

from src.domain.ticker_data import TickerData


logger = logging.getLogger(__name__)


class TickerService:
    """
    Serviço de busca de dados de tickers via yfinance.
    Implementa lógica de retry, tratamento de bloqueios e requisições em batch.
    """
    
    def __init__(
        self,
        batch_size: int = 10,
        delay_ms: int = 300,
        backoff_base: int = 2,
        max_retries: int = 10
    ):
        self.batch_size = batch_size
        self.delay_seconds = delay_ms / 1000.0
        self.backoff_base = backoff_base
        self.max_retries = max_retries
        
        # Integrar rate limit tracking
        from src.services.rate_limit_service import RateLimitService
        self.rate_limit_service = RateLimitService()
    
    def fetch_by_list(
        self,
        ticker_symbols: List[str],
        on_rate_limit: Optional[callable] = None
    ) -> Tuple[List[TickerData], List[str]]:
        """
        Busca dados de múltiplos tickers EM BATCH com retry e backoff exponencial.
        Usa yf.download() para buscar todos de uma vez (muito mais rápido).
        
        Args:
            ticker_symbols: Lista de tickers a buscar
            on_rate_limit: Callback para quando houver bloqueio (recebe ticker, retry_count)
        
        Returns:
            Tupla: (lista de TickerData bem-sucedidos, lista de tickers que falharam)
        """
        
        results = []
        failed_tickers = []
        
        # Dividir em batches
        batches = [
            ticker_symbols[i:i + self.batch_size]
            for i in range(0, len(ticker_symbols), self.batch_size)
        ]
        
        logger.info(f"Iniciando fetch de {len(ticker_symbols)} tickers em {len(batches)} batches")
        
        for batch_num, batch in enumerate(batches, 1):
            logger.info(f"Batch {batch_num}/{len(batches)}: {batch}")
            
            # Tentar buscar o batch inteiro com retry exponencial
            batch_data = self._fetch_batch_with_retry(batch)
            
            if batch_data is None:
                # Batch completo falhou após retries
                failed_tickers.extend(batch)
                logger.error(f"✗ Batch {batch_num} falhou completamente")
                continue
            
            # Processar cada ticker do batch
            for ticker in batch:
                try:
                    ticker_data = self._process_ticker_from_batch(ticker, batch_data)
                    
                    if ticker_data:
                        results.append(ticker_data)
                        logger.debug(f"✓ {ticker} processado com sucesso")
                    else:
                        failed_tickers.append(ticker)
                        logger.warning(f"✗ {ticker} retornou None")
                        
                except Exception as e:
                    logger.error(f"✗ Erro ao processar {ticker}: {e}")
                    failed_tickers.append(ticker)
            
            # Delay entre batches (não no último batch)
            if batch != batches[-1]:
                logger.info(f"Aguardando {self.delay_seconds}s entre batches...")
                time.sleep(self.delay_seconds)
        
        logger.info(
            f"Fetch completo: {len(results)} sucesso, "
            f"{len(failed_tickers)} falharam"
        )
        
        return results, failed_tickers
    
    def _fetch_batch_with_retry(self, tickers: List[str]) -> Optional[Dict]:
        """
        Busca um batch inteiro de tickers com yf.download() e retry exponencial.
        
        Args:
            tickers: Lista de símbolos dos tickers
        
        Returns:
            Dict com dados do yf.download() ou None se falhar completamente
        """
        MAX_RETRIES = 5  # 5 tentativas como solicitado
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug(f"Tentativa {attempt}/{MAX_RETRIES} para batch de {len(tickers)} tickers")
                
                # Buscar dados em BATCH (todos de uma vez!)
                data = yf.download(
                    tickers,
                    period='1d',
                    interval='1d',
                    progress=False,
                    threads=False,
                    ignore_tz=False
                )
                
                # ═══════════════════════════════════════════════════════════
                # VALIDAÇÃO: Verificar se retornou conteúdo
                # ═══════════════════════════════════════════════════════════
                if data is None or data.empty:
                    logger.warning(f"⚠ Batch retornou vazio (tentativa {attempt})")
                    
                    if attempt < MAX_RETRIES:
                        backoff = self.backoff_base ** attempt
                        logger.info(f"Retry em {backoff}s...")
                        time.sleep(backoff)
                        continue
                    else:
                        logger.error(f"✗ Batch falhou: sem dados após {MAX_RETRIES} tentativas")
                        return None
                
                # Sucesso!
                logger.info(f"✓ Batch baixado com sucesso ({len(data)} registros)")
                
                # Registrar tentativa bem-sucedida
                logger.debug(f"[TRACKING] Chamando log_fetch_attempt (sucesso, attempt={attempt})")
                try:
                    self.rate_limit_service.log_fetch_attempt(
                        ticker="BATCH",
                        success=True,
                        retry_count=attempt
                    )
                    logger.debug(f"[TRACKING] log_fetch_attempt concluído com sucesso")
                except Exception as track_err:
                    logger.error(f"[TRACKING] Erro ao registrar tentativa: {track_err}")
                
                return data
                
            except Exception as e:
                error_msg = str(e)
                
                # Registrar tentativa com falha
                logger.debug(f"[TRACKING] Chamando log_fetch_attempt (falha, attempt={attempt}, erro={error_msg[:50]})")
                try:
                    self.rate_limit_service.log_fetch_attempt(
                        ticker="BATCH",
                        success=False,
                        retry_count=attempt,
                        error_message=error_msg
                    )
                    logger.debug(f"[TRACKING] log_fetch_attempt de falha concluído")
                except Exception as track_err:
                    logger.error(f"[TRACKING] Erro ao registrar tentativa de falha: {track_err}")
                
                # Verificar se é rate limiting (429)
                if '429' in error_msg or 'Too Many Requests' in error_msg:
                    logger.warning(f"⚠ Rate limit detectado (tentativa {attempt})")
                    
                    if attempt < MAX_RETRIES:
                        backoff = (self.backoff_base ** attempt) * 2  # Backoff maior para rate limit
                        logger.info(f"Aguardando {backoff}s antes de retry...")
                        time.sleep(backoff)
                    else:
                        logger.error(f"✗ Batch bloqueado permanentemente após {MAX_RETRIES} tentativas")
                        return None
                else:
                    # Outros erros
                    logger.warning(f"⚠ Erro no batch (tentativa {attempt}): {e}")
                    
                    if attempt < MAX_RETRIES:
                        backoff = self.backoff_base ** attempt
                        time.sleep(backoff)
                    else:
                        logger.error(f"✗ Batch falhou permanentemente: {e}")
                        return None
        
        return None
    
    def _process_ticker_from_batch(self, ticker: str, batch_data) -> Optional[TickerData]:
        """
        Processa um ticker individual dos dados do batch.
        
        Args:
            ticker: Símbolo do ticker
            batch_data: DataFrame retornado pelo yf.download()
        
        Returns:
            TickerData ou None se falhar
        """
        try:
            # Buscar objeto Ticker para info adicional
            ticker_obj = yf.Ticker(ticker)
            
            # Extrair preço do batch_data
            try:
                if len(batch_data.columns.levels) > 1:
                    # Multi-ticker
                    close_price = batch_data['Close'][ticker].iloc[-1] if ticker in batch_data['Close'].columns else None
                else:
                    # Single ticker
                    close_price = batch_data['Close'].iloc[-1] if 'Close' in batch_data.columns else None
                
                if pd.isna(close_price) or close_price is None:
                    logger.warning(f"Impossível obter preço para {ticker}")
                    return None
                    
            except Exception as e:
                logger.error(f"Erro ao extrair preço de {ticker}: {e}")
                return None
            
            # Buscar volume, tipo de ativo e fundamentals
            try:
                volume = ticker_obj.info.get('volume', 0) if ticker_obj.info else 0
            except:
                volume = 0
            
            try:
                asset_type = ticker_obj.info.get('quoteType', 'EQUITY') if ticker_obj.info else 'EQUITY'
            except:
                asset_type = 'EQUITY'
            
            try:
                currency = ticker_obj.info.get('currency', 'BRL') if ticker_obj.info else 'BRL'
            except:
                currency = 'BRL'
            
            # Fundamentalistas (opcionais)
            fundamentals = self._fetch_fundamentals(ticker_obj)
            
            # Histórico já veio no batch_data
            history = batch_data if not batch_data.empty else pd.DataFrame()
            
            ticker_data = TickerData(
                ticker=ticker,
                last_price=float(close_price),
                volume=int(volume),
                currency=currency,
                asset_type=asset_type,
                last_updated=datetime.utcnow(),
                **fundamentals,
                history_ohlcv=history
            )
            
            return ticker_data
            
        except Exception as e:
            logger.error(f"Erro ao processar {ticker}: {e}")
            return None
    
    def _fetch_fundamentals(self, ticker_obj) -> Dict:
        """Busca dados fundamentalistas quando disponíveis"""
        fundamentals = {}
        
        try:
            info = ticker_obj.info
            fundamentals['pe_ratio'] = info.get('trailingPE') or info.get('forwardPE')
            fundamentals['eps'] = info.get('trailingEps') or info.get('epsTrailingTwelveMonths')
            fundamentals['dividend_yield'] = info.get('dividendYield')
            fundamentals['market_cap'] = info.get('marketCap')
        except Exception as e:
            logger.debug(f"Erro ao buscar fundamentalistas: {e}")
        
        return fundamentals
    
    def _fetch_history(self, ticker_obj, period: str = "10y") -> pd.DataFrame:
        """Busca histórico OHLCV"""
        try:
            history = ticker_obj.history(period=period)
            return history
        except Exception as e:
            logger.warning(f"Erro ao buscar histórico: {e}")
            return pd.DataFrame()
