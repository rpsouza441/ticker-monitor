# 🗄️ Alembic vs Flyway: Guia Comparativo

## ✅ Sim, Python tem (e melhor que Flyway!)

Alembic é o equivalente Python ao Flyway. Mas tem **vantagens**:

---

## 📊 Comparação Detalhada

### 1. **Auto-geração de Migrations** ⭐ ALEMBIC VENCE

**Flyway (Java):**
```bash
# Você escreve o SQL manualmente
V001__create_users_table.sql
V002__add_email_to_users.sql
```

**Alembic (Python):**
```bash
# Auto-detecta mudanças nos modelos ORM
alembic revision --autogenerate -m "add email to users"
# Gera o arquivo automaticamente!
```

✨ **Alembic detecta:**
- Novas colunas
- Mudanças de tipo
- Índices
- Foreign keys
- Constraints

---

### 2. **Sintaxe das Migrations**

**Flyway (SQL puro - simples mas verboso):**
```sql
-- V001__initial.sql
CREATE TABLE tickers (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(20) UNIQUE NOT NULL
);

CREATE INDEX ix_ticker_symbol ON tickers(symbol);
```

**Alembic (Python - programável):**
```python
# migrations/versions/001_initial.py
def upgrade() -> None:
    op.create_table(
        'tickers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(20), unique=True, nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ticker_symbol', 'tickers', ['symbol'])

def downgrade() -> None:
    op.drop_index('ix_ticker_symbol')
    op.drop_table('tickers')
```

✨ **Vantagem Alembic:**
- Downgrade automático (rollback)
- Lógica condicional em migrations
- Integração com SQLAlchemy

---

### 3. **Versioning & Tracking**

| Aspecto | Flyway | Alembic |
|---------|--------|---------|
| **Arquivo de Versão** | `flyway_schema_history` | `alembic_version` |
| **Formato** | Sequencial (V001, V002) | Hash SHA-256 |
| **Rollback** | Limitado (requer reversão manual) | Completo (automático) |
| **Branching** | Não suporta bem | Suporta bem |

---

## 🚀 Como Usar Alembic

### Setup (Uma única vez)

```bash
# 1. Inicializar Alembic
pip install alembic
alembic init migrations

# 2. Configurar database.py com os modelos
# (já está pronto no projeto)
```

### Workflow de Desenvolvimento

```bash
# ════════════════════════════════════════════
# CENÁRIO: Adicionar coluna "description" em tickers
# ════════════════════════════════════════════

# 1. Modificar seu modelo ORM
# ticker_data.py
class TickerModel(Base):
    __tablename__ = "tickers"
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, nullable=False)
    description = Column(String(500), nullable=True)  # ← NOVO

# 2. Auto-gerar migration
alembic revision --autogenerate -m "add description to tickers"

# 3. Verificar arquivo gerado (migrations/versions/002_add_description_to_tickers.py)
# Alembic criou automaticamente!

# 4. Testar
alembic upgrade head    # Aplicar migration
alembic downgrade -1    # Reverter 1 migration

# 5. Commit
git add migrations/versions/002_add_description_to_tickers.py
git commit -m "feat: add description field to tickers"
```

---

## 📋 Comandos Alembic (equivalentes ao Flyway)

### Flyway vs Alembic

| Flyway | Alembic | O que faz |
|--------|---------|----------|
| `flyway migrate` | `alembic upgrade head` | Aplicar todas as migrations |
| `flyway clean` | `alembic downgrade base` | Remover tudo (cuidado!) |
| `flyway info` | `alembic current` | Ver versão atual |
| `flyway validate` | (não tem equivalente) | Não precisa |
| `flyway undo` | `alembic downgrade -1` | Reverter 1 step |

---

## 🔄 Exemplos Práticos

### Exemplo 1: Criar Nova Tabela

