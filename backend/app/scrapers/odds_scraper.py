"""
Scraper de odds usando The Odds API.
Coleta odds das principais casas de apostas e armazena no Redis (cache)
e PostgreSQL (histórico).
"""

import httpx
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Casas de apostas que queremos monitorar
# Chaves conforme documentação da OddsAPI
BOOKMAKERS = [
    "betano",
    "bet365",
    "betsson",
    "unibet",
    "williamhill",
    "draftkings",
    "pinnacle",
]

# Ligas de futebol que vamos monitorar
SPORTS = [
    "soccer_brazil_campeonato",       # Brasileirão Série A
    "soccer_brazil_serie_b",          # Brasileirão Série B
    "soccer_epl",                     # Premier League
    "soccer_spain_la_liga",           # La Liga
    "soccer_italy_serie_a",           # Serie A italiana
    "soccer_germany_bundesliga",      # Bundesliga
    "soccer_france_ligue_one",        # Ligue 1
    "soccer_uefa_champs_league",      # Champions League
    "soccer_conmebol_copa_libertadores",  # Libertadores
]

BASE_URL = "https://api.the-odds-api.com/v4"


class OddsScraper:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_sports(self) -> list:
        """Lista todos os esportes disponíveis na API."""
        url = f"{BASE_URL}/sports"
        response = await self.client.get(url, params={"apiKey": self.api_key})
        response.raise_for_status()
        return response.json()

    async def get_odds(
        self,
        sport: str,
        regions: str = "eu,uk,us,au",
        markets: str = "h2h",  # h2h = resultado final (1x2)
        odds_format: str = "decimal",
    ) -> list:
        """
        Busca odds de um esporte específico.

        Args:
            sport: chave do esporte (ex: soccer_brazil_campeonato)
            regions: regiões das casas (eu = Europa, uk = Reino Unido)
            markets: tipo de mercado
                - h2h: resultado final (1x2)
                - spreads: handicap
                - totals: over/under
            odds_format: decimal ou american
        """
        url = f"{BASE_URL}/sports/{sport}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format,
            "bookmakers": ",".join(BOOKMAKERS),
        }

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()

            # A API retorna quantas requisições restam no header
            remaining = response.headers.get("x-requests-remaining", "?")
            used = response.headers.get("x-requests-used", "?")
            logger.info(
                f"[OddsAPI] {sport} | Requisições usadas: {used} | Restantes: {remaining}"
            )

            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"[OddsAPI] Erro HTTP {e.response.status_code} para {sport}")
            return []
        except Exception as e:
            logger.error(f"[OddsAPI] Erro inesperado para {sport}: {e}")
            return []

    async def get_all_odds(self) -> dict:
        """
        Coleta odds de todas as ligas monitoradas.
        Retorna dicionário organizado por liga.
        """
        all_odds = {}

        for sport in SPORTS:
            logger.info(f"[OddsAPI] Coletando odds: {sport}")
            odds = await self.get_odds(sport)

            if odds:
                all_odds[sport] = self._parse_odds(odds)
                logger.info(
                    f"[OddsAPI] {sport}: {len(odds)} jogos encontrados"
                )

        return all_odds

    def _parse_odds(self, raw_odds: list) -> list:
        """
        Transforma o retorno bruto da API em formato padronizado.

        Formato de saída por jogo:
        {
            "id": "abc123",
            "sport": "soccer_brazil_campeonato",
            "home_team": "Flamengo",
            "away_team": "Palmeiras",
            "commence_time": "2024-05-01T20:00:00Z",
            "bookmakers": {
                "betano": {
                    "home": 2.10,
                    "draw": 3.20,
                    "away": 3.50,
                    "last_update": "2024-05-01T18:00:00Z"
                },
                ...
            },
            "best_odds": {
                "home": {"bookmaker": "betano", "odd": 2.10},
                "draw": {"bookmaker": "bet365", "odd": 3.30},
                "away": {"bookmaker": "betsson", "odd": 3.60},
            }
        }
        """
        parsed = []

        for game in raw_odds:
            bookmakers_data = {}

            for bookmaker in game.get("bookmakers", []):
                name = bookmaker["key"]
                markets = bookmaker.get("markets", [])

                # Pega mercado h2h (resultado final)
                h2h = next(
                    (m for m in markets if m.get("key") == "h2h"), None
                )
                if not h2h:
                    continue

                outcomes = {o["name"]: o["price"] for o in h2h["outcomes"]}
                bookmakers_data[name] = {
                    "home": outcomes.get(game["home_team"]),
                    "draw": outcomes.get("Draw"),
                    "away": outcomes.get(game["away_team"]),
                    "last_update": bookmaker.get("last_update"),
                }

            if not bookmakers_data:
                continue

            # Calcula melhor odd disponível por resultado
            best_odds = self._find_best_odds(bookmakers_data)

            parsed.append({
                "id": game["id"],
                "sport_key": game["sport_key"],
                "sport_title": game["sport_title"],
                "home_team": game["home_team"],
                "away_team": game["away_team"],
                "commence_time": game["commence_time"],
                "bookmakers": bookmakers_data,
                "best_odds": best_odds,
                "collected_at": datetime.utcnow().isoformat(),
            })

        return parsed

    def _find_best_odds(self, bookmakers_data: dict) -> dict:
        """
        Encontra a melhor odd disponível para cada resultado.
        É aqui que o comparador de odds funciona.
        """
        best = {
            "home": {"bookmaker": None, "odd": 0},
            "draw": {"bookmaker": None, "odd": 0},
            "away": {"bookmaker": None, "odd": 0},
        }

        for bookmaker, odds in bookmakers_data.items():
            for outcome in ["home", "draw", "away"]:
                odd = odds.get(outcome)
                if odd and odd > best[outcome]["odd"]:
                    best[outcome] = {
                        "bookmaker": bookmaker,
                        "odd": odd,
                    }

        return best

    async def close(self):
        await self.client.aclose()


def calculate_implied_probability(odd: float) -> float:
    """
    Converte odd decimal em probabilidade implícita.
    Ex: odd 2.00 → 50% de probabilidade implícita
    """
    if odd <= 0:
        return 0
    return round(1 / odd, 4)


def calculate_value_bet(
    model_probability: float,
    odd: float,
    threshold: float = 0.05,
) -> Optional[dict]:
    """
    Identifica se existe value bet.

    Value bet existe quando a probabilidade real (calculada pelo modelo)
    é maior que a probabilidade implícita da odd.

    Ex:
        - Modelo diz 60% de chance pro Flamengo
        - Odd 2.10 implica 47.6% de chance
        - Diferença: 12.4% → VALUE BET!

    Args:
        model_probability: probabilidade estimada pelo modelo (0 a 1)
        odd: odd decimal da casa de aposta
        threshold: diferença mínima para considerar value (padrão 5%)

    Returns:
        dict com detalhes do value bet ou None se não houver
    """
    implied_prob = calculate_implied_probability(odd)
    edge = model_probability - implied_prob

    if edge >= threshold:
        return {
            "is_value": True,
            "model_probability": round(model_probability, 4),
            "implied_probability": implied_prob,
            "edge": round(edge, 4),
            "edge_percent": round(edge * 100, 2),
            "expected_value": round((model_probability * odd) - 1, 4),
        }

    return None