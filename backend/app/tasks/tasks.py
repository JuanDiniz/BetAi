"""
Tasks Celery — usa SQLAlchemy SÍNCRONO para evitar conflitos
de event loop com asyncpg em processos forked.
"""

import json
import logging
import os
from datetime import datetime, timezone

from celery import Celery
from dotenv import load_dotenv
from sqlalchemy import create_engine, select, desc
from sqlalchemy.orm import Session

load_dotenv()

from app.models.models import Game, Odd, Alert
from app.scrapers.odds_scraper import OddsScraper, calculate_value_bet

logger = logging.getLogger(__name__)

celery_app = Celery("betai")
celery_app.config_from_object("app.tasks.celeryconfig")

API_KEY = os.getenv("API_ODDS_KEY", "")
DATABASE_URL_SYNC = os.getenv("DATABASE_URL_SYNC", "")
VALUE_BET_THRESHOLD = float(os.getenv("VALUE_BET_THRESHOLD", "0.05"))

# Engine SÍNCRONA pra usar nas tasks
engine = create_engine(DATABASE_URL_SYNC, echo=False)


@celery_app.task(name="run_ml_predictions", bind=True, max_retries=3)
def run_ml_predictions(self):
    try:
        from app.ml.predictor import run_predictions
        run_predictions()
        logger.info("[Celery] run_ml_predictions concluído")
    except Exception as exc:
        logger.error(f"[Celery] Erro em run_ml_predictions: {exc}")
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(name="collect_odds", bind=True, max_retries=3)
def collect_odds(self):
    try:
        import asyncio
        asyncio.run(_fetch_and_save_odds())
        logger.info("[Celery] collect_odds concluído com sucesso")
    except Exception as exc:
        logger.error(f"[Celery] Erro em collect_odds: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="detect_alerts", bind=True, max_retries=3)
def detect_alerts(self):
    try:
        _run_detect_alerts()
        logger.info("[Celery] detect_alerts concluído com sucesso")
    except Exception as exc:
        logger.error(f"[Celery] Erro em detect_alerts: {exc}")
        raise self.retry(exc=exc, countdown=60)


async def _fetch_odds_from_api():
    """Busca odds da API — parte assíncrona isolada."""
    scraper = OddsScraper(api_key=API_KEY)
    try:
        return await scraper.get_all_odds()
    finally:
        await scraper.close()


def _run_detect_alerts():
    """Detecta value bets — totalmente síncrono."""
    fake_prob = 0.55

    with Session(engine) as session:
        now = datetime.now(timezone.utc)
        games = session.execute(
            select(Game)
            .where(Game.commence_time > now)
            .order_by(Game.commence_time)
            .limit(50)
        ).scalars().all()

        alerts_created = 0

        for game in games:
            latest_odd = session.execute(
                select(Odd)
                .where(Odd.game_id == game.id)
                .order_by(desc(Odd.collected_at))
                .limit(1)
            ).scalar_one_or_none()

            if not latest_odd:
                continue

            for outcome, odd_value, bookmaker in [
                ("home", latest_odd.best_home, latest_odd.best_home_bookmaker),
                ("draw", latest_odd.best_draw, latest_odd.best_draw_bookmaker),
                ("away", latest_odd.best_away, latest_odd.best_away_bookmaker),
            ]:
                if not odd_value:
                    continue

                value = calculate_value_bet(fake_prob, odd_value, VALUE_BET_THRESHOLD)
                if not value:
                    continue

                outcome_label = {
                    "home": game.home_team,
                    "draw": "Empate",
                    "away": game.away_team,
                }[outcome]

                alert = Alert(
                    game_id=game.id,
                    alert_type="value_bet",
                    title=f"Value bet — {game.home_team} x {game.away_team}",
                    description=(
                        f"{bookmaker} oferece odd {odd_value} para {outcome_label}. "
                        f"Nosso modelo estima {value['model_probability']*100:.0f}% de chance. "
                        f"Edge: +{value['edge_percent']}%"
                    ),
                    bookmaker=bookmaker,
                    edge=value["edge"],
                    expected_value=value["expected_value"],
                    outcome=outcome,
                    extra_data=json.dumps(value),
                )
                session.add(alert)
                alerts_created += 1

        session.commit()
        logger.info(f"[Celery] {alerts_created} alertas gerados")


async def _fetch_and_save_odds():
    """Busca odds e salva no banco de forma síncrona."""
    all_odds = await _fetch_odds_from_api()
    total_games = 0
    total_odds = 0

    with Session(engine) as session:
        for sport, games in all_odds.items():
            for game_data in games:
                existing = session.execute(
                    select(Game).where(Game.id == game_data["id"])
                ).scalar_one_or_none()

                if not existing:
                    game = Game(
                        id=game_data["id"],
                        sport_key=game_data["sport_key"],
                        sport_title=game_data["sport_title"],
                        home_team=game_data["home_team"],
                        away_team=game_data["away_team"],
                        commence_time=datetime.fromisoformat(
                            game_data["commence_time"].replace("Z", "+00:00")
                        ),
                    )
                    session.add(game)
                    total_games += 1

                best = game_data.get("best_odds", {})
                for bookmaker, odds_data in game_data["bookmakers"].items():
                    odd = Odd(
                        game_id=game_data["id"],
                        bookmaker=bookmaker,
                        odd_home=odds_data.get("home"),
                        odd_draw=odds_data.get("draw"),
                        odd_away=odds_data.get("away"),
                        best_home=best.get("home", {}).get("odd"),
                        best_draw=best.get("draw", {}).get("odd"),
                        best_away=best.get("away", {}).get("odd"),
                        best_home_bookmaker=best.get("home", {}).get("bookmaker"),
                        best_draw_bookmaker=best.get("draw", {}).get("bookmaker"),
                        best_away_bookmaker=best.get("away", {}).get("bookmaker"),
                    )
                    session.add(odd)
                    total_odds += 1

        session.commit()

    logger.info(f"[Celery] Salvo: {total_games} jogos novos, {total_odds} odds")