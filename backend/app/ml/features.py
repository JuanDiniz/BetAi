"""
Engenharia de features para o modelo de ML.

Features calculadas por jogo:
- Forma recente (últimos N jogos) — pontos, gols, saldo
- Desempenho em casa vs fora
- Head-to-head histórico
- Média ponderada por recência (jogos mais recentes valem mais)
- Posição relativa na "tabela corrente"
"""

import numpy as np
import pandas as pd
from typing import Optional


def points_from_result(result: str, is_home: bool) -> int:
    """Converte resultado em pontos para um time."""
    if result == "H":
        return 3 if is_home else 0
    elif result == "A":
        return 0 if is_home else 3
    elif result == "D":
        return 1
    return 0


def get_team_form(
    df: pd.DataFrame,
    team: str,
    before_date: pd.Timestamp,
    n_games: int = 5,
    home_only: bool = False,
    away_only: bool = False,
) -> dict:
    """
    Calcula forma recente de um time antes de uma data específica.

    Returns dict com métricas de forma.
    """
    # Filtra jogos do time antes da data
    home_games = df[(df["HomeTeam"] == team) & (df["Date"] < before_date)].copy()
    away_games = df[(df["AwayTeam"] == team) & (df["Date"] < before_date)].copy()

    if home_only:
        games = home_games.tail(n_games)
    elif away_only:
        games = away_games.tail(n_games)
    else:
        # Combina casa e fora, ordena por data
        home_games["is_home"] = True
        away_games["is_home"] = False
        games = pd.concat([home_games, away_games]).sort_values("Date").tail(n_games)

    if games.empty:
        return _empty_form()

    pts_list, gf_list, ga_list = [], [], []

    for _, row in games.iterrows():
        is_home = row.get("is_home", row["HomeTeam"] == team)
        pts = points_from_result(row["FTR"], is_home)
        pts_list.append(pts)

        if is_home:
            gf_list.append(row["FTHG"])
            ga_list.append(row["FTAG"])
        else:
            gf_list.append(row["FTAG"])
            ga_list.append(row["FTHG"])

    n = len(pts_list)

    # Pesos exponenciais (jogos mais recentes valem mais)
    weights = np.exp(np.linspace(-1, 0, n))
    weights /= weights.sum()

    return {
        "form_pts": float(np.average(pts_list, weights=weights)),
        "form_pts_raw": float(np.mean(pts_list)),
        "form_gf": float(np.average(gf_list, weights=weights)),
        "form_ga": float(np.average(ga_list, weights=weights)),
        "form_gd": float(np.average(gf_list, weights=weights)) - float(np.average(ga_list, weights=weights)),
        "form_wins": sum(1 for p in pts_list if p == 3) / n,
        "form_draws": sum(1 for p in pts_list if p == 1) / n,
        "form_losses": sum(1 for p in pts_list if p == 0) / n,
        "form_games": n,
    }


def _empty_form() -> dict:
    return {
        "form_pts": 1.0,  # média neutra
        "form_pts_raw": 1.0,
        "form_gf": 1.2,
        "form_ga": 1.2,
        "form_gd": 0.0,
        "form_wins": 0.33,
        "form_draws": 0.33,
        "form_losses": 0.33,
        "form_games": 0,
    }


def get_h2h(
    df: pd.DataFrame,
    home_team: str,
    away_team: str,
    before_date: pd.Timestamp,
    n_games: int = 5,
) -> dict:
    """Histórico de confrontos diretos entre dois times."""
    h2h = df[
        (
            ((df["HomeTeam"] == home_team) & (df["AwayTeam"] == away_team)) |
            ((df["HomeTeam"] == away_team) & (df["AwayTeam"] == home_team))
        ) & (df["Date"] < before_date)
    ].tail(n_games)

    if h2h.empty:
        return {"h2h_home_wins": 0.4, "h2h_draws": 0.25, "h2h_away_wins": 0.35, "h2h_games": 0}

    home_wins, draws, away_wins = 0, 0, 0
    for _, row in h2h.iterrows():
        if row["HomeTeam"] == home_team:
            if row["FTR"] == "H": home_wins += 1
            elif row["FTR"] == "D": draws += 1
            else: away_wins += 1
        else:
            if row["FTR"] == "A": home_wins += 1
            elif row["FTR"] == "D": draws += 1
            else: away_wins += 1

    n = len(h2h)
    return {
        "h2h_home_wins": home_wins / n,
        "h2h_draws": draws / n,
        "h2h_away_wins": away_wins / n,
        "h2h_games": n,
    }


def get_season_stats(
    df: pd.DataFrame,
    team: str,
    before_date: pd.Timestamp,
) -> dict:
    """Estatísticas acumuladas na temporada corrente."""
    season_start = before_date - pd.DateOffset(months=10)

    home = df[
        (df["HomeTeam"] == team) &
        (df["Date"] >= season_start) &
        (df["Date"] < before_date)
    ]
    away = df[
        (df["AwayTeam"] == team) &
        (df["Date"] >= season_start) &
        (df["Date"] < before_date)
    ]

    total_games = len(home) + len(away)
    if total_games == 0:
        return {
            "season_pts_per_game": 1.0,
            "season_gf_per_game": 1.2,
            "season_ga_per_game": 1.2,
            "season_home_pts": 1.0,
            "season_away_pts": 1.0,
        }

    home_pts = sum(3 if r == "H" else (1 if r == "D" else 0) for r in home["FTR"])
    away_pts = sum(3 if r == "A" else (1 if r == "D" else 0) for r in away["FTR"])
    total_pts = home_pts + away_pts

    total_gf = home["FTHG"].sum() + away["FTAG"].sum()
    total_ga = home["FTAG"].sum() + away["FTHG"].sum()

    return {
        "season_pts_per_game": total_pts / total_games,
        "season_gf_per_game": total_gf / total_games,
        "season_ga_per_game": total_ga / total_games,
        "season_home_pts": (home_pts / len(home)) if len(home) > 0 else 1.0,
        "season_away_pts": (away_pts / len(away)) if len(away) > 0 else 1.0,
    }


