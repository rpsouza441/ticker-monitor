# 📚 Documentação - Índice Principal

## 🎯 Bem-vindo à Documentação do Ticker Monitor!

### 📖 Comece por Aqui

**Novo usuário?** Leia nesta ordem:

1. **[README.md](../README.md)** (5 min)
   - Visão geral do projeto
   - Quick start
   - Características principais

2. **[INSTALACAO.md](./INSTALACAO.md)** (15 min)
   - Pré-requisitos
   - Setup rápido vs manual
   - Verificação pós-instalação

3. **[USO.md](./USO.md)** (10 min)
   - Iniciar o sistema
   - Monitorar em tempo real
   - Operações comuns

4. **[DOCUMENTACAO-COMPLETA.md](./DOCUMENTACAO-COMPLETA.md)** (20 min)
   - Arquitetura completa
   - Estrutura de pastas
   - Banco de dados
   - Deployment

---

## 📑 Documentação por Tópico

### ✅ Setup & Instalação

| Documento | Tempo | Conteúdo |
|-----------|-------|----------|
| [INSTALACAO.md](./INSTALACAO.md) | 15 min | Setup rápido, pré-requisitos, verificação |
| [setup.sh](../setup.sh) | 5 min | Script de setup automatizado |

### 🚀 Operação

| Documento | Tempo | Conteúdo |
|-----------|-------|----------|
| [USO.md](./USO.md) | 10 min | Iniciar, monitorar, operações comuns |
| [Makefile](../Makefile) | 3 min | 20+ comandos úteis |

### 💻 Desenvolvimento

| Documento | Tempo | Conteúdo |
|-----------|-------|----------|
| [API.md](./API.md) | 20 min | Usar services, exemplos de código |
| [DOCUMENTACAO-COMPLETA.md](./DOCUMENTACAO-COMPLETA.md) | 30 min | Arquitetura, BD, estrutura completa |

### 🔧 Troubleshooting

