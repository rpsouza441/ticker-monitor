# Guia de Instalação e Setup

## 📋 Pré-requisitos

- **Python**: 3.11 ou superior
- **Docker**: 20.10 ou superior
- **Docker Compose**: 2.0 ou superior
- **Git**: Qualquer versão recente
- **Espaço em disco**: Mínimo 10GB
- **Conexão internet**: Para baixar dependências e dados

## 🚀 Setup Rápido (Recomendado - 5 minutos)

### Opção 1: Automatizado com Script

```bash
# 1. Clonar repositório
git clone <url> ticker-monitor
cd ticker-monitor

# 2. Executar setup.sh
chmod +x setup.sh
bash setup.sh

# 3. Verificar
docker-compose ps
docker-compose logs -f ticker-monitor
```

**O script irá automaticamente:**
- ✅ Verificar dependências (Python, Docker)
- ✅ Renomear arquivos __init__.py
- ✅ Mover migrations
- ✅ Criar estrutura de pastas
- ✅ Instalar pacotes Python
- ✅ Copiar .env
- ✅ Subir Docker Compose

### Opção 2: Manual Passo a Passo

#### Passo 1: Preparar Arquivos

```bash
# Renomear __init__.py (7 arquivos)
mv __init__-src-main.py src/__init__.py
mv __init__-domain.py src/domain/__init__.py
mv __init__-infrastructure.py src/infrastructure/__init__.py
mv __init__-services.py src/services/__init__.py
mv __init__-scheduler.py src/scheduler/__init__.py
mv __init__-tests.py tests/__init__.py
mv __init__-migrations-versions.py migrations/versions/__init__.py

# Mover migration
mv 001_initial.py migrations/versions/001_initial.py

# Verificar estrutura
tree src/
# ou
find src -type f -name "*.py" | sort
```

#### Passo 2: Configurar Ambiente

```bash
# Copiar .env
cp .env.example .env

# Editar (opcional - defaults funcionam)
nano .env  # ou use seu editor favorito

# Chaves importantes em .env:
# EXECUTION_TIME=16:30                 # Horário de execução
# MONITORED_TICKERS=PETR4.SA,VALE3.SA  # Tickers a monitorar
# DATABASE_URL=postgresql://...        # URL do banco (já correto para Docker)
```

#### Passo 3: Instalar Dependências Python

```bash
# Criar virtual env (opcional mas recomendado)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Verificar instalação
python3 -c "import yfinance; print('✓ yfinance OK')"
python3 -c "import psycopg2; print('✓ psycopg2 OK')"
python3 -c "import pika; print('✓ pika OK')"
```

#### Passo 4: Subir Docker Compose

```bash
# Subir stack (PostgreSQL + RabbitMQ + App)
docker-compose up -d

# Verificar status
docker-compose ps

# Resultado esperado:
# NAME                    STATUS
# ticker-postgres         Up 2 minutes
# ticker-rabbitmq         Up 2 minutes  
# ticker-monitor-app      Up 1 minute

# Ver logs (Ctrl+C para parar)
docker-compose logs -f ticker-monitor
```

---

## ✅ Verificar Instalação

### 1. Health Check Completo

```bash
python3 -c "
from src.main import health_check
import json
result = health_check()
print(json.dumps(result, indent=2))
"

# Resultado esperado:
# {
#   'timestamp': '2025-11-25T...',
#   'components': {
#     'database': true,
#     'rabbitmq': true,
#     'yfinance': true
#   },
#   'healthy': true
# }
```

### 2. Testar Banco de Dados

```bash
# Conectar ao PostgreSQL
docker exec -it ticker-postgres psql -U ticker_user -d ticker_db

# Dentro do psql:
\dt  # Ver todas as tabelas

# Resultado esperado:
# tickers
# ticker_prices
# ticker_fundamentals
# ticker_history
# rate_limit_events
# job_queue

\q  # Sair
```

### 3. Testar RabbitMQ

```bash
# Abrir no navegador
open http://localhost:15672
# ou acessar manualmente:
# http://localhost:15672

# Login:
# Usuario: guest
# Senha: guest

# Verificar:
# - Queues: deve ter "ticker_updates"
# - Connections: deve ter conexões ativas
```

### 4. Teste de Integração

```bash
# Enfileirar job manualmente
python3 << 'EOF'
from src.infrastructure.queue_manager import QueueManager
from src.domain.job_message import JobMessage
from datetime import datetime

qm = QueueManager()
if qm.connect():
    job = JobMessage(
        ticker_list=['PETR4.SA', 'VALE3.SA'],
        execution_time=datetime.utcnow(),
        retry_count=0
    )
    if qm.produce_job(job):
        print("✓ Job enfileirado com sucesso")
    qm.close()
EOF

# Verificar em http://localhost:15672/
```

---

## 🔧 Configuração Detalhada

### Variáveis de Ambiente (.env)

#### Execução e Scheduler

