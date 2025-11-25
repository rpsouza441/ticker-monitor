"""
Scheduler: Consumer
Loop infinito 24/7 que:
1. Consome jobs da fila RabbitMQ
2. Valida se é hora de executar
3. Chama TickerService.fetch_by_list()
4. Salva via PersistenceService
5. Enfileira próximo job
"""

import logging
import signal
import sys
from datetime import datetime, timedelta
import time
import pytz

from src.config import settings
from src.infrastructure.database import get_database
from src.infrastructure.queue_manager import QueueManager
from src.infrastructure.logger import setup_logging, get_logger
from src.services.ticker_service import TickerService
from src.services.persistence_service import PersistenceService
from src.services.rate_limit_service import RateLimitService
from src.domain.job_message import JobMessage

logger = get_logger(__name__)


class Consumer:
    """
    Consumer principal: processa jobs enfileirados.
    Rodando 24/7 como background worker.
    """
    
    def __init__(self):
        self.db = get_database()
        self.queue_manager = QueueManager()
        self.ticker_service = TickerService(
            batch_size=settings.TICKERS_PER_REQUEST,
            delay_ms=settings.REQUEST_DELAY_MS,
            backoff_base=settings.BACKOFF_BASE,
            max_retries=settings.RABBITMQ_MAX_RETRIES
        )
        self.persistence_service = PersistenceService()
        self.rate_limit_service = RateLimitService()
        self.running = True
        self.tz = settings.tz
    
    def start(self) -> bool:
        """
        Inicia o consumer.
        
        Returns:
            bool: True se inicializado com sucesso
        """
        logger.info("=" * 60)
        logger.info("🚀 INICIANDO TICKER MONITOR CONSUMER")
        logger.info("=" * 60)
        
        # Verificar dependências
        if not self.db.initialize():
            logger.error("✗ Falha ao inicializar BD")
            return False
        
        if not self.queue_manager.connect():
            logger.error("✗ Falha ao conectar RabbitMQ")
            return False
        
        logger.info("✓ BD e RabbitMQ OK")
        
        # Registrar signal handlers para shutdown graceful
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Iniciar consumer
        self.queue_manager.start_consumer(self._process_job)
        logger.info("✓ Consumer iniciado")
        
        return True
    
    def _signal_handler(self, sig, frame):
        """Handler para SIGTERM/SIGINT - graceful shutdown"""
        logger.info("📍 Recebido sinal de encerramento (SIGTERM/SIGINT)")
        self.stop()
        sys.exit(0)
    
    def _process_job(self, ch, method, properties, body):
        """
        Callback para processar cada job da fila.
        
        Args:
            ch: Channel RabbitMQ
            method: Delivery info
            properties: Properties
            body: Body da mensagem (JSON)
        """
        job_id = None
        try:
            # 1. Desserializar job
            job = JobMessage.from_json(body.decode('utf-8'))
            job_id = job.job_id
            
            logger.info(f"📨 Job recebido: {job_id}")
            logger.info(f"   Tickers: {len(job.ticker_list)}")
            logger.info(f"   Scheduled: {job.execution_time}")
            logger.info(f"   Tentativa: {job.retry_count + 1}")
            
            
            # 2. Validar se é hora de executar
            should_exec = self._should_execute(job.execution_time)
            
            if not should_exec:
                # Se retornou False por duplicação, remover da fila (ACK)
                # Se retornou False por horário futuro, recolocar na fila (NACK requeue)
                
                # Verificar se foi por duplicação (olhando a última mensagem de log)
                # Por simplicidade, vamos sempre fazer ACK quando should_execute = False
                # O job de amanhã será criado automaticamente após sucesso
                logger.debug(f"⏰ Job não pode ser executado agora. Removendo da fila.")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            
            # 3. Executar fetch
            logger.info(f"🔄 Buscando dados de {len(job.ticker_list)} tickers...")
            results, failed = self.ticker_service.fetch_by_list(job.ticker_list)
            
            logger.info(f"✓ Fetch completo: {len(results)} sucesso, {len(failed)} falhas")
            
            # 4. Salvar dados
            logger.info("💾 Persistindo dados...")
            saved, failed_save = self.persistence_service.save_all(results)
            logger.info(f"✓ Salvos: {saved}")
            
            # 5. Registrar job como executado (anti-duplicação)
            self._register_job_execution(job)
            
            # 6. Enfileirar próximo job
            next_execution = self._next_execution_time(job.execution_time)
            next_job = JobMessage(
                ticker_list=job.ticker_list,
                execution_time=next_execution,
                retry_count=0
            )
            
            self.queue_manager.produce_job(next_job)
            logger.info(f"⏰ Próximo job enfileirado para {next_execution.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 7. Confirmar processamento
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"✓ Job {job_id} processado com sucesso")
        
        except Exception as e:
            logger.error(f"✗ Erro ao processar job {job_id}: {e}")
            
            # Retry com backoff
            job = JobMessage.from_json(body.decode('utf-8'))
            if job.retry_count < settings.RABBITMQ_MAX_RETRIES:
                job.retry_count += 1
                delay = (settings.BACKOFF_BASE ** job.retry_count)
                
                logger.warning(
                    f"🔄 Retry {job.retry_count}/{settings.RABBITMQ_MAX_RETRIES} "
                    f"em {delay}s"
                )
                
                time.sleep(delay)
                self.queue_manager.produce_job(job)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            else:
                logger.error(f"💀 Job {job_id} falhou {settings.RABBITMQ_MAX_RETRIES}x")
                self.rate_limit_service.log_block_event(
                    ticker="SYSTEM",
                    retry_count=settings.RABBITMQ_MAX_RETRIES
                )
                self.queue_manager.handle_dead_letter(
                    job_id, 
                    f"Falhou após {settings.RABBITMQ_MAX_RETRIES} tentativas"
                )
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def _should_execute(self, execution_time: datetime) -> bool:
        """
        Valida se é hora de executar (segunda-sexta, horário correto).
        
        Args:
            execution_time: Horário agendado
        
        Returns:
            bool: True se deve executar agora
        """
        now = datetime.now(self.tz)
        scheduled = execution_time.astimezone(self.tz) if execution_time.tzinfo else self.tz.localize(execution_time)
        
        # Verificar se é dia útil (seg=0, sex=4)
        if now.weekday() > 4:
            logger.debug(f"Fim de semana detectado (weekday={now.weekday()})")
            return False
        
        # ═══════════════════════════════════════════════════════════
        # ANTI-DUPLICAÇÃO: Verificar se já executou hoje
        # ═══════════════════════════════════════════════════════════
        from src.domain.ticker_data import JobQueueModel
        
        try:
            with self.db.get_session() as session:
                # Buscar execuções de HOJE que já tiveram sucesso
                # Usa created_at (quando foi registrado) ao invés de execution_time (quando foi agendado)
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                already_executed = session.query(JobQueueModel).filter(
                    JobQueueModel.created_at >= today_start,
                    JobQueueModel.created_at <= today_end,
                    JobQueueModel.status == 'completed'
                ).first()
                
                if already_executed:
                    logger.warning(
                        f"⚠ Job já foi executado hoje às {already_executed.created_at}. "
                        f"Ignorando para evitar duplicação."
                    )
                    return False
        except Exception as e:
            logger.error(f"Erro ao verificar duplicação: {e}")
            # Em caso de erro, prosseguir (fail-safe)
        
        # ═══════════════════════════════════════════════════════════
        # VALIDAÇÃO DE HORÁRIO  
        # ═══════════════════════════════════════════════════════════
        
        # Se o horário agendado já passou, executar imediatamente
        # (evita loop infinito de requeue)
        if scheduled <= now:
            logger.info(f"✓ Horário agendado ({scheduled}) atingido. Executando job.")
            return True
        
        # Se ainda não chegou a hora, aguardar
        time_diff = (scheduled - now).total_seconds()
        logger.debug(f"⏰ Aguardando horário: {scheduled} (faltam {time_diff:.0f}s)")
        return False
    
    def _next_execution_time(self, current: datetime) -> datetime:
        """
        Calcula próxima hora de execução (próximo dia útil).
        
        Args:
            current: Hora de execução atual
        
        Returns:
            datetime: Próxima execução
        """
        next_exec = current + timedelta(days=1)
        
        # Pular fins de semana
        while next_exec.weekday() > 4:
            next_exec += timedelta(days=1)
        
        return next_exec
    
    def _register_job_execution(self, job: JobMessage):
        """
        Registra job executado na tabela job_queue.
        Usado para anti-duplicação.
        
        Args:
            job: JobMessage que foi executado
        """
        from src.domain.ticker_data import JobQueueModel
        import json
        
        try:
            with self.db.get_session() as session:
                job_record = JobQueueModel(
                    ticker_ids=json.dumps(job.ticker_list),
                    execution_time=job.execution_time,
                    retry_count=job.retry_count,
                    status='completed',
                    last_attempted_at=datetime.now(self.tz)
                )
                session.add(job_record)
            
            logger.debug(f"✓ Job registrado no histórico: {job.job_id}")
            
        except Exception as e:
            logger.error(f"Erro ao registrar job no histórico: {e}")
            # Não falhar por conta disso
    
    def stop(self):
        """Para o consumer gracefully"""
        logger.info("🛑 Encerrando consumer...")
        self.running = False
        self.queue_manager.stop_consumer()
        self.queue_manager.close()
        self.db.close()
        logger.info("✓ Consumer encerrado")
    
    def run(self):
        """Loop principal"""
        if not self.start():
            logger.error("Falha ao iniciar consumer")
            sys.exit(1)
        
        # Manter rodando
        try:
            logger.info("✓ Consumer aguardando jobs...")
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrompido pelo usuário")
            self.stop()


# ════════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    setup_logging()
    
    consumer = Consumer()
    consumer.run()
