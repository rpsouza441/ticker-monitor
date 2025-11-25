# Referência de API e Código

## 🎯 Como Usar os Serviços

### 1. TickerService - Buscar Dados

```python
from src.services.ticker_service import TickerService

# Criar instância
service = TickerService(
    batch_size=10,           # Quantos tickers por requisição
    delay_ms=300,            # Delay entre requisições (ms)
    backoff_base=2,          # Base para retry (2^n segundos)
    max_retries=10           # Máximo de tentativas
)

# Buscar lista de tickers
tickers_to_fetch = ['PETR4.SA', 'VALE3.SA', 'WEGE3.SA']
results, failed = service.fetch_by_list(tickers_to_fetch)

# results é uma lista de TickerData
for ticker_data in results:
    print(f"{ticker_data.ticker}")
    print(f"  Preço: R$ {ticker_data.last_price:.2f}")
    print(f"  Volume: {ticker_data.volume:,}")
    print(f"  P/E: {ticker_data.pe_ratio}")
    print(f"  Dividend Yield: {ticker_data.dividend_yield:.2%}")

# failed é uma lista de símbolos que falharam
if failed:
    print(f"Falharam: {', '.join(failed)}")
```

### 2. PersistenceService - Salvar em BD

```python
from src.services.persistence_service import PersistenceService
from src.services.ticker_service import TickerService

# Criar instâncias
ticker_service = TickerService()
persistence_service = PersistenceService()

# Buscar e salvar
ticker_list = ['PETR4.SA', 'VALE3.SA']
results, failed = ticker_service.fetch_by_list(ticker_list)

# Salvar todos
saved_count, failed_save = persistence_service.save_all(results)
print(f"Salvos: {saved_count}, Falharam: {len(failed_save)}")

# Ou salvar um por um
for ticker_data in results:
    success = persistence_service.save_ticker_data(ticker_data)
    if success:
        print(f"✓ {ticker_data.ticker} salvo")
    else:
        print(f"✗ {ticker_data.ticker} falhou")

# Consultar dados salvos
latest_price = persistence_service.get_latest_price('PETR4.SA')
print(f"Último preço PETR4: R$ {latest_price:.2f}")
```

### 3. RateLimitService - Rastrear Bloqueios

```python
from src.services.rate_limit_service import RateLimitService

service = RateLimitService()

# Registrar bloqueio
tracker = service.log_block_event('PETR4.SA', retry_count=5)
print(f"Bloqueio registrado às {tracker.blocked_at}")

# Marcar como resolvido
service.log_resolution(event_id=1)

# Obter estatísticas de um ticker
stats = service.get_statistics('PETR4.SA')
print(f"Total bloqueios: {stats.total_blocks}")
print(f"Última ocorrência: {stats.last_block_at}")
print(f"Duração total: {stats.total_duration_seconds} segundos")
print(f"Duração média: {stats.average_duration_seconds:.1f} segundos")

# Listar tickers com mais bloqueios
all_stats = service.get_all_statistics()
for ticker, stat in sorted(all_stats.items(), 
                           key=lambda x: x[1].total_blocks, 
                           reverse=True)[:5]:
    print(f"{ticker}: {stat.total_blocks} bloqueios")

# Verificar se está bloqueado
is_blocked = service.is_ticker_blocked('PETR4.SA')
if is_blocked:
    print("⏸ PETR4 está bloqueado!")
```

### 4. Database - Gerenciar Conexão

```python
from src.infrastructure.database import get_database
from src.domain.ticker_data import TickerModel, TickerPriceModel

# Obter singleton
db = get_database()
db.initialize()  # Conecta + executa migrations

# Consultar com session
with db.get_session() as session:
    # SELECT
    ticker = session.query(TickerModel)\
        .filter_by(symbol='PETR4.SA')\
        .first()
    
    if ticker:
        print(f"ID: {ticker.id}, Símbolo: {ticker.symbol}")

# Inserir/Atualizar com transação ACID
with db.get_db_transaction() as session:
    # INSERT
    new_ticker = TickerModel(
        symbol='NOVO.SA',
        asset_type='STOCK',
        currency='BRL'
    )
    session.add(new_ticker)
    
    # UPDATE
    ticker = session.query(TickerModel)\
        .filter_by(symbol='PETR4.SA')\
        .first()
    if ticker:
        ticker.currency = 'USD'  # Modificação
    
    # COMMIT automático ao sair do bloco

# Raw SQL query
results = db.execute_raw_sql(
    """
    SELECT t.symbol, tp.price 
    FROM ticker_prices tp
    JOIN tickers t ON tp.ticker_id = t.id
    WHERE tp.price > :min_price
    ORDER BY tp.updated_at DESC
    """,
    {"min_price": 100.0}
)

# Health check
if db.health_check():
    print("✓ BD conectado")

# Informações de conexão
info = db.get_connection_info()
print(f"Pool: {info['pool_size']} conexões, "
      f"{info['pool_checked_out']} em uso")

# Fechar conexões
db.close()
```

