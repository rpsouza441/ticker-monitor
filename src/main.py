"""
main.py - Entry point da aplicação
Pode ser usado para testes, inicialização manual, ou API Flask
"""

import sys
import logging
from datetime import datetime, timedelta

from src.config import settings
from src.infrastructure.database import get_database
from src.infrastructure.queue_manager import QueueManager
from src.infrastructure.logger import setup_logging, get_logger
from src.domain.job_message import JobMessage

logger = get_logger(__name__)


def init_system() -> bool:
    """
    Inicializa sistema (BD + RabbitMQ).
    
    Returns:
        bool: True se sucesso
    """
    logger.info("Inicializando sistema...")
    
    # Inicializar BD
    db = get_database()
    if not db.initialize():
        logger.error("Falha ao inicializar BD")
        return False
    
    logger.info("✓ BD conectado e migrations executadas")
    
    # Inicializar RabbitMQ
    qm = QueueManager()
    if not qm.connect():
        logger.error("Falha ao conectar RabbitMQ")
        return False
    
    logger.info("✓ RabbitMQ conectado")
    
    # Enfileirar primeiro job (se não existem jobs)
    _enqueue_initial_job(qm)
    
    qm.close()
    db.close()
    
    logger.info("✓ Sistema inicializado com sucesso")
    return True


def _enqueue_initial_job(qm: QueueManager):
    """Enfileira o primeiro job (agora)"""
    try:
        # Usar timezone local (BRT) ao invés de UTC naive
        import pytz
        tz = pytz.timezone(settings.TIMEZONE)
        now = datetime.now(tz)  # <- Timezone-aware!
        
        job = JobMessage(
            ticker_list=settings.tickers_list,
            execution_time=now,
            retry_count=0
        )
        
        if qm.produce_job(job):
            logger.info(f"✓ Job inicial enfileirado: {len(settings.tickers_list)} tickers")
        else:
            logger.warning("Falha ao enfileirar job inicial")
    
    except Exception as e:
        logger.error(f"Erro ao enfileirar job: {e}")


def health_check() -> dict:
    """
    Health check do sistema.
    
    Returns:
        dict com status de cada componente
    """
    status = {
        'timestamp': datetime.utcnow().isoformat(),
        'components': {
            'database': False,
            'rabbitmq': False,
            'yfinance': False,
        }
    }
    
    # Database
    try:
        db = get_database()
        status['components']['database'] = db.health_check()
    except Exception as e:
        logger.error(f"DB health check falhou: {e}")
    
    # RabbitMQ
    try:
        qm = QueueManager()
        if qm.connect():
            status['components']['rabbitmq'] = qm.health_check()
            qm.close()
    except Exception as e:
        logger.error(f"RabbitMQ health check falhou: {e}")
    
    # yfinance
    try:
        import yfinance as yf
        ticker = yf.Ticker('PETR4.SA')
        _ = ticker.info
        status['components']['yfinance'] = True
    except Exception as e:
        logger.error(f"yfinance health check falhou: {e}")
    
    status['healthy'] = all(status['components'].values())
    
    return status


def main():
    """Entry point da aplicação"""
    setup_logging()
    
    logger.info(f"Ticker Monitor v1.0")
    logger.info(f"Configurações:")
    logger.info(f"  - Horário execução: {settings.EXECUTION_TIME}")
    logger.info(f"  - Tickers: {len(settings.tickers_list)}")
    logger.info(f"  - Tickers por requisição: {settings.TICKERS_PER_REQUEST}")
    logger.info(f"  - Retry máximo: {settings.RABBITMQ_MAX_RETRIES}")
    
    # Inicializar
    if not init_system():
        logger.error("Falha na inicialização")
        sys.exit(1)
    
    # Rodar consumer
    logger.info("Iniciando consumer...")
    from src.scheduler.consumer import Consumer
    
    consumer = Consumer()
    consumer.run()


if __name__ == '__main__':
    main()
