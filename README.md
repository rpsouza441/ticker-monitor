# Ticker Monitor - Sistema de Monitoramento de Ações com yfinance

Sistema de produção para monitorar tickers de forma contínua usando **yfinance + PostgreSQL + RabbitMQ**.

## 🎯 Características

- ✅ **Monitoramento contínuo** de múltiplos tickers via RabbitMQ
- ✅ **Requisições em batch** (configurável, padrão 10 tickers)
- ✅ **Retry com backoff exponencial** (máx 10 tentativas)
- ✅ **Rate limit tracking** em tabela separada
- ✅ **Histórico completo** (OHLCV até 10 anos)
- ✅ **Dados fundamentalistas** (P/E, EPS, dividend yield, market cap)
- ✅ **Suporte multi-ativo**: Ações, FIIs, BDRs, ETFs, Criptomoedas
- ✅ **Logging estruturado** (JSON)
- ✅ **Arquitetura de serviços** (Domain, Services, Infrastructure)
- ✅ **Health checks** automáticos
- ✅ **Docker Compose** pronto para produção

---

## 🚀 Quick Start

### 1. Clonar e Configurar

```bash
git clone <seu-repo> ticker-monitor
cd ticker-monitor

# Copiar arquivo de ambiente
cp .env.example .env

# Editar tickers (opcional)
nano .env
# MONITORED_TICKERS=PETR4.SA,VALE3.SA,WEGE3.SA,...
```

### 2. Subir Stack

```bash
docker-compose up -d

# Verificar status
docker-compose ps
docker-compose logs -f ticker-monitor
```

### 3. Monitorar

**RabbitMQ Management** (ver fila de jobs):
- http://localhost:15672
- Usuário: guest / Senha: guest

**PostgreSQL** (ver dados):
```bash
docker exec -it ticker-postgres psql -U ticker_user -d ticker_db

# Queries úteis:
SELECT * FROM latest_ticker_prices;
SELECT * FROM rate_limit_statistics;
SELECT * FROM rate_limit_events WHERE status = 'ACTIVE';
```

---

## 📋 Configuração

### Variáveis de Ambiente (.env)

```bash
# EXECUÇÃO
EXECUTION_TIME=16:30                 # Horário de atualização diária
TICKERS_PER_REQUEST=10               # Máximo de tickers por requisição
REQUEST_DELAY_MS=300                 # Delay entre requisições (ms)

# TICKERS
MONITORED_TICKERS=PETR4.SA,VALE3.SA,...  # Separados por vírgula

# DATABASE
DATABASE_URL=postgresql://user:pass@postgres:5432/ticker_db
DB_ECHO=false

# RABBITMQ
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
RABBITMQ_QUEUE=ticker_updates
RABBITMQ_MAX_RETRIES=10

# LOGGING
LOG_LEVEL=INFO                       # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json                      # json ou text

# RATE LIMITING
BACKOFF_BASE=2                       # Base para exponencial (2^n)
BACKOFF_MAX_SECONDS=3600             # Máximo de espera

# TIMEZONE
TIMEZONE=America/Sao_Paulo
```

---

## 🏗️ Arquitetura

```
src/
├── config.py                    # Configurações (Pydantic)
├── main.py                      # Entry point
│
├── domain/                      # Entidades
│   ├── ticker_data.py          # Classe TickerData
│   ├── rate_limit_tracker.py   # Rastreamento de bloqueios
│   └── job_message.py          # Mensagens RabbitMQ
│
├── services/                    # Lógica de negócio
│   ├── ticker_service.py       # Fetch yfinance (batches, retry)
│   ├── persistence_service.py  # Salva em BD
│   └── rate_limit_service.py   # Gerencia bloqueios
│
├── infrastructure/              # Infraestrutura
│   ├── database.py             # SQLAlchemy ORM
│   ├── queue_manager.py        # RabbitMQ pub/sub
│   └── logger.py               # Logging estruturado
│
└── scheduler/
    └── consumer.py             # Consumer (rodando 24/7)
```

---

## 📊 Fluxo de Execução

```
┌─────────────────────────────────────────┐
│  Consumer RabbitMQ (24/7)               │
│  Verifica fila a cada 30s               │
└─────────────────┬───────────────────────┘
                  │
                  ▼
        IF hora_atual >= execution_time
                  │
    ┌─────────────┴─────────────┐
    ▼                           ▼
TickerService              RabbitMQ
fetch_by_list()            (enfileira)
├─ Batch 10 tickers
├─ Delay 300ms
├─ Retry com backoff
└─ Rate limit tracking
    │
    ▼
PersistenceService
save_all()
├─ Insert ticker_prices
├─ Insert ticker_fundamentals
├─ Insert ticker_history
└─ Update rate_limit_events
    │
    ▼
Enfileira próxima execução
(amanhã, mesmo horário)
```