### 5. QueueManager - RabbitMQ

```python
from src.infrastructure.queue_manager import QueueManager
from src.domain.job_message import JobMessage
from datetime import datetime

qm = QueueManager()

# Conectar
if not qm.connect():
    print("Erro ao conectar RabbitMQ")
    exit(1)

# Enfileirar job
job = JobMessage(
    ticker_list=['PETR4.SA', 'VALE3.SA', 'WEGE3.SA'],
    execution_time=datetime.utcnow(),
    retry_count=0
)

if qm.produce_job(job):
    print(f"✓ Job {job.job_id} enfileirado")

# Iniciar consumer
def process_message(ch, method, properties, body):
    """Callback chamado para cada mensagem"""
    try:
        job = JobMessage.from_json(body.decode())
        print(f"Processando {len(job.ticker_list)} tickers")
        
        # Seu código aqui
        
        # Confirmar processamento
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Erro: {e}")
        # Rejeitar e voltar à fila
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

# Usar consumer
qm.start_consumer(process_message)
# ... rodando em thread separada

# Health check
if qm.health_check():
    print("✓ RabbitMQ OK")

# Fechar gracefully
qm.stop_consumer()
qm.close()
```

### 6. Models - Estrutura de Dados

```python
from src.domain.ticker_data import TickerData
from datetime import datetime
import pandas as pd

# Criar TickerData (manualmente, para testes)
ticker_data = TickerData(
    ticker='PETR4.SA',
    asset_type='STOCK',
    currency='BRL',
    last_price=28.45,
    last_updated=datetime.utcnow(),
    volume=125_000_000,
    
    # Opcional - fundamentalistas
    pe_ratio=5.2,
    eps=5.47,
    dividend_yield=0.08,
    market_cap=200_000_000_000,
    
    # Opcional - histórico OHLCV
    history_ohlcv=pd.DataFrame({
        'Open': [28.0, 28.2],
        'High': [28.5, 28.7],
        'Low': [27.9, 28.1],
        'Close': [28.4, 28.6],
        'Volume': [100_000_000, 105_000_000]
    }, index=pd.DatetimeIndex(['2025-11-25', '2025-11-26']))
)

# Acessar campos
print(f"{ticker_data.ticker}: R$ {ticker_data.last_price}")
print(f"P/E: {ticker_data.pe_ratio}")
```

---

## 📚 Estrutura de Dados

### TickerData

```python
class TickerData:
    ticker: str                  # Ex: "PETR4.SA"
    asset_type: str              # "STOCK", "ETF", "FII", "CRYPTO"
    currency: str                # "BRL", "USD", etc
    last_price: float            # Preço atual
    last_updated: datetime       # Quando foi atualizado
    volume: int                  # Volume do dia
    pe_ratio: Optional[float]    # P/E ratio
    eps: Optional[float]         # Earnings per share
    dividend_yield: Optional[float]  # Dividendo %
    market_cap: Optional[int]    # Capitalização de mercado
    history_ohlcv: DataFrame     # Histórico OHLCV (pandas)
```

### JobMessage

```python
class JobMessage:
    job_id: str                  # UUID
    ticker_list: List[str]       # Tickers a processar
    execution_time: datetime     # Quando deve executar
    retry_count: int             # Tentativa atual
    created_at: datetime         # Quando foi criado
    updated_at: datetime         # Última atualização
```

### RateLimitTracker