**Flyway (V003__create_alerts_table.sql):**
```sql
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    ticker_id INT NOT NULL REFERENCES tickers(id),
    price_threshold DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Alembic (automático):**
```bash
# 1. Adicionar modelo
class AlertModel(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    ticker_id = Column(Integer, ForeignKey('tickers.id'), nullable=False)
    price_threshold = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

# 2. Gerar migration
alembic revision --autogenerate -m "create alerts table"

# 3. Pronto! (arquivo criado em migrations/versions/)
```

### Exemplo 2: Adicionar Índice

**Flyway:**
```sql
-- V004__add_indexes.sql
CREATE INDEX ix_alerts_ticker_id ON alerts(ticker_id);
CREATE INDEX ix_ticker_prices_date ON ticker_prices(updated_at DESC);
```

**Alembic:**
```bash
# 1. Modificar modelo (adicionar Index)
from sqlalchemy import Index

class TickerPriceModel(Base):
    __tablename__ = "ticker_prices"
    __table_args__ = (
        Index('ix_ticker_prices_date', 'updated_at', postgresql_using='btree'),
    )

# 2. Auto-gerar
alembic revision --autogenerate -m "add indexes"
```

### Exemplo 3: Remover Coluna

**Flyway:**
```sql
-- V005__remove_deprecated_field.sql
ALTER TABLE tickers DROP COLUMN deprecated_field;
```

**Alembic:**
```bash
# 1. Remover do modelo ORM
# (deletar a coluna da classe)

# 2. Auto-gerar
alembic revision --autogenerate -m "remove deprecated field"

# 3. Alembic cria automaticamente o downgrade!
```

---

## 🎯 Workflow Completo no Projeto

### 1️⃣ **Inicializar (primeira vez)**

```bash
# Já configurado em database.py:
db = Database()
db.initialize()  # Executa migrations automaticamente
```

### 2️⃣ **Durante Desenvolvimento**

```bash
# Mudar modelo em src/domain/ticker_data.py
class TickerModel(Base):
    # adicione campo aqui

# Gerar migration automaticamente
alembic revision --autogenerate -m "descriptive message"

# Testar migration
alembic upgrade head

# Testar rollback
alembic downgrade -1

# Tudo OK? Commit
git add migrations/versions/
git commit -m "migration: ..."
```

### 3️⃣ **Em Produção**

```bash
# Docker Compose executa automaticamente:
# src/infrastructure/database.py → _run_migrations()
# que chama: alembic upgrade head

# Checklist:
docker-compose up -d
docker-compose logs ticker-monitor  # Ver migrations rodando
docker exec -it ticker-postgres psql -U ticker_user -d ticker_db
\dt  # Ver tabelas criadas
```

---

## ⚠️ Boas Práticas

### ✅ Faça

```python
# Ser descritivo em migrations
alembic revision --autogenerate -m "add price_alert_threshold to tickers"

# Sempre fazer upgrade/downgrade em dev
alembic upgrade head
alembic downgrade -1

# Commitar migrations com código
git add migrations/versions/
```

### ❌ Não Faça

```python
# Não aplicar SQL raw sem migration
# (vai quebrar o rollback)

# Não editar migrations já deployadas
# (usa o workflow: novo modelo → nova migration)

# Não esquecer de commitar migrations
# (dev faz upgrade, prod não tem arquivo)
```

---

## 🔧 Troubleshooting

### Problema: "Target database is not up to date"

```bash
# Solução: Sincronizar
alembic upgrade head

# Ver status atual
alembic current

# Ver histórico
alembic history --rev-range 001:
```

### Problema: Conflito de migrations (2 devs criaram ao mesmo tempo)

```bash
# 1. Ver arquivo de conflito
ls migrations/versions/

# 2. Editar manualmente (combinar mudanças)

# 3. Atualizar down_revision do segundo arquivo
# migration_2.py
down_revision = '002_outro_dev'  # (era 001)

# 4. Testar
alembic upgrade head
```

### Problema: Preciso fazer downgrade em produção

```bash
# 1. Identificar versão anterior
alembic history

# 2. Downgrade
alembic downgrade 001_initial

# 3. Revert código
git revert <commit-hash>

# 4. Re-deploy
```

---

## 📊 Resumo: Alembic é Melhor Para Python

| Critério | Flyway | Alembic |
|----------|--------|---------|
| **Auto-geração** | ❌ | ✅ |
| **Rollback** | ⚠️ Limitado | ✅ Completo |
| **Integração ORM** | ❌ | ✅ |
| **Curva aprendizado** | ✅ Simples | ⚠️ Médio |
| **Para Python** | ❌ Não é Python | ✅ Nativo |
| **Comunidade** | ✅ Enorme | ✅ Grande |

---

## 🎁 Próximas Migrations (Exemplos)

Você pode usar assim daqui em diante:

```bash
# Adicionar nova funcionalidade
alembic revision --autogenerate -m "add watchlist support"
alembic upgrade head
git add migrations/versions/

# Remover campo deprecado
alembic revision --autogenerate -m "remove old_field"
alembic upgrade head
git add migrations/versions/

# Adicionar índice novo para performance
alembic revision --autogenerate -m "add index for performance"
alembic upgrade head
git add migrations/versions/
```

---

## 🚀 Conclusão

Alembic é **superior ao Flyway** em vários aspectos:
- ✅ Auto-geração de migrations
- ✅ Rollback completo
- ✅ Integração com SQLAlchemy
- ✅ Nativo em Python
- ✅ Menos boilerplate

**Use Alembic para suas migrations!** 🎉