---

## 🗄️ Schema do Banco de Dados

### Tabelas Principais

**tickers** - Master de tickers
```sql
id | symbol | asset_type | currency | created_at
```

**ticker_prices** - Preços atualizados
```sql
id | ticker_id | price | volume | updated_at | created_at
```

**ticker_fundamentals** - Dados fundamentalistas
```sql
id | ticker_id | pe_ratio | eps | dividend_yield | market_cap | collected_at
```

**ticker_history** - Histórico OHLCV
```sql
id | ticker_id | date | open | high | low | close | volume
```

**rate_limit_events** - Rastreamento de bloqueios
```sql
id | ticker_id | blocked_at | duration_seconds | retry_count | resolved_at | status
```

**job_queue** - Fila de jobs
```sql
id | ticker_ids | execution_time | retry_count | status | last_attempted_at
```

---

## 📈 Queries Úteis

### Ver últimos preços
```sql
SELECT * FROM latest_ticker_prices
ORDER BY ticker;
```

### Análise de rate limiting
```sql
SELECT * FROM rate_limit_statistics
WHERE total_blocks > 0
ORDER BY total_blocks DESC;
```

### Histórico OHLCV de um ticker
```sql
SELECT th.date, th.open, th.high, th.low, th.close, th.volume
FROM ticker_history th
JOIN tickers t ON th.ticker_id = t.id
WHERE t.symbol = 'PETR4.SA'
ORDER BY th.date DESC
LIMIT 30;
```

### Jobs processados
```sql
SELECT ticker_ids, status, execution_time, last_attempted_at, retry_count
FROM job_queue
ORDER BY created_at DESC
LIMIT 20;
```

---

## 🔍 Monitoramento

### Logs em Tempo Real
```bash
# Todos os serviços
docker-compose logs -f

# Apenas aplicação
docker-compose logs -f ticker-monitor

# PostgreSQL
docker-compose logs -f postgres

# RabbitMQ
docker-compose logs -f rabbitmq
```

### Health Check
```bash
# Verificar saúde de todos os serviços
docker-compose ps

# Testar saúde da aplicação
docker exec ticker-monitor-app curl http://localhost:8000/health
```

---

## 🧪 Testes

```bash
# Entrar no container
docker exec -it ticker-monitor-app bash

# Rodar testes
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=src/
```

---

## 📝 Exemplos de Uso

### Adicionar novo ticker

```bash
# Editar .env
MONITORED_TICKERS=PETR4.SA,VALE3.SA,NOVO_TICKER.SA

# Reiniciar
docker-compose restart ticker-monitor
```

### Consultar dados salvos

```bash
# Entrar no PostgreSQL
docker exec -it ticker-postgres psql -U ticker_user -d ticker_db

# Ver preços mais recentes
SELECT t.symbol, tp.price, tp.volume, tp.updated_at
FROM ticker_prices tp
JOIN tickers t ON tp.ticker_id = t.id
ORDER BY tp.updated_at DESC
LIMIT 10;
```

### Analisar bloqueios

```bash
# Bloqueios ativos
SELECT t.symbol, rle.blocked_at, rle.retry_count, 
       AGE(NOW(), rle.blocked_at) as duration
FROM rate_limit_events rle
JOIN tickers t ON rle.ticker_id = t.id
WHERE rle.status = 'ACTIVE'
ORDER BY rle.blocked_at DESC;
```

---

## 🐛 Troubleshooting

### Container não sobe
```bash
# Ver logs
docker-compose logs ticker-monitor

# Reiniciar
docker-compose restart
```

### Banco não conecta
```bash
# Verificar PostgreSQL
docker-compose logs postgres

# Testar conexão
docker exec ticker-monitor-app psql -h postgres -U ticker_user -d ticker_db -c "SELECT 1"
```

### RabbitMQ não responde
```bash
# Verificar logs
docker-compose logs rabbitmq

# Reiniciar
docker-compose restart rabbitmq
```

### Limpar tudo e recomeçar
```bash
# Parar e remover
docker-compose down -v

# Remover imagem
docker rmi ticker-monitor:latest

# Reconstruir
docker-compose up -d --build
```

---

## 📚 Tecnologias

- **Python 3.11** - Linguagem
- **yfinance 0.2.32** - Dados do Yahoo Finance
- **PostgreSQL 15** - Banco de dados
- **RabbitMQ 3.12** - Message broker
- **SQLAlchemy 2.0** - ORM
- **Pydantic 2.5** - Validação
- **structlog 23.3** - Logging estruturado
- **Docker Compose** - Orquestração

---

## 📞 Suporte

Para dúvidas ou problemas:
1. Verificar logs: `docker-compose logs`
2. Consultar README
3. Verificar `.env` vs `.env.example`

---

## 📄 Licença

MIT License