| Documento | Tempo | Conteúdo |
|-----------|-------|----------|
| [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | 15 min | Problemas comuns e soluções |

### 📚 Referência Rápida

| Arquivo | Conteúdo |
|---------|----------|
| [ALEMBIC-vs-FLYWAY.md](./ALEMBIC-vs-FLYWAY.md) | Migrations: Python vs Java |
| [GUIA-DATABASE.md](./GUIA-DATABASE.md) | SQLAlchemy + Alembic |

---

## 🎓 Roteiros de Aprendizado

### Para DevOps / SRE

```
1. INSTALACAO.md
   ↓
2. docker-compose.yml (entender composição)
   ↓
3. USO.md (monitoramento)
   ↓
4. TROUBLESHOOTING.md
   ↓
5. Produção (deployment)
```

### Para Desenvolvedores Python

```
1. DOCUMENTACAO-COMPLETA.md (arquitetura)
   ↓
2. src/domain/ (models)
   ↓
3. API.md (usar services)
   ↓
4. Implementar features
   ↓
5. Testes
```

### Para DevOps + Dev (Full Stack)

```
1. README.md
   ↓
2. INSTALACAO.md
   ↓
3. DOCUMENTACAO-COMPLETA.md
   ↓
4. API.md
   ↓
5. USO.md
   ↓
6. Customizações
```

---

## 🔍 Procurando por...?

### "Como fazer [algo]"

- **...instalar?** → [INSTALACAO.md](./INSTALACAO.md)
- **...usar?** → [USO.md](./USO.md)
- **...buscar tickers?** → [API.md](./API.md#1-tickerservice)
- **...salvar em BD?** → [API.md](./API.md#2-persistenceservice)
- **...rastrear rate limit?** → [API.md](./API.md#3-ratelimitservice)
- **...entender arquitetura?** → [DOCUMENTACAO-COMPLETA.md](./DOCUMENTACAO-COMPLETA.md#arquitetura)
- **...fazer deploy?** → [DOCUMENTACAO-COMPLETA.md](./DOCUMENTACAO-COMPLETA.md#deployment)

### "Erro: [mensagem]"

- **Python not found** → [TROUBLESHOOTING.md](./TROUBLESHOOTING.md#erro-python-3-não-encontrado)
- **Docker not found** → [TROUBLESHOOTING.md](./TROUBLESHOOTING.md#erro-docker-não-found)
- **Connection refused** → [TROUBLESHOOTING.md](./TROUBLESHOOTING.md#erro-connection-refused)
- **Module not found** → [TROUBLESHOOTING.md](./TROUBLESHOOTING.md#erro-module-not-found-no-module-named-src)
- **Rate limit muito frequente** → [USO.md](./USO.md#rate-limit-muito-frequente)

---

## 📊 Estrutura de Documentação

```
docs/
├── README.md                           # Este arquivo
├── INSTALACAO.md                       # Setup e pré-requisitos
├── USO.md                              # Operação do sistema
├── API.md                              # Usar services e código
├── DOCUMENTACAO-COMPLETA.md           # Referência técnica completa
├── TROUBLESHOOTING.md                 # Erros e soluções
├── ALEMBIC-vs-FLYWAY.md               # Migrations
└── GUIA-DATABASE.md                   # SQLAlchemy + Alembic
```

---

## 🎯 Checklist de Leitura

### Obrigatório
- [ ] README.md (5 min)
- [ ] INSTALACAO.md (15 min)
- [ ] USO.md (10 min)

### Recomendado
- [ ] DOCUMENTACAO-COMPLETA.md (30 min)
- [ ] API.md (20 min)

### Conforme Necessário
- [ ] TROUBLESHOOTING.md (ao encontrar erro)
- [ ] ALEMBIC-vs-FLYWAY.md (ao trabalhar com BD)
- [ ] GUIA-DATABASE.md (ao customizar BD)

---

## 🔗 Links Rápidos

### Internos
- [Código-fonte](../src)
- [Docker Compose](../docker-compose.yml)
- [Requirements](../requirements.txt)
- [Makefile](../Makefile)
- [Setup Script](../setup.sh)

### Externos
- [Python 3.11 Docs](https://docs.python.org/3.11/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [RabbitMQ Docs](https://www.rabbitmq.com/documentation.html)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [Alembic Docs](https://alembic.sqlalchemy.org/)
- [yfinance Docs](https://github.com/ranaroussi/yfinance)
- [Docker Compose Docs](https://docs.docker.com/compose/)

---

## 💡 Dicas

### Antes de Iniciar
- Ter Python 3.11+ instalado
- Ter Docker + Docker Compose
- 10GB de espaço em disco
- Conexão internet estável

### Durante Uso
- Sempre ver logs: `docker-compose logs -f`
- Monitorar RabbitMQ: http://localhost:15672
- Usar Make para comandos: `make help`
- Consultar BD regularmente

### Troubleshooting Rápido
```bash
# Ver logs em tempo real
docker-compose logs -f

# Ver status
docker-compose ps

# Testar conexões
make health

# Reiniciar
docker-compose restart
```

---

## 🆘 Precisa de Ajuda?

### Procurar em (Nesta Ordem)
1. **TROUBLESHOOTING.md** - 90% dos problemas estão lá
2. **USO.md** - Operações comuns
3. **DOCUMENTACAO-COMPLETA.md** - Referência técnica
4. **API.md** - Exemplos de código

### Informações Úteis ao Reportar Bug
```
1. Comando executado
2. Erro exato (completo)
3. Versões: python --version, docker --version
4. Logs: docker-compose logs --tail 50
5. Estrutura: ls -la src/
```

---

## ✅ Status

- **Documentação**: Completa ✅
- **Código**: Production-ready ✅
- **Testes**: Recomendados para customizações
- **Deploy**: Pronto ✅

---

## 📝 Versão

**Documentação**: 1.0.0  
**Data**: 2025-11-25  
**Status**: Completa e Atualizada ✅

---

## 🎊 Você está pronto!

Escolha um documento acima e comece. Se tiver dúvidas, consulte TROUBLESHOOTING.md ou USO.md.

**Happy monitoring! 🚀**
