"""
Endpoints REST da API BetAI.

Rotas:
- GET /api/games          → lista jogos com odds
- GET /api/games/{id}     → detalhe de um jogo
- GET /api/alerts         → alertas ativos
- GET /api/bookmakers     → casas disponíveis com links de afiliado
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.models.models import Game, Odd, Alert

router = APIRouter(prefix="/api", tags=["BetAI"])

# Links de afiliado por bookmaker
AFFILIATE_LINKS = {
    "betano": settings.AFFILIATE_BETANO,
    "bet365": settings.AFFILIATE_BET365,
    "betsson": settings.AFFILIATE_BETSSON,
    "betnacional": settings.AFFILIATE_BETNACIONAL,
    "williamhill": "",
    "unibet": "",
    "pinnacle": "",
    "draftkings": "",
}


# ─── JOGOS ────────────────────────────────────────────────

@router.get("/games")
async def list_games(
    sport: Optional[str] = Query(None, description="Filtrar por liga"),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Lista jogos futuros com as melhores odds disponíveis."""
    now = datetime.now(timezone.utc)

    query = select(Game).where(Game.commence_time > now).order_by(Game.commence_time)

    if sport:
        query = query.where(Game.sport_key == sport)

    query = query.limit(limit)
    result = await db.execute(query)
    games = result.scalars().all()

    output = []
    for game in games:
        # Busca odds mais recentes
        odds_result = await db.execute(
            select(Odd)
            .where(Odd.game_id == game.id)
            .order_by(desc(Odd.collected_at))
            .limit(1)
        )
        latest_odd = odds_result.scalar_one_or_none()

        # Busca todas as odds por bookmaker
        all_odds_result = await db.execute(
            select(Odd)
            .where(Odd.game_id == game.id)
            .order_by(desc(Odd.collected_at))
            .limit(20)
        )
        all_odds = all_odds_result.scalars().all()

        bookmakers = {}
        seen = set()
        for odd in all_odds:
            if odd.bookmaker not in seen:
                seen.add(odd.bookmaker)
                bookmakers[odd.bookmaker] = {
                    "home": odd.odd_home,
                    "draw": odd.odd_draw,
                    "away": odd.odd_away,
                    "affiliate_link": AFFILIATE_LINKS.get(odd.bookmaker, ""),
                }

        game_data = {
            "id": game.id,
            "sport_key": game.sport_key,
            "sport_title": game.sport_title,
            "home_team": game.home_team,
            "away_team": game.away_team,
            "commence_time": game.commence_time.isoformat(),
            "bookmakers": bookmakers,
            "best_odds": None,
            "model_probabilities": None,
        }

        if latest_odd:
            game_data["best_odds"] = {
                "home": {
                    "odd": latest_odd.best_home,
                    "bookmaker": latest_odd.best_home_bookmaker,
                    "affiliate_link": AFFILIATE_LINKS.get(
                        latest_odd.best_home_bookmaker or "", ""
                    ),
                },
                "draw": {
                    "odd": latest_odd.best_draw,
                    "bookmaker": latest_odd.best_draw_bookmaker,
                    "affiliate_link": AFFILIATE_LINKS.get(
                        latest_odd.best_draw_bookmaker or "", ""
                    ),
                },
                "away": {
                    "odd": latest_odd.best_away,
                    "bookmaker": latest_odd.best_away_bookmaker,
                    "affiliate_link": AFFILIATE_LINKS.get(
                        latest_odd.best_away_bookmaker or "", ""
                    ),
                },
            }

        if game.prob_home:
            game_data["model_probabilities"] = {
                "home": game.prob_home,
                "draw": game.prob_draw,
                "away": game.prob_away,
                "confidence": game.model_confidence,
            }

        output.append(game_data)

    return {"games": output, "total": len(output)}


@router.get("/games/{game_id}")
async def get_game(game_id: str, db: AsyncSession = Depends(get_db)):
    """Detalhe completo de um jogo com histórico de odds."""
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()

    if not game:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Jogo não encontrado")

    # Histórico de odds
    odds_result = await db.execute(
        select(Odd)
        .where(Odd.game_id == game_id)
        .order_by(desc(Odd.collected_at))
        .limit(50)
    )
    odds = odds_result.scalars().all()

    bookmakers = {}
    for odd in odds:
        if odd.bookmaker not in bookmakers:
            bookmakers[odd.bookmaker] = {
                "home": odd.odd_home,
                "draw": odd.odd_draw,
                "away": odd.odd_away,
                "last_update": odd.collected_at.isoformat(),
                "affiliate_link": AFFILIATE_LINKS.get(odd.bookmaker, ""),
            }

    # Alertas do jogo
    alerts_result = await db.execute(
        select(Alert)
        .where(Alert.game_id == game_id, Alert.is_active == True)
        .order_by(desc(Alert.created_at))
    )
    alerts = alerts_result.scalars().all()

    return {
        "id": game.id,
        "sport_key": game.sport_key,
        "sport_title": game.sport_title,
        "home_team": game.home_team,
        "away_team": game.away_team,
        "commence_time": game.commence_time.isoformat(),
        "bookmakers": bookmakers,
        "model_probabilities": {
            "home": game.prob_home,
            "draw": game.prob_draw,
            "away": game.prob_away,
            "confidence": game.model_confidence,
        } if game.prob_home else None,
        "alerts": [
            {
                "id": a.id,
                "type": a.alert_type,
                "title": a.title,
                "description": a.description,
                "bookmaker": a.bookmaker,
                "edge": a.edge,
                "expected_value": a.expected_value,
                "outcome": a.outcome,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ],
    }


# ─── ALERTAS ──────────────────────────────────────────────

@router.get("/alerts")
async def list_alerts(
    alert_type: Optional[str] = Query(None),
    limit: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Lista alertas ativos ordenados por criação."""
    query = (
        select(Alert)
        .where(Alert.is_active == True)
        .order_by(desc(Alert.created_at))
        .limit(limit)
    )

    if alert_type:
        query = query.where(Alert.alert_type == alert_type)

    result = await db.execute(query)
    alerts = result.scalars().all()

    return {
        "alerts": [
            {
                "id": a.id,
                "game_id": a.game_id,
                "type": a.alert_type,
                "title": a.title,
                "description": a.description,
                "bookmaker": a.bookmaker,
                "edge": a.edge,
                "expected_value": a.expected_value,
                "outcome": a.outcome,
                "affiliate_link": AFFILIATE_LINKS.get(a.bookmaker or "", ""),
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ],
        "total": len(alerts),
    }


# ─── BOOKMAKERS ───────────────────────────────────────────

@router.get("/bookmakers")
async def list_bookmakers():
    """Lista casas de apostas com links de afiliado."""
    return {
        "bookmakers": [
            {
                "key": key,
                "name": key.title(),
                "affiliate_link": link,
                "has_affiliate": bool(link),
            }
            for key, link in AFFILIATE_LINKS.items()
        ]
    }


# ─── SPORTS ───────────────────────────────────────────────

@router.get("/sports")
async def list_sports(db: AsyncSession = Depends(get_db)):
    """Lista ligas disponíveis com contagem de jogos."""
    from sqlalchemy import func
    result = await db.execute(
        select(Game.sport_key, Game.sport_title, func.count(Game.id).label("games"))
        .where(Game.commence_time > datetime.now(timezone.utc))
        .group_by(Game.sport_key, Game.sport_title)
        .order_by(desc("games"))
    )
    sports = result.all()

    return {
        "sports": [
            {"key": s.sport_key, "title": s.sport_title, "games": s.games}
            for s in sports
        ]
    }