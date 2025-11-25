.PHONY: help install up down logs shell test clean migrate

help:
	@echo "📋 Ticker Monitor - Comandos úteis"
	@echo ""
	@echo "🚀 Desenvolvimento:"
	@echo "  make install        - Instalar dependências"
	@echo "  make up             - Subir stack Docker"
	@echo "  make down           - Derrubar stack"
	@echo "  make logs           - Ver logs em tempo real"
	@echo "  make shell          - Entrar no shell Python"
	@echo ""
	@echo "🧪 Testes:"
	@echo "  make test           - Rodar testes"
	@echo "  make test-cov       - Testes com cobertura"
	@echo ""
	@echo "🗄️ BD:"
	@echo "  make migrate        - Executar migrations Alembic"
	@echo "  make migrate-new    - Gerar nova migration"
	@echo "  make db-shell       - Entrar no PostgreSQL"
	@echo ""
	@echo "🧹 Limpeza:"
	@echo "  make clean          - Remover arquivos temp"
	@echo "  make clean-all      - Remover tudo (cuidado!)"

install:
	@echo "📦 Instalando dependências..."
	pip install -r requirements.txt

up:
	@echo "🚀 Subindo Docker Compose..."
	docker-compose up -d
	@echo ""
	@echo "✓ Stack iniciado!"
	@echo "📊 RabbitMQ Management: http://localhost:15672 (guest:guest)"
	@echo "📝 Logs: make logs"

down:
	@echo "🛑 Derrubando stack..."
	docker-compose down

logs:
	@echo "📝 Logs em tempo real (Ctrl+C para parar)..."
	docker-compose logs -f ticker-monitor

shell-python:
	@echo "🐍 Entrando no shell Python..."
	docker exec -it ticker-monitor-app python

shell-postgres:
	@echo "🗄️ Conectando ao PostgreSQL..."
	docker exec -it ticker-postgres psql -U ticker_user -d ticker_db

shell-rabbit:
	@echo "🐰 Abrindo RabbitMQ Management..."
	@python -c "import webbrowser; webbrowser.open('http://localhost:15672')"

test:
	@echo "🧪 Rodando testes..."
	pytest tests/ -v

test-cov:
	@echo "🧪 Rodando testes com cobertura..."
	pytest tests/ --cov=src/ --cov-report=html
	@echo "📊 Cobertura: htmlcov/index.html"

migrate:
	@echo "🗄️ Executando migrations..."
	alembic upgrade head

migrate-new:
	@echo "🗄️ Gerando nova migration..."
	@read -p "Nome da migration: " name; \
	alembic revision --autogenerate -m "$$name"

db-shell:
	@echo "🗄️ Acessando PostgreSQL..."
	docker exec -it ticker-postgres psql -U ticker_user -d ticker_db

clean:
	@echo "🧹 Limpando arquivos temporários..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info
	@echo "✓ Limpeza concluída"

clean-all: clean
	@echo "💣 Removendo TUDO (docker volumes, BD, etc)..."
	docker-compose down -v
	rm -rf logs/*
	rm -f .env
	@echo "✓ Limpeza completa"

ps:
	@echo "📊 Status dos containers..."
	docker-compose ps

restart:
	@echo "🔄 Reiniciando stack..."
	docker-compose restart

format:
	@echo "✨ Formatando código..."
	black src/ tests/
	isort src/ tests/

lint:
	@echo "🔍 Verificando código..."
	pylint src/

health:
	@echo "🏥 Verificando saúde do sistema..."
	@python -c "from src.main import health_check; import json; print(json.dumps(health_check(), indent=2))"

init:
	@echo "⚙️ Inicializando sistema..."
	@python src/main.py init

version:
	@echo "Version: 1.0.0"