```bash
# Horário de execução (HH:MM) - segunda a sexta
EXECUTION_TIME=16:30

# Lista de tickers a monitorar (separados por vírgula)
MONITORED_TICKERS=PETR4.SA,VALE3.SA,WEGE3.SA,KNRI11.SA

# Tickers por requisição (menor = menos bloqueio, mais requisições)
TICKERS_PER_REQUEST=10

# Delay entre requisições em milisegundos
REQUEST_DELAY_MS=300

# Fuso horário (para scheduler)
TIMEZONE=America/Sao_Paulo
```

#### Database

```bash
# URL de conexão PostgreSQL
DATABASE_URL=postgresql://ticker_user:ticker_pass@postgres:5432/ticker_db

# Echo de SQL queries (para debug)
DB_ECHO=false
```

#### RabbitMQ

```bash
# URL de conexão RabbitMQ
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

# Nome da fila
RABBITMQ_QUEUE=ticker_updates

# Máximo de tentativas antes de DLQ
RABBITMQ_MAX_RETRIES=10
```

#### Rate Limiting

```bash
# Base para backoff exponencial (2^n segundos)
BACKOFF_BASE=2

# Máximo de espera em segundos
BACKOFF_MAX_SECONDS=3600
```

#### Logging

```bash
# Nível de log: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Formato: json ou texto
LOG_FORMAT=json

# Arquivo de log (deixe em branco para stdout)
LOG_FILE=
```

---

## 🐳 Comandos Docker Úteis

```bash
# Ver status
docker-compose ps

# Ver logs
docker-compose logs -f

# Logs específicos de um serviço
docker-compose logs -f ticker-monitor

# Parar serviços
docker-compose stop

# Parar e remover (sem perder dados)
docker-compose down

# Parar e remover tudo (CUIDADO - remove dados!)
docker-compose down -v

# Reiniciar um serviço
docker-compose restart ticker-monitor

# Executar comando no container
docker exec -it ticker-monitor bash

# Acesso ao PostgreSQL
docker exec -it ticker-postgres psql -U ticker_user -d ticker_db

# Ver uso de recursos
docker stats
```

---

## 🛠️ Troubleshooting de Instalação

### Erro: "Python 3 não encontrado"

```bash
# Verificar versão
python3 --version

# Instalar em macOS (Homebrew)
brew install python@3.11

# Instalar em Ubuntu/Debian
sudo apt-get install python3.11

# Instalar em Windows
# Baixar de: https://www.python.org/downloads/
# Ou: choco install python311
```

### Erro: "Docker não found"

```bash
# macOS/Windows: Instalar Docker Desktop
# https://www.docker.com/products/docker-desktop

# Ubuntu/Debian
sudo apt-get install docker.io docker-compose

# Verificar instalação
docker --version
docker-compose --version
```

### Erro: "Port 5432 already in use"

```bash
# PostgreSQL já rodando. Opções:

# 1. Parar serviço local
sudo systemctl stop postgresql

# 2. Ou usar porta diferente em docker-compose.yml
# Mudar: 5432:5432 → 5433:5432
```

### Erro: "Module not found: src"

```bash
# Verificar que está no diretório correto
pwd
# Deve mostrar: /path/to/ticker-monitor

# Se não estiver, navegar para lá
cd /path/to/ticker-monitor
```

### Erro: "Connection refused" (PostgreSQL)

```bash
# Verificar status
docker-compose ps postgres

# Ver logs
docker-compose logs postgres

# Aguardar inicialização (pode levar 10-15s)
sleep 15

# Tentar conectar
docker exec -it ticker-postgres psql -U ticker_user -d ticker_db

# Se persistir, reiniciar
docker-compose restart postgres
```

### Erro: "Connection refused" (RabbitMQ)

```bash
# Mesmo processo
docker-compose logs rabbitmq
sleep 10
docker-compose restart rabbitmq

# Testar
curl http://localhost:15672
```

---

## 📊 Validação Pós-Instalação

Checklist:

```
[ ] Python 3.11+ instalado
[ ] Docker e Docker Compose funcionando
[ ] Estrutura de pastas criada
[ ] __init__.py renomeados
[ ] 001_initial.py movido
[ ] .env copiado e configurado
[ ] requirements.txt instalado
[ ] docker-compose up funcionando
[ ] PostgreSQL respondendo
[ ] RabbitMQ acessível
[ ] Consumer rodando sem erros
[ ] Migrations executadas
[ ] Banco criado e preenchido
[ ] Health check passando
[ ] RabbitMQ Management acessível
```

---

## 🎯 Próximos Passos

1. **Ler documentação**: `docs/USO.md`
2. **Adicionar tickers**: Editar `MONITORED_TICKERS` em `.env`
3. **Monitorar**: Abrir RabbitMQ Management
4. **Explorar dados**: Conectar ao PostgreSQL
5. **Customizar**: Adaptar para suas necessidades

---

## 📞 Suporte

- Problemas? Veja `docs/TROUBLESHOOTING.md`
- Dúvidas? Veja `docs/USO.md`
- Mais detalhes? Veja `docs/DOCUMENTACAO-COMPLETA.md`

**Status**: ✅ Pronto para produção!
