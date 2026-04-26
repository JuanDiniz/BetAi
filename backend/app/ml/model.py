"""
Treinamento e avaliação do modelo XGBoost.

Usa validação temporal — treina em temporadas passadas,
testa na mais recente. Nunca usa dados do futuro.
"""

import joblib
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import log_loss, accuracy_score
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

MODEL_PATH = MODEL_DIR / "betai_model.pkl"
FEATURE_NAMES_PATH = MODEL_DIR / "feature_names.pkl"


def train_model(X: pd.DataFrame, y: pd.Series, test_size: float = 0.2) -> dict:
    """
    Treina o modelo XGBoost com validação temporal.

    Args:
        X: DataFrame de features
        y: Series de labels (0=home, 1=draw, 2=away)
        test_size: fração dos dados mais recentes para teste

    Returns:
        dict com métricas de avaliação
    """
    n = len(X)
    split = int(n * (1 - test_size))

    # Divisão temporal — dados mais recentes ficam no teste
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    logger.info(f"Treino: {len(X_train)} jogos | Teste: {len(X_test)} jogos")

    # XGBoost com hiperparâmetros calibrados para futebol
    xgb = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        gamma=1,
        reg_alpha=0.1,
        reg_lambda=1.0,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
    )

    # Calibração de probabilidades com Platt scaling
    # Isso é CRÍTICO — sem calibração, as probabilidades do XGBoost
    # tendem a ser extremas (muito próximas de 0 ou 1)
    model = CalibratedClassifierCV(xgb, method="isotonic", cv=3)

    logger.info("Treinando modelo...")
    model.fit(X_train, y_train)

    # Avaliação
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    logloss = log_loss(y_test, y_proba)

    # Baseline: sempre prever o resultado mais comum
    baseline_pred = np.full(len(y_test), y_train.mode()[0])
    baseline_acc = accuracy_score(y_test, baseline_pred)

    # Salva o modelo e os nomes das features
    joblib.dump(model, MODEL_PATH)
    joblib.dump(list(X.columns), FEATURE_NAMES_PATH)

    metrics = {
        "accuracy": round(accuracy, 4),
        "baseline_accuracy": round(baseline_acc, 4),
        "improvement": round(accuracy - baseline_acc, 4),
        "log_loss": round(logloss, 4),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "feature_count": len(X.columns),
    }

    logger.info(f"Acurácia: {accuracy:.2%} (baseline: {baseline_acc:.2%}, melhora: +{accuracy-baseline_acc:.2%})")
    logger.info(f"Log Loss: {logloss:.4f}")

    return metrics


def load_model():
    """Carrega o modelo salvo."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Modelo não encontrado em {MODEL_PATH}. Execute o treinamento primeiro.")

    model = joblib.load(MODEL_PATH)
    feature_names = joblib.load(FEATURE_NAMES_PATH)
    return model, feature_names


def predict_probabilities(model, feature_names: list, features: dict) -> dict:
    """
    Gera probabilidades para um jogo.

    Returns dict com prob_home, prob_draw, prob_away.
    """
    # Garante que as features estão na ordem certa
    X = pd.DataFrame([features])[feature_names]

    # Preenche NaN com médias neutras
    X = X.fillna(X.mean())

    proba = model.predict_proba(X)[0]

    # Classes: 0=home, 1=draw, 2=away
    return {
        "prob_home": round(float(proba[0]), 4),
        "prob_draw": round(float(proba[1]), 4),
        "prob_away": round(float(proba[2]), 4),
    }


def evaluate_value_bets(
    model,
    feature_names: list,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    odds_test: pd.DataFrame = None,
) -> dict:
    """
    Avalia performance de value bets no conjunto de teste.
    Simula apostas onde o modelo detecta edge positivo.
    """
    y_proba = model.predict_proba(X_test[feature_names])
    threshold = 0.05  # 5% de edge mínimo

    results = {
        "total_bets": 0,
        "wins": 0,
        "roi": 0.0,
        "avg_edge": 0.0,
    }

    if odds_test is None:
        return results

    edges = []
    profits = []

    for i in range(len(X_test)):
        for outcome_idx, outcome_col in enumerate(["B365H", "B365D", "B365A"]):
            if outcome_col not in odds_test.columns:
                continue

            odd = odds_test.iloc[i][outcome_col]
            if pd.isna(odd) or odd <= 1:
                continue

            implied_prob = 1 / odd
            model_prob = y_proba[i][outcome_idx]
            edge = model_prob - implied_prob

            if edge >= threshold:
                results["total_bets"] += 1
                edges.append(edge)

                # Simula aposta de 1 unidade
                actual = y_test.iloc[i]
                if actual == outcome_idx:
                    profits.append(odd - 1)
                    results["wins"] += 1
                else:
                    profits.append(-1)

    if results["total_bets"] > 0:
        results["roi"] = round(sum(profits) / results["total_bets"] * 100, 2)
        results["avg_edge"] = round(np.mean(edges) * 100, 2)
        results["win_rate"] = round(results["wins"] / results["total_bets"] * 100, 2)

    return results