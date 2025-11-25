"""
config.py - Configurações com Pydantic

Carrega variáveis de .env e docker-compose environment
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
import pytz

class Settings(BaseSettings):
    """
    Configurações da aplicação.
    
    Carrega variáveis de:
    1. .env (arquivo local)
    2. Variáveis de ambiente do SO/Docker
    """
    
    # ═══════════════════════════════════════════════════════════
    # EXECUÇÃO E SCHEDULER
    # ═══════════════════════════════════════════════════════════
    
    EXECUTION_TIME: str = "16:30"
    """Horário de execução diária (HH:MM) - segunda a sexta"""
    
    TICKERS_PER_REQUEST: int = 10
    """Quantidade de tickers por requisição yfinance"""
    
    REQUEST_DELAY_MS: int = 300
    """Delay entre requisições em milisegundos"""
    
    MONITORED_TICKERS: str = "PETR4.SA,VALE3.SA,WEGE3.SA"
    """Lista de tickers a monitorar (separados por vírgula)"""
    
    TIMEZONE: str = "America/Sao_Paulo"
    """Fuso horário para scheduler"""
    
    # ═══════════════════════════════════════════════════════════
    # DATABASE
    # ═══════════════════════════════════════════════════════════
    
    DATABASE_URL: str = "postgresql://ticker_user:ticker_pass@localhost:5432/ticker_db"
    """URL de conexão PostgreSQL"""
    
    DB_ECHO: bool = False
    """Echo de SQL queries (debug)"""
    
    DB_POOL_SIZE: int = 10
    """Tamanho do connection pool"""
    
    DB_MAX_OVERFLOW: int = 20
    """Overflow do pool"""
    
    # ═══════════════════════════════════════════════════════════
    # RABBITMQ
    # ═══════════════════════════════════════════════════════════
    
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    """URL de conexão RabbitMQ"""
    
    RABBITMQ_QUEUE: str = "ticker_updates"
    """Nome da fila principal"""
    
    RABBITMQ_DLQ: str = "ticker_updates_dlq"
    """Nome da dead letter queue"""
    
    RABBITMQ_MAX_RETRIES: int = 10
    """Máximo de tentativas antes de DLQ"""
    
    # ═══════════════════════════════════════════════════════════
    # RATE LIMITING
    # ═══════════════════════════════════════════════════════════
    
    BACKOFF_BASE: int = 2
    """Base para exponencial backoff (2^n segundos)"""
    
    BACKOFF_MAX_SECONDS: int = 3600
    """Máximo de espera em backoff"""
    
    # ═══════════════════════════════════════════════════════════
    # LOGGING
    # ═══════════════════════════════════════════════════════════
    
    LOG_LEVEL: str = "INFO"
    """Nível de log: DEBUG, INFO, WARNING, ERROR"""
    
    LOG_FORMAT: str = "json"
    """Formato: json ou texto"""
    
    LOG_FILE: Optional[str] = None
    """Arquivo de log (None = stdout)"""
    
    # ═══════════════════════════════════════════════════════════
    # PYDANTIC CONFIG
    # ═══════════════════════════════════════════════════════════
    
    model_config = ConfigDict(
        extra='allow',  # ✅ PERMITE variáveis extras (docker-compose)
        env_file='.env',
        case_sensitive=True
    )
    
    # ═══════════════════════════════════════════════════════════
    # PROPRIEDADES CALCULADAS
    # ═══════════════════════════════════════════════════════════
    
    @property
    def tz(self):
        """Retorna timezone object"""
        return pytz.timezone(self.TIMEZONE)
    
    @property
    def tickers_list(self) -> list:
        """Retorna lista de tickers"""
        return [t.strip() for t in self.MONITORED_TICKERS.split(',') if t.strip()]
    
    def __repr__(self):
        return (
            f"Settings("
            f"execution_time={self.EXECUTION_TIME}, "
            f"tickers={len(self.tickers_list)}, "
            f"database={self.DATABASE_URL.split('@')[1] if '@' in self.DATABASE_URL else '?'}"
            f")"
        )


# ═══════════════════════════════════════════════════════════
# INSTÂNCIA GLOBAL
# ═══════════════════════════════════════════════════════════

try:
    settings = Settings()
except Exception as e:
    print(f"❌ Erro ao carregar Settings: {e}")
    raise
