"""
Database: Setup SQLAlchemy, Connection Management, Migrations com Alembic
Equivalente ao Flyway em Java, mas com auto-geração de migrations
"""

from sqlalchemy import create_engine, text, inspect, event
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations
import logging
from contextlib import contextmanager
from typing import Generator, Optional
from datetime import datetime

from src.config import settings
from src.domain.ticker_data import Base

logger = logging.getLogger(__name__)


class Database:
    """
    Gerenciador de banco de dados com Alembic migrations.
    Responsável por: conexão, session management, migrations, health checks.
    """
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.scoped_session = None
    
    def initialize(self) -> bool:
        """
        Inicializa engine e session factory.
        Cria tabelas se não existirem (primeira execução).
        
        Returns:
            bool: True se sucesso, False se erro
        """
        try:
            # Criar engine com pool de conexões
            self.engine = create_engine(
                settings.DATABASE_URL,
                poolclass=QueuePool,
                pool_size=10,              # Conexões ativas
                max_overflow=20,           # Conexões extras quando necessário
                pool_recycle=3600,         # Reciclar conexão a cada hora
                echo=settings.DB_ECHO,     # Log SQL se habilitado
                connect_args={
                    "connect_timeout": 10,
                    "keepalives": 1,
                    "keepalives_idle": 30,
                }
            )
            
            # Event listener para monitorar conexões
            @event.listens_for(self.engine, "connect")
            def receive_connect(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                logger.debug("✓ Nova conexão ao BD estabelecida")
            
            # Testar conexão
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("✓ Conexão ao PostgreSQL estabelecida")
            
            # Criar session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Scoped session para thread-safety
            self.scoped_session = scoped_session(self.SessionLocal)
            
            # Executar migrations
            if not self._run_migrations():
                logger.error("Erro ao executar migrations")
                return False
            
            logger.info("✓ Database inicializado com sucesso")
            return True
        
        except OperationalError as e:
            logger.error(f"✗ Erro ao conectar ao PostgreSQL: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Erro ao inicializar database: {e}")
            return False
    
    def _run_migrations(self) -> bool:
        """
        Executa migrations Alembic.
        Equivalente ao 'flyway migrate' em Java.
        
        Returns:
            bool: True se sucesso
        """
        try:
            # ═══════════════════════════════════════════════════════════
            # MIGRATIONS ALEMBIC - Controle de versão do banco
            # ═══════════════════════════════════════════════════════════
            logger.info("Executando migrations Alembic...")
            
            from alembic.command import upgrade, current
            from alembic.script import ScriptDirectory
            
            cfg = Config("alembic.ini")
            cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
            
            # Verificar versão atual
            with self.engine.begin() as connection:
                migration_context = MigrationContext.configure(connection)
                current_revision = migration_context.get_current_revision()
                logger.info(f"📌 Revisão atual do BD: {current_revision or 'Nenhuma'}")
                
                # Verificar revisão HEAD (mais recente disponível)
                script = ScriptDirectory.from_config(cfg)
                head_revision = script.get_current_head()
                logger.info(f"📌 Revisão HEAD (disponível): {head_revision}")
                
                # Se já está atualizado, pular upgrade
                if current_revision == head_revision:
                    logger.info("✓ BD já está na versão mais recente")
                    return True
            
            # Atualizar para a versão mais recente ('head')
            logger.info("🔄 Aplicando migrations pendentes...")
            try:
                upgrade(cfg, "head")
                logger.info("✓ Migrations executadas com sucesso")
                
                # Verificar nova versão
                with self.engine.begin() as connection:
                    migration_context = MigrationContext.configure(connection)
                    new_revision = migration_context.get_current_revision()
                    logger.info(f"📌 Nova revisão do BD: {new_revision}")
                
            except Exception as e:
                error_msg = str(e)
                if "Can't locate revision identified by" in error_msg:
                    logger.error("✗ ERRO: Tabela alembic_version existe mas está inconsistente")
                    logger.error("   Solução: DELETE FROM alembic_version; ou docker compose down -v")
                    return False
                elif "No such revision" in error_msg or "Can't locate" in error_msg:
                    logger.warning(f"⚠ Nenhuma migration encontrada: {error_msg}")
                else:
                    logger.error(f"✗ Erro ao executar migrations: {e}")
                    raise
            
            return True
        
        except Exception as e:
            logger.error(f"✗ Erro ao executar migrations: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager para obter uma session.
        Garante rollback automático em caso de erro.
        
        Uso:
            with db.get_session() as session:
                result = session.query(TickerModel).first()
        
        Yields:
            Session: SQLAlchemy session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"✗ Erro em transação BD: {e}")
            raise
        finally:
            session.close()
    
    @contextmanager
    def get_db_transaction(self) -> Generator[Session, None, None]:
        """
        Context manager para transação explícita.
        Mais seguro que get_session para operações críticas.
        
        Uso:
            with db.get_db_transaction() as session:
                session.add(ticker)
                session.add(price)
                # Commit automático ao sair sem erro
        
        Yields:
            Session: SQLAlchemy session
        """
        session = self.SessionLocal()
        try:
            with session.begin():
                yield session
            logger.debug("✓ Transação confirmada")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"✗ Transação falhou: {e}")
            raise
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """
        Verifica saúde da conexão ao BD.
        Usado no health endpoint do Docker.
        
        Returns:
            bool: True se BD está OK
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.debug("✓ Health check BD: OK")
                return True
        except Exception as e:
            logger.error(f"✗ Health check BD falhou: {e}")
            return False
    
    def get_connection_info(self) -> dict:
        """
        Retorna informações sobre conexão e pool.
        Útil para monitoramento.
        """
        try:
            pool = self.engine.pool
            return {
                'pool_size': pool.size(),
                'pool_checked_out': pool.checkedout(),
                'pool_checked_in': len(pool._queue.queue) if hasattr(pool, '_queue') else 0,
                'engine_echo': self.engine.echo,
                'database_url': settings.DATABASE_URL.replace(
                    settings.DATABASE_URL.split('@')[0].split('://')[1],
                    '***:***'  # Ocultar credenciais
                ),
            }
        except Exception as e:
            logger.error(f"Erro ao obter info de conexão: {e}")
            return {}
    
    def execute_raw_sql(self, sql: str, params: dict = None) -> list:
        """
        Executa SQL raw (cuidado com SQL injection).
        Apenas para queries complexas não suportadas pelo ORM.
        
        Args:
            sql: Query SQL
            params: Parâmetros (usar :param_name)
        
        Returns:
            list: Resultados
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                return result.fetchall()
        except SQLAlchemyError as e:
            logger.error(f"✗ Erro ao executar SQL raw: {e}")
            return []
    
    def close(self):
        """Fecha todas as conexões ao BD"""
        if self.engine:
            self.engine.dispose()
            logger.info("✓ Conexões ao BD fechadas")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ════════════════════════════════════════════════════════════════
# Instância Global
# ════════════════════════════════════════════════════════════════

_db_instance: Optional[Database] = None


def get_database() -> Database:
    """
    Retorna instância singleton do Database.
    Garante que há apenas uma conexão ao BD.
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
        _db_instance.initialize()
    return _db_instance


def get_db() -> Generator[Session, None, None]:
    """
    Dependência para FastAPI/async apps.
    Usa padrão de generator.
    
    Exemplo:
        @app.get("/tickers")
        async def get_tickers(db: Session = Depends(get_db)):
            return db.query(TickerModel).all()
    """
    db = get_database()
    with db.get_session() as session:
        yield session


# ════════════════════════════════════════════════════════════════
# Helpers de Teste
# ════════════════════════════════════════════════════════════════

def create_test_database() -> Database:
    """
    Cria database em memória para testes.
    Usa SQLite em vez de PostgreSQL.
    """
    test_db = Database()
    test_db.engine = create_engine("sqlite:///:memory:")
    test_db.SessionLocal = sessionmaker(bind=test_db.engine)
    test_db.scoped_session = scoped_session(test_db.SessionLocal)
    
    # Criar tabelas
    Base.metadata.create_all(bind=test_db.engine)
    
    logger.info("✓ Test database criado em memória")
    return test_db