def build_features_for_game(
    df: pd.DataFrame,
    home_team: str,
    away_team: str,
    date: pd.Timestamp,
    league: str,
) -> Optional[dict]:
    """
    Constrói o vetor de features completo para um jogo.
    Retorna None se não houver dados suficientes.
    """
    # Forma geral (últimos 5 jogos)
    home_form = get_team_form(df, home_team, date, n_games=5)
    away_form = get_team_form(df, away_team, date, n_games=5)

    # Forma em casa/fora específica
    home_form_home = get_team_form(df, home_team, date, n_games=5, home_only=True)
    away_form_away = get_team_form(df, away_team, date, n_games=5, away_only=True)

    # Head-to-head
    h2h = get_h2h(df, home_team, away_team, date)

    # Stats da temporada
    home_season = get_season_stats(df, home_team, date)
    away_season = get_season_stats(df, away_team, date)

    # Verifica dados mínimos
    if home_form["form_games"] < 2 or away_form["form_games"] < 2:
        return None

    features = {
        # Forma geral do time da casa
        "home_form_pts": home_form["form_pts"],
        "home_form_gf": home_form["form_gf"],
        "home_form_ga": home_form["form_ga"],
        "home_form_gd": home_form["form_gd"],
        "home_form_wins": home_form["form_wins"],
        "home_form_losses": home_form["form_losses"],

        # Forma geral do visitante
        "away_form_pts": away_form["form_pts"],
        "away_form_gf": away_form["form_gf"],
        "away_form_ga": away_form["form_ga"],
        "away_form_gd": away_form["form_gd"],
        "away_form_wins": away_form["form_wins"],
        "away_form_losses": away_form["form_losses"],

        # Forma específica (casa jogando em casa, fora jogando fora)
        "home_form_home_pts": home_form_home["form_pts"],
        "home_form_home_gf": home_form_home["form_gf"],
        "home_form_home_ga": home_form_home["form_ga"],
        "away_form_away_pts": away_form_away["form_pts"],
        "away_form_away_gf": away_form_away["form_gf"],
        "away_form_away_ga": away_form_away["form_ga"],

        # Diferenças entre os times
        "pts_diff": home_form["form_pts"] - away_form["form_pts"],
        "gd_diff": home_form["form_gd"] - away_form["form_gd"],
        "gf_diff": home_form["form_gf"] - away_form["form_gf"],

        # H2H
        "h2h_home_wins": h2h["h2h_home_wins"],
        "h2h_draws": h2h["h2h_draws"],
        "h2h_away_wins": h2h["h2h_away_wins"],
        "h2h_games": h2h["h2h_games"],

        # Season stats
        "home_season_pts": home_season["season_pts_per_game"],
        "home_season_gf": home_season["season_gf_per_game"],
        "home_season_ga": home_season["season_ga_per_game"],
        "home_season_home_pts": home_season["season_home_pts"],
        "away_season_pts": away_season["season_pts_per_game"],
        "away_season_gf": away_season["season_gf_per_game"],
        "away_season_ga": away_season["season_ga_per_game"],
        "away_season_away_pts": away_season["season_away_pts"],

        # Vantagem de jogar em casa (feature importante)
        "home_advantage": 1.0,
    }

    return features


def build_training_dataset(df: pd.DataFrame) -> tuple:
    """
    Constrói dataset completo para treino.

    Returns:
        X: DataFrame de features
        y: Series com labels (0=home, 1=draw, 2=away)
    """
    rows = []
    labels = []

    label_map = {"H": 0, "D": 1, "A": 2}

    for i, row in df.iterrows():
        if i % 500 == 0:
            print(f"  Processando jogo {i}/{len(df)}...")

        features = build_features_for_game(
            df,
            home_team=row["HomeTeam"],
            away_team=row["AwayTeam"],
            date=row["Date"],
            league=row.get("league", "unknown"),
        )

        if features is None:
            continue

        rows.append(features)
        labels.append(label_map.get(row["FTR"], -1))

    X = pd.DataFrame(rows)
    y = pd.Series(labels)

    # Remove labels inválidos
    valid = y >= 0
    X = X[valid].reset_index(drop=True)
    y = y[valid].reset_index(drop=True)

    print(f"\nDataset: {len(X)} jogos com features válidas")
    print(f"Distribuição: Home={sum(y==0)} ({sum(y==0)/len(y)*100:.1f}%) "
          f"Draw={sum(y==1)} ({sum(y==1)/len(y)*100:.1f}%) "
          f"Away={sum(y==2)} ({sum(y==2)/len(y)*100:.1f}%)")

    return X, y