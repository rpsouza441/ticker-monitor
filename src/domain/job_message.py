"""
Job Message: Estrutura de mensagens para RabbitMQ
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List
import json


@dataclass
class JobMessage:
    """Estrutura de mensagem enfileirada no RabbitMQ"""
    
    ticker_list: List[str]  # Lista de tickers a processar
    execution_time: datetime  # Quando deve executar
    retry_count: int = 0  # Número de tentativas
    job_id: str = None  # ID único do job
    created_at: datetime = None
    
    def __post_init__(self):
        """Inicializa campos padrão"""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.job_id is None:
            import uuid
            self.job_id = str(uuid.uuid4())
    
    def to_json(self) -> str:
        """Serializa para JSON (para fila)"""
        data = {
            'job_id': self.job_id,
            'ticker_list': self.ticker_list,
            'execution_time': self.execution_time.isoformat(),
            'retry_count': self.retry_count,
            'created_at': self.created_at.isoformat(),
        }
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'JobMessage':
        """Desserializa de JSON"""
        data = json.loads(json_str)
        return cls(
            job_id=data['job_id'],
            ticker_list=data['ticker_list'],
            execution_time=datetime.fromisoformat(data['execution_time']),
            retry_count=data.get('retry_count', 0),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.utcnow().isoformat())),
        )
    
    def __repr__(self) -> str:
        return (
            f"JobMessage(job_id={self.job_id}, tickers={len(self.ticker_list)}, "
            f"retry={self.retry_count}, scheduled={self.execution_time})"
        )
