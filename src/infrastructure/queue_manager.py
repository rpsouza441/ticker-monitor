"""
Infrastructure: QueueManager
Gerencia RabbitMQ producer/consumer para fila de jobs
Suporta retry, dead letter queue, acknowledgments
"""

import pika
import json
import logging
from typing import Callable, Optional
from threading import Thread
import time

from src.config import settings
from src.domain.job_message import JobMessage

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Gerenciador de fila RabbitMQ.
    Responsabilidades:
    - Conectar ao RabbitMQ
    - Produzir jobs (enfileirar)
    - Consumir jobs (worker)
    - Lidar com DLQ (dead letter queue)
    - Health checks
    """
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.queue_name = settings.RABBITMQ_QUEUE
        self.dlq_name = f"{self.queue_name}_dlq"
        self.consumer_thread = None
        self.is_running = False
    
    def connect(self) -> bool:
        """
        Conecta ao RabbitMQ e declara queues.
        
        Returns:
            bool: True se sucesso
        """
        try:
            # Parsear URL do RabbitMQ
            import urllib.parse
            parsed = urllib.parse.urlparse(settings.RABBITMQ_URL)
            
            credentials = pika.PlainCredentials(
                parsed.username or 'guest',
                parsed.password or 'guest'
            )
            
            parameters = pika.ConnectionParameters(
                host=parsed.hostname or 'localhost',
                port=parsed.port or 5672,
                credentials=credentials,
                connection_attempts=3,
                retry_delay=2,
                heartbeat=600,
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declarar exchanges e queues
            self._declare_queues()
            
            logger.info("✓ Conectado ao RabbitMQ")
            return True
        
        except Exception as e:
            logger.error(f"✗ Erro ao conectar ao RabbitMQ: {e}")
            return False
    
    def _declare_queues(self):
        """Declara queues e exchanges com configurações de retry"""
        
        # Exchange padrão
        self.channel.exchange_declare(
            exchange='ticker_exchange',
            exchange_type='direct',
            durable=True
        )
        
        # Dead Letter Queue (para mensagens que falharam 10x)
        self.channel.queue_declare(
            queue=self.dlq_name,
            durable=True
        )
        self.channel.queue_bind(
            queue=self.dlq_name,
            exchange='ticker_exchange',
            routing_key=f'{self.queue_name}_dlq'
        )
        
        # Fila principal com TTL e DLQ
        self.channel.queue_declare(
            queue=self.queue_name,
            durable=True,
            arguments={
                'x-dead-letter-exchange': 'ticker_exchange',
                'x-dead-letter-routing-key': f'{self.queue_name}_dlq',
                'x-message-ttl': 86400000,  # 24 horas
            }
        )
        self.channel.queue_bind(
            queue=self.queue_name,
            exchange='ticker_exchange',
            routing_key=self.queue_name
        )
        
        logger.debug(f"✓ Queues declaradas: {self.queue_name}, {self.dlq_name}")
    
    def produce_job(self, job: JobMessage) -> bool:
        """
        Produz (enfileira) um novo job.
        
        Args:
            job: JobMessage com dados
        
        Returns:
            bool: True se sucesso
        """
        try:
            if not self.channel:
                logger.error("Canal não conectado")
                return False
            
            message = job.to_json()
            
            self.channel.basic_publish(
                exchange='ticker_exchange',
                routing_key=self.queue_name,
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistente
                    content_type='application/json',
                )
            )
            
            logger.info(f"✓ Job enfileirado: {job.job_id}")
            return True
        
        except Exception as e:
            logger.error(f"✗ Erro ao produzir job: {e}")
            return False
    
    def start_consumer(self, callback: Callable):
        """
        Inicia consumer em thread separada.
        
        Args:
            callback: Função que processa cada job
                      Assinatura: callback(channel, method, properties, body)
        """
        if self.is_running:
            logger.warning("Consumer já está rodando")
            return
        
        self.is_running = True
        self.consumer_thread = Thread(
            target=self._consumer_loop,
            args=(callback,),
            daemon=False
        )
        self.consumer_thread.start()
        logger.info("✓ Consumer iniciado em thread separada")
    
    def _consumer_loop(self, callback: Callable):
        """Loop do consumer (rodando em thread)"""
        try:
            self.channel.basic_qos(prefetch_count=1)  # 1 job por vez
            
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=callback,
                auto_ack=False
            )
            
            logger.info(f"✓ Consumer aguardando mensagens em {self.queue_name}...")
            self.channel.start_consuming()
        
        except Exception as e:
            logger.error(f"✗ Erro no consumer loop: {e}")
            self.is_running = False
    
    def stop_consumer(self):
        """Para o consumer gracefully"""
        if self.channel and self.is_running:
            self.channel.stop_consuming()
            self.is_running = False
            logger.info("✓ Consumer parado")
    
    def handle_dead_letter(self, job_id: str, reason: str):
        """
        Registra job que falhou permanentemente (DLQ).
        
        Args:
            job_id: ID do job
            reason: Motivo da falha
        """
        logger.error(
            f"💀 Job morto: {job_id} - {reason} "
            f"(será movido para DLQ)"
        )
    
    def health_check(self) -> bool:
        """
        Verifica saúde da conexão RabbitMQ.
        
        Returns:
            bool: True se OK
        """
        try:
            if not self.connection or self.connection.is_closed:
                logger.error("Conexão RabbitMQ fechada")
                return False
            
            # Testar ping
            self.channel.queue_declare(
                queue='test_queue',
                passive=True
            )
            return True
        
        except Exception as e:
            logger.error(f"✗ RabbitMQ health check falhou: {e}")
            return False
    
    def close(self):
        """Fecha conexão gracefully"""
        try:
            self.stop_consumer()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                logger.info("✓ Conexão RabbitMQ fechada")
        except Exception as e:
            logger.error(f"Erro ao fechar RabbitMQ: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def check_rabbitmq_health() -> bool:
    """Health check function para Docker"""
    try:
        qm = QueueManager()
        result = qm.connect() and qm.health_check()
        qm.close()
        return result
    except:
        return False
