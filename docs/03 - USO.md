# Guia de Uso e Operação

## 🚀 Iniciar o Sistema

### Primeira Execução

```bash
# Subir stack completa
docker-compose up -d

# Aguardar inicialização (10-15 segundos)
sleep 10

# Verificar logs
docker-compose logs -f ticker-monitor

# Você deve ver:
# ✓ Conexão ao PostgreSQL estabelecida
# ✓ Migrations executadas com sucesso
# ✓ Conectado ao RabbitMQ
# ✓ Consumer iniciado
# ✓ Consumer aguardando mensagens...
```

### Usando Make

```bash
# Subir
make up

# Logs
make logs

# Status
make ps

# Parar
make down
```

---

## 📊 Monitorar em Tempo Real

### RabbitMQ Management

Acesse: **http://localhost:15672**

- **Usuário**: guest
- **Senha**: guest

Visualize:
- **Queues**: `ticker_updates` (fila principal) + `ticker_updates_dlq` (dead letter)
- **Messages**: Quantidade de jobs na fila
- **Connections**: Consumidores conectados
- **Channels**: Canais de comunicação

### Logs em Tempo Real

```bash
# Todos os serviços
docker-compose logs -f

# Apenas aplicação
docker-compose logs -f ticker-monitor

# Apenas PostgreSQL
docker-compose logs -f postgres

# Apenas RabbitMQ
docker-compose logs -f rabbitmq

# Últimas 100 linhas
docker-compose logs --tail 100

# Com timestamps
docker-compose logs -f -t
```

### Banco de Dados

```bash
# Conectar
docker exec -it ticker-postgres psql -U ticker_user -d ticker_db

# Queries úteis dentro do psql:

-- Ver tickers monitorados
SELECT * FROM tickers;

-- Últimos preços
SELECT * FROM latest_ticker_prices;

-- Rate limiting (últimas ocorrências)
SELECT * FROM rate_limit_events 
ORDER BY blocked_at DESC LIMIT 10;

-- Estatísticas por ticker
SELECT * FROM rate_limit_statistics;

-- Histórico de um ticker (30 dias)
SELECT * FROM ticker_history 
WHERE ticker_id = 1 
ORDER BY date DESC LIMIT 30;

-- Jobs processados
SELECT * FROM job_queue 
ORDER BY created_at DESC LIMIT 20;
```

---

## 🔧 Operações Comuns

### Adicionar Novo Ticker

```bash
# 1. Editar .env
nano .env

# Adicionar ticker na lista
MONITORED_TICKERS=PETR4.SA,VALE3.SA,NOVO.SA

# 2. Reiniciar consumer
docker-compose restart ticker-monitor

# 3. Verificar logs
docker-compose logs -f ticker-monitor
```

### Pausar Monitoramento

```bash
# Parar consumer sem perder fila
docker-compose stop ticker-monitor

# Restart
docker-compose start ticker-monitor
```

### Limpar Dead Letter Queue

```bash
# Conectar RabbitMQ (via admin ou API)
# http://localhost:15672

# Ou via CLI
docker exec -it ticker-rabbitmq rabbitmqctl purge_queue ticker_updates_dlq
```

### Resetar Banco de Dados

⚠️ **CUIDADO - Remove todos os dados!**

```bash
# 1. Parar containers
docker-compose down -v

# 2. Subir novamente (sem dados)
docker-compose up -d
```

### Ver Estatísticas em Tempo Real

```bash
# Resource usage
docker stats

# Resultado:
# CONTAINER         MEM USAGE / LIMIT    CPU %    PIDS
# ticker-monitor    120.5MiB / 2GiB      2.1%     12
# ticker-postgres   256.8MiB / 2GiB      0.5%     8
# ticker-rabbitmq   180.3MiB / 2GiB      1.2%     45
```

---

## 📈 Monitoramento e Alertas

### Health Check

```bash
# Completo
make health

# Ou via Python
python3 -c "from src.main import health_check; import json; print(json.dumps(health_check(), indent=2))"

# Resultado esperado:
# {
#   'timestamp': '2025-11-25T14:30:00',
#   'components': {
#     'database': true,
#     'rabbitmq': true,
#     'yfinance': true
#   },
#   'healthy': true
# }
```

### Alerts Comuns

#### Consumer não processando

```bash
# Sintoma: Fila crescendo mas consumer não faz nada

# Verificação
docker-compose logs ticker-monitor | grep "aguardando mensagens"

# Se não aparecer, reiniciar
docker-compose restart ticker-monitor
```

#### Rate limit muito frequente

```bash
# Sintoma: Muitos eventos em rate_limit_events

# Consultar
SELECT COUNT(*) FROM rate_limit_events 
WHERE blocked_at > NOW() - INTERVAL '1 hour'
AND status = 'ACTIVE';

# Soluções:
# 1. Aumentar BACKOFF_MAX_SECONDS
# 2. Diminuir TICKERS_PER_REQUEST
# 3. Aumentar REQUEST_DELAY_MS
```

