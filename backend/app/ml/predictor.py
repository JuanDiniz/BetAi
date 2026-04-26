"""
Predictor — integra o modelo de ML com o banco de dados.

Responsabilidades:
1. Normalizar nomes de times entre football-data e OddsAPI
2. Buscar features para jogos futuros
3. Rodar o modelo e salvar probabilidades no banco
4. Gerar alertas APENAS para casas com link de afiliado
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine, select, desc
from sqlalchemy.orm import Session

from app.models.models import Game, Odd, Alert
from app.ml.features import build_features_for_game
from app.ml.model import load_model, predict_probabilities
from app.ml.data_collector import load_all_leagues

logger = logging.getLogger(__name__)

DATABASE_URL_SYNC = os.getenv("DATABASE_URL_SYNC", "")

# Casas que TEMOS link de afiliado — só geramos alertas para essas
AFFILIATE_BOOKMAKERS = {
    "betano", "bet365", "betsson", "betnacional", "f12bet", "kto"
}

# Normalização de nomes de times
# football-data usa nomes diferentes da OddsAPI
TEAM_NAME_MAP = {
    # Brasil
    "Flamengo": "Flamengo",
    "Palmeiras": "Palmeiras",
    "Atletico MG": "Atletico Mineiro",
    "Atletico-MG": "Atletico Mineiro",
    "Atletico Mineiro": "Atletico Mineiro",
    "Fluminense": "Fluminense",
    "Corinthians": "Corinthians",
    "Sao Paulo": "Sao Paulo",
    "Internacional": "Internacional",
    "Botafogo": "Botafogo",
    "Gremio": "Grêmio",
    "Cruzeiro": "Cruzeiro",
    "Bragantino": "Bragantino-SP",
    "RB Bragantino": "Bragantino-SP",
    "Bahia": "Bahia",
    "Vasco": "Vasco da Gama",
    "Vasco da Gama": "Vasco da Gama",
    "Athletico PR": "Atletico Paranaense",
    "Athletico-PR": "Atletico Paranaense",
    "Santos": "Santos",
    # Premier League
    "Man City": "Manchester City",
    "Man United": "Manchester United",
    "Spurs": "Tottenham Hotspur",
    "Tottenham": "Tottenham Hotspur",
    "Newcastle": "Newcastle United",
    "Brighton": "Brighton",
    "Wolves": "Wolverhampton Wanderers",
    "West Ham": "West Ham United",
    "Leicester": "Leicester City",
    "Aston Villa": "Aston Villa",
    # La Liga
    "Atletico Madrid": "Atlético Madrid",
    "Atletico": "Atlético Madrid",
    "Celta": "Celta Vigo",
    "Ath Bilbao": "Athletic Bilbao",
    "Ath Madrid": "Atlético Madrid",
    # Serie A
    "AC Milan": "AC Milan",
    "Inter": "Inter Milan",
    "Internazionale": "Inter Milan",
    "Juventus": "Juventus",
    "Napoli": "Napoli",
    "Roma": "AS Roma",
    "Lazio": "Lazio",
    # Bundesliga
    "Bayern Munich": "Bayern Munich",
    "Dortmund": "Borussia Dortmund",
    "Leverkusen": "Bayer Leverkusen",
    "Ein Frankfurt": "Eintracht Frankfurt",
    "Freiburg": "SC Freiburg",
    # Ligue 1
    "Paris SG": "Paris Saint Germain",
    "PSG": "Paris Saint Germain",
    "Monaco": "AS Monaco",
    "Marseille": "Marseille",
    "Lyon": "Lyon",
}


def normalize_team_name(name: str) -> str:
    """Normaliza nome de time para comparação."""
    return TEAM_NAME_MAP.get(name, name)


def find_historical_team_name(odds_name: str, historical_names: set) -> str:
    """
    Tenta encontrar o nome histórico correspondente ao nome da OddsAPI.
    Usa correspondência por substring se exato não encontrar.
    """
    # Tenta direto
    if odds_name in historical_names:
        return odds_name

    # Tenta pelo mapa reverso
    normalized = normalize_team_name(odds_name)
    if normalized in historical_names:
        return normalized

    # Tenta substring
    odds_lower = odds_name.lower()
    for hist_name in historical_names:
        if odds_lower in hist_name.lower() or hist_name.lower() in odds_lower:
            return hist_name

    # Retorna o nome original se não encontrar
    return odds_name


def run_predictions():
    """
    Pipeline completo:
    1. Carrega dados históricos
    2. Carrega modelo
    3. Para cada jogo futuro no banco, gera probabilidades
    4. Salva no banco e gera alertas apenas para casas afiliadas
    """
    logger.info("[ML] Iniciando pipeline de predições...")

    # Carrega dados históricos
    try:
        historical_df = load_all_leagues()
        if historical_df.empty:
            logger.error("[ML] Sem dados históricos. Execute download primeiro.")
            return
        historical_names = set(historical_df["HomeTeam"].unique()) | set(historical_df["AwayTeam"].unique())
        logger.info(f"[ML] {len(historical_df)} jogos históricos carregados")
    except Exception as e:
        logger.error(f"[ML] Erro ao carregar dados históricos: {e}")
        return

    # Carrega modelo
    try:
        model, feature_names = load_model()
        logger.info("[ML] Modelo carregado com sucesso")
    except FileNotFoundError:
        logger.error("[ML] Modelo não treinado ainda. Execute o treinamento primeiro.")
        return

    engine = create_engine(DATABASE_URL_SYNC, echo=False)

    with Session(engine) as session:
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=7)  # jogos dos próximos 7 dias

        games = session.execute(
            select(Game)
            .where(Game.commence_time > now)
            .where(Game.commence_time < cutoff)
            .order_by(Game.commence_time)
        ).scalars().all()

        logger.info(f"[ML] {len(games)} jogos para prever")
        predictions_made = 0
        alerts_created = 0

        for game in games:
            try:
                # Normaliza nomes
                home = find_historical_team_name(game.home_team, historical_names)
                away = find_historical_team_name(game.away_team, historical_names)
                date = game.commence_time.replace(tzinfo=None)

                # Constrói features
                features = build_features_for_game(
                    historical_df, home, away,
                    pd.Timestamp(date), game.sport_key
                )

                if features is None:
                    logger.debug(f"[ML] Sem features para {game.home_team} x {game.away_team}")
                    continue

                # Prediz probabilidades
                probs = predict_probabilities(model, feature_names, features)

                # Salva probabilidades no banco
                game.prob_home = probs["prob_home"]
                game.prob_draw = probs["prob_draw"]
                game.prob_away = probs["prob_away"]
                game.model_confidence = max(probs.values())
                predictions_made += 1

                # Busca odds mais recentes
                latest_odd = session.execute(
                    select(Odd)
                    .where(Odd.game_id == game.id)
                    .order_by(desc(Odd.collected_at))
                    .limit(1)
                ).scalar_one_or_none()

                if not latest_odd:
                    continue

                # Gera alertas APENAS para casas com afiliado
                all_odds = session.execute(
                    select(Odd)
                    .where(Odd.game_id == game.id)
                    .order_by(desc(Odd.collected_at))
                    .limit(20)
                ).scalars().all()

                bookmaker_odds = {}
                seen = set()
                for odd in all_odds:
                    if odd.bookmaker not in seen:
                        seen.add(odd.bookmaker)
                        bookmaker_odds[odd.bookmaker] = odd

                for bookmaker, odd_row in bookmaker_odds.items():
                    # FILTRO CRÍTICO — só alerta para casas afiliadas
                    if bookmaker.lower() not in AFFILIATE_BOOKMAKERS:
                        continue

                    for outcome, model_prob, odd_val, outcome_label in [
                        ("home", probs["prob_home"], odd_row.odd_home, game.home_team),
                        ("draw", probs["prob_draw"], odd_row.odd_draw, "Empate"),
                        ("away", probs["prob_away"], odd_row.odd_away, game.away_team),
                    ]:
                        if not odd_val or odd_val <= 1:
                            continue

                        implied_prob = 1 / odd_val
                        edge = model_prob - implied_prob

                        if edge >= 0.05:  # 5% de edge mínimo
                            # Verifica se já existe alerta similar recente
                            existing = session.execute(
                                select(Alert).where(
                                    Alert.game_id == game.id,
                                    Alert.bookmaker == bookmaker,
                                    Alert.outcome == outcome,
                                    Alert.alert_type == "value_bet",
                                )
                            ).scalar_one_or_none()

                            if existing:
                                # Atualiza edge
                                existing.edge = round(edge, 4)
                                existing.expected_value = round((model_prob * odd_val) - 1, 4)
                            else:
                                alert = Alert(
                                    game_id=game.id,
                                    alert_type="value_bet",
                                    title=f"Value bet — {game.home_team} x {game.away_team}",
                                    description=(
                                        f"{bookmaker.title()} oferece odd {odd_val} para {outcome_label}. "
                                        f"Modelo estima {model_prob*100:.0f}% de chance "
                                        f"(casa implica {implied_prob*100:.0f}%). "
                                        f"Edge: +{edge*100:.1f}%"
                                    ),
                                    bookmaker=bookmaker,
                                    edge=round(edge, 4),
                                    expected_value=round((model_prob * odd_val) - 1, 4),
                                    outcome=outcome,
                                    extra_data=None,
                                )
                                session.add(alert)
                                alerts_created += 1

            except Exception as e:
                logger.error(f"[ML] Erro no jogo {game.home_team} x {game.away_team}: {e}")
                continue

        session.commit()
        logger.info(f"[ML] {predictions_made} predições feitas, {alerts_created} alertas criados")


# Import necessário no predictor
import pandas as pd