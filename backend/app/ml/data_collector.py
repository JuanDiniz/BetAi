"""
Coletor de dados históricos de futebol.
Fonte: football-data.co.uk — CSVs gratuitos com resultados de partidas.
"""

import time
import logging
import pandas as pd
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

LEAGUE_URLS = {
    "soccer_epl": [
        ("2324", "https://www.football-data.co.uk/mmz4281/2324/E0.csv"),
        ("2223", "https://www.football-data.co.uk/mmz4281/2223/E0.csv"),
        ("2122", "https://www.football-data.co.uk/mmz4281/2122/E0.csv"),
        ("2021", "https://www.football-data.co.uk/mmz4281/2021/E0.csv"),
        ("1920", "https://www.football-data.co.uk/mmz4281/1920/E0.csv"),
    ],
    "soccer_spain_la_liga": [
        ("2324", "https://www.football-data.co.uk/mmz4281/2324/SP1.csv"),
        ("2223", "https://www.football-data.co.uk/mmz4281/2223/SP1.csv"),
        ("2122", "https://www.football-data.co.uk/mmz4281/2122/SP1.csv"),
        ("2021", "https://www.football-data.co.uk/mmz4281/2021/SP1.csv"),
        ("1920", "https://www.football-data.co.uk/mmz4281/1920/SP1.csv"),
    ],
    "soccer_italy_serie_a": [
        ("2324", "https://www.football-data.co.uk/mmz4281/2324/I1.csv"),
        ("2223", "https://www.football-data.co.uk/mmz4281/2223/I1.csv"),
        ("2122", "https://www.football-data.co.uk/mmz4281/2122/I1.csv"),
        ("2021", "https://www.football-data.co.uk/mmz4281/2021/I1.csv"),
        ("1920", "https://www.football-data.co.uk/mmz4281/1920/I1.csv"),
    ],
    "soccer_germany_bundesliga": [
        ("2324", "https://www.football-data.co.uk/mmz4281/2324/D1.csv"),
        ("2223", "https://www.football-data.co.uk/mmz4281/2223/D1.csv"),
        ("2122", "https://www.football-data.co.uk/mmz4281/2122/D1.csv"),
        ("2021", "https://www.football-data.co.uk/mmz4281/2021/D1.csv"),
        ("1920", "https://www.football-data.co.uk/mmz4281/1920/D1.csv"),
    ],
    "soccer_france_ligue_one": [
        ("2324", "https://www.football-data.co.uk/mmz4281/2324/F1.csv"),
        ("2223", "https://www.football-data.co.uk/mmz4281/2223/F1.csv"),
        ("2122", "https://www.football-data.co.uk/mmz4281/2122/F1.csv"),
        ("2021", "https://www.football-data.co.uk/mmz4281/2021/F1.csv"),
        ("1920", "https://www.football-data.co.uk/mmz4281/1920/F1.csv"),
    ],
    "soccer_brazil_campeonato": [
        ("2024", "https://www.football-data.co.uk/new/BRA.csv"),
    ],
    "soccer_conmebol_copa_libertadores": [
        ("2024", "https://www.football-data.co.uk/new/BRA.csv"),
    ],
}

REQUIRED_COLS = {
    "standard": ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"],
    "extra": ["HS", "AS", "HST", "AST", "HC", "AC"],
}


def download_csv(url: str, filepath: Path) -> bool:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        if len(response.content) < 100:
            return False
        filepath.write_bytes(response.content)
        logger.info(f"✓ Baixado: {filepath.name}")
        return True
    except Exception as e:
        logger.error(f"Erro ao baixar {url}: {e}")
        return False


def download_all_leagues(force: bool = False) -> dict:
    results = {}
    for league, seasons in LEAGUE_URLS.items():
        league_dir = DATA_DIR / league
        league_dir.mkdir(exist_ok=True)
        results[league] = []
        for season, url in seasons:
            filepath = league_dir / f"{season}.csv"
            if filepath.exists() and not force:
                results[league].append(str(filepath))
                continue
            if download_csv(url, filepath):
                results[league].append(str(filepath))
            time.sleep(0.5)
    return results


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nomes de colunas para o formato padrão.
    Lida com formato europeu (HomeTeam/FTHG/FTR) e
    formato Brasil (Home/HG/Res).
    """
    # Remove BOM do nome da primeira coluna
    df.columns = [c.replace("ï»¿", "").strip() for c in df.columns]

    # Mapa do formato alternativo para o padrão
    col_map = {
        "Home": "HomeTeam",
        "Away": "AwayTeam",
        "HG": "FTHG",
        "AG": "FTAG",
        "Res": "FTR",
    }
    df = df.rename(columns=col_map)
    return df


def load_league_data(league: str) -> pd.DataFrame:
    league_dir = DATA_DIR / league
    if not league_dir.exists():
        return pd.DataFrame()

    dfs = []
    for csv_file in sorted(league_dir.glob("*.csv")):
        try:
            df = pd.read_csv(csv_file, encoding="latin-1", on_bad_lines="skip")

            # Normaliza colunas antes de verificar
            df = _normalize_columns(df)

            required = REQUIRED_COLS["standard"]
            missing = [c for c in required if c not in df.columns]
            if missing:
                logger.warning(f"{csv_file.name}: colunas faltando {missing}")
                continue

            for col in REQUIRED_COLS["extra"]:
                if col not in df.columns:
                    df[col] = None

            df = df[required + [c for c in REQUIRED_COLS["extra"] if c in df.columns]]
            df["league"] = league
            df["season"] = csv_file.stem

            df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
            df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"])
            df["FTHG"] = pd.to_numeric(df["FTHG"], errors="coerce")
            df["FTAG"] = pd.to_numeric(df["FTAG"], errors="coerce")
            df = df.dropna(subset=["FTHG", "FTAG"])
            df = df[df["FTR"].isin(["H", "D", "A"])]

            dfs.append(df)
            logger.info(f"Carregado {csv_file.name}: {len(df)} jogos")

        except Exception as e:
            logger.error(f"Erro ao ler {csv_file}: {e}")

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.sort_values("Date").reset_index(drop=True)
    logger.info(f"Liga {league}: {len(combined)} jogos no total")
    return combined


def load_all_leagues() -> pd.DataFrame:
    all_dfs = []
    for league in LEAGUE_URLS.keys():
        df = load_league_data(league)
        if not df.empty:
            all_dfs.append(df)
    if not all_dfs:
        return pd.DataFrame()
    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.sort_values("Date").reset_index(drop=True)
    logger.info(f"Total: {len(combined)} jogos em {len(all_dfs)} ligas")
    return combined


def get_data_summary() -> dict:
    summary = {}
    for league in LEAGUE_URLS.keys():
        league_dir = DATA_DIR / league
        if league_dir.exists():
            files = list(league_dir.glob("*.csv"))
            summary[league] = {"files": len(files), "seasons": [f.stem for f in files]}
        else:
            summary[league] = {"files": 0, "seasons": []}
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = download_all_leagues()
    for league, files in results.items():
        print(f"  {league}: {len(files)} arquivo(s)")