#### Banco crescendo muito

```bash
# Ver tamanho
SELECT pg_size_pretty(pg_database_size('ticker_db'));

# Limpar histórico antigo
DELETE FROM ticker_history 
WHERE date < NOW() - INTERVAL '1 year';

# Vacuum
VACUUM ANALYZE;
```

#### Memory leak no consumer

```bash
# Verificar uso
docker stats ticker-monitor

# Se aumentar continuamente:
# 1. Reiniciar
docker-compose restart ticker-monitor

# 2. Ou limpar logs
docker logs --tail 1000 ticker-monitor > /dev/null
```

---

## 🔍 Debugging

### Ver Variáveis de Ambiente

```bash
# Dentro do container
docker exec -it ticker-monitor env | grep TICKER

# Resultado:
# EXECUTION_TIME=16:30
# TICKERS_PER_REQUEST=10
# MONITORED_TICKERS=PETR4.SA,VALE3.SA
```

### Testar Fetch Manualmente

```python
from src.services.ticker_service import TickerService

service = TickerService()
results, failed = service.fetch_by_list(['PETR4.SA', 'VALE3.SA'])

for ticker in results:
    print(f"{ticker.ticker}: {ticker.last_price}")

print(f"Falharam: {failed}")
```

### Testar Persistência

```python
from src.services.persistence_service import PersistenceService
from src.services.ticker_service import TickerService

ticker_service = TickerService()
persistence_service = PersistenceService()

results, _ = ticker_service.fetch_by_list(['PETR4.SA'])
saved, failed = persistence_service.save_all(results)

print(f"Salvos: {saved}")
```

### Testar Rate Limiting

```python
from src.services.rate_limit_service import RateLimitService

service = RateLimitService()

# Log de bloqueio
tracker = service.log_block_event('PETR4.SA', retry_count=5)

# Obter stats
stats = service.get_statistics('PETR4.SA')
print(f"Total bloqueios: {stats.total_blocks}")

# Listar ativos
active = service.get_active_blocks()
for block in active:
    print(f"{block.ticker} bloqueado")
```

---

## 📅 Agendamento

### Como Funciona

```
├─ 16:30 (HH:MM definido em EXECUTION_TIME)
│  └─ Consumer valida: é dia útil (seg-sex)? É a hora certa?
│     ├─ SIM: Busca tickers → Salva → Próximo job
│     └─ NÃO: Volta à fila, reavalia depois
│
└─ Próximo job enfileirado para amanhã 16:30
   └─ Se amanhã for feriado/fim de semana, pula para próximo útil
```

### Alterar Horário

```bash
# 1. Editar .env
EXECUTION_TIME=10:00  # Mudar para 10:00 AM

# 2. Reiniciar
docker-compose restart ticker-monitor

# 3. Verificar logs
docker-compose logs -f ticker-monitor
```

### Feriados e Fins de Semana

O sistema **automaticamente** pula:
- ❌ Sábado e domingo
- ❌ Feriados (configurável em config.py)

---

## 🚨 Procedures de Emergência

### Parar Consumer Gracefully

```bash
# O consumer respeita SIGTERM e finaliza limpo
docker-compose stop -t 30 ticker-monitor

# Aguarda até 30 segundos
# Completa operação atual antes de parar
```

### Resetar Fila

```bash
# Descartar jobs não processados
docker exec -it ticker-rabbitmq \
  rabbitmqctl purge_queue ticker_updates

# E DLQ
docker exec -it ticker-rabbitmq \
  rabbitmqctl purge_queue ticker_updates_dlq
```

### Limpar Tudo

```bash
# ⚠️ CUIDADO - Remove TUDO

# Parar e remover
docker-compose down -v

# Remove:
# - Containers
# - Volumes (dados do BD)
# - Networks
# - Imagens não usadas

# Depois de confirmar, subir novo
docker-compose up -d
```

---

## 📋 Checklists

### Checklist Diário

```
[ ] docker-compose ps - tudo rodando?
[ ] Logs - algum erro?
[ ] RabbitMQ - fila vazia?
[ ] BD - espaço disponível?
[ ] Consumer - processando jobs?
```

### Checklist Semanal

```
[ ] Verificar estatísticas de rate limit
[ ] Limpar logs antigos
[ ] Revisar performance
[ ] Testar failover (parar/reiniciar)
[ ] Backup de dados
```

### Checklist Mensal

```
[ ] Atualizar dependências (pip)
[ ] Revisar histórico antigo (limpar se necessário)
[ ] Análise de performance
[ ] Testes de recovery
[ ] Documentação atualizada
```

---

## 📞 Suporte

Problema? Veja:
- `docs/TROUBLESHOOTING.md` - Erros comuns
- `docs/DOCUMENTACAO-COMPLETA.md` - Referência técnica
- Logs: `docker-compose logs`
- RabbitMQ: http://localhost:15672

**Status**: ✅ Pronto para usar!