```python
class RateLimitTracker:
    ticker: str                  # "PETR4.SA"
    blocked_at: datetime         # Quando foi bloqueado
    retry_count: int             # Tentativas até bloqueio
    status: str                  # "ACTIVE" ou "RESOLVED"
```

### RateLimitStatistics

```python
class RateLimitStatistics:
    ticker: str
    total_blocks: int            # Total de bloqueios
    total_duration_seconds: int  # Tempo total bloqueado
    last_block_at: Optional[datetime]
    max_retries_in_block: int
    average_duration_seconds: float
    most_recent_retry_count: int
```

---

## 🔗 Padrões de Uso

### Padrão 1: Fetch → Save → Next Job

```python
from src.services.ticker_service import TickerService
from src.services.persistence_service import PersistenceService
from src.infrastructure.queue_manager import QueueManager
from src.domain.job_message import JobMessage
from datetime import datetime, timedelta

ticker_service = TickerService()
persistence_service = PersistenceService()
qm = QueueManager()
qm.connect()

# Simular job
job = JobMessage(
    ticker_list=['PETR4.SA', 'VALE3.SA'],
    execution_time=datetime.utcnow()
)

# 1. Buscar
results, failed = ticker_service.fetch_by_list(job.ticker_list)
print(f"Buscados: {len(results)}, Falharam: {len(failed)}")

# 2. Salvar
saved, failed_save = persistence_service.save_all(results)
print(f"Salvos: {saved}")

# 3. Próximo job
next_time = datetime.utcnow() + timedelta(days=1)
next_job = JobMessage(
    ticker_list=job.ticker_list,
    execution_time=next_time,
    retry_count=0
)
qm.produce_job(next_job)
print(f"Próximo job enfileirado para {next_time}")

qm.close()
```

### Padrão 2: Retry com Backoff

```python
from src.services.ticker_service import TickerService
from src.config import settings
import time

service = TickerService(
    batch_size=10,
    delay_ms=300,
    backoff_base=2,
    max_retries=10
)

try:
    results, failed = service.fetch_by_list(['PETR4.SA'])
    print(f"Sucesso: {len(results)}")
except Exception as e:
    # Retry automático já incluído no TickerService
    print(f"Falhou: {e}")
```

### Padrão 3: Monitorar Rate Limit

```python
from src.services.rate_limit_service import RateLimitService

service = RateLimitService()

# Verificar se bloqueado
if service.is_ticker_blocked('PETR4.SA'):
    print("⏸ Aguarde até que seja desbloqueado")
    
    # Ver quanto tempo falta
    stats = service.get_statistics('PETR4.SA')
    if stats.last_block_at:
        print(f"Última ocorrência: {stats.last_block_at}")

# Listar todos bloqueados
blocked = service.get_active_blocks()
for block in blocked:
    print(f"⏸ {block.ticker} bloqueado há {block.blocked_at}")
```

---

## 🧪 Testes Rápidos

```python
# Importar tudo
from src.infrastructure.database import get_database
from src.services.ticker_service import TickerService
from src.services.persistence_service import PersistenceService
from src.services.rate_limit_service import RateLimitService
from src.infrastructure.queue_manager import QueueManager

# Inicializar
db = get_database()
db.initialize()

ticker_service = TickerService()
persistence_service = PersistenceService()
rate_limit_service = RateLimitService()

# Teste 1: Buscar um ticker
print("=== Teste 1: Fetch ===")
results, failed = ticker_service.fetch_by_list(['PETR4.SA'])
if results:
    print(f"✓ {results[0].ticker}: R$ {results[0].last_price}")

# Teste 2: Salvar
print("\n=== Teste 2: Save ===")
saved, _ = persistence_service.save_all(results)
print(f"✓ {saved} tickers salvos")

# Teste 3: Consultar
print("\n=== Teste 3: Query ===")
price = persistence_service.get_latest_price('PETR4.SA')
print(f"✓ Último preço PETR4: R$ {price}")

# Teste 4: Rate limit
print("\n=== Teste 4: Rate Limit ===")
stats = rate_limit_service.get_all_statistics()
print(f"✓ {len(stats)} tickers com bloqueios registrados")

print("\n=== Tudo OK! ===")
```

---

**Próximas páginas**: 
- `TROUBLESHOOTING.md` - Erros e soluções
- `DOCUMENTACAO-COMPLETA.md` - Referência completa
