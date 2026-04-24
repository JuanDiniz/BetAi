# BetAI

Plataforma de análise de jogos de futebol com IA — modelo preditivo + comparador de odds em tempo real + sistema de alertas inteligentes.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.12 + FastAPI |
| ML | scikit-learn + XGBoost + Pandas |
| Scraping | Scrapy + Playwright |
| Tasks | Celery + Redis |
| Banco | PostgreSQL + Redis |
| Frontend | Vue 3 + Vite + Pinia |
| Infra | Railway / Render + Cloudflare |

## Estrutura do projeto

```
betai/
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints FastAPI (rotas REST + WebSocket)
│   │   ├── core/         # Config, segurança, banco de dados
│   │   ├── models/       # Models SQLAlchemy (jogos, odds, usuários)
│   │   ├── scrapers/     # Scrapers de odds por casa de aposta
│   │   ├── tasks/        # Tasks Celery (scraping, alertas, ML)
│   │   └── ml/           # Modelo preditivo e cálculo de value bets
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/             # Vue 3 + Vite
├── infra/                # Docker, configs de deploy
└── .github/workflows/    # CI/CD
```

## Como rodar localmente

### 1. Pré-requisitos
- Python 3.12+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Edite o .env com suas chaves

alembic upgrade head
uvicorn app.main:app --reload
```

### 3. Celery (tasks em background)

```bash
# Worker
celery -A app.tasks.celery worker --loglevel=info

# Scheduler (scraping periódico)
celery -A app.tasks.celery beat --loglevel=info
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

## Módulos principais

### Scraper de odds
Coleta odds das casas de aposta a cada 5 minutos via Playwright (renderiza JavaScript) e Scrapy. Armazena histórico no PostgreSQL e mantém odds atuais em cache no Redis.

### Modelo preditivo
Treinado com dados históricos de jogos europeus. Features: forma recente, confrontos diretos, gols marcados/sofridos, home/away advantage, posição na tabela. Output: probabilidade para vitória casa / empate / vitória visitante.

### Value bet engine
Compara probabilidade do modelo com a odd implícita de cada casa. Quando a diferença supera o threshold configurado (`VALUE_BET_THRESHOLD`), gera um alerta.

### Smart Alerts
Sistema de alertas em tempo real via WebSocket. Tipos: odd promocional, value bet, odd caindo, código promocional, cashback disponível.

## Variáveis de ambiente

Veja `.env.example` para a lista completa.

## Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/minha-feature`)
3. Commit suas mudanças (`git commit -m 'feat: minha feature'`)
4. Push pra branch (`git push origin feature/minha-feature`)
5. Abra um Pull Request

## Licença

MIT
