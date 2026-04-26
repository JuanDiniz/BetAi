"""
Script de treinamento do modelo BetAI.

Uso:
    python train.py              # treina com dados existentes
    python train.py --download   # baixa dados novos e treina
    python train.py --evaluate   # avalia modelo existente
"""

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Adiciona o backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    parser = argparse.ArgumentParser(description="Treina o modelo BetAI")
    parser.add_argument("--download", action="store_true", help="Baixa dados antes de treinar")
    parser.add_argument("--evaluate", action="store_true", help="Só avalia o modelo existente")
    parser.add_argument("--force", action="store_true", help="Rebaixa dados mesmo se existirem")
    args = parser.parse_args()

    from app.ml.data_collector import download_all_leagues, load_all_leagues, get_data_summary
    from app.ml.features import build_training_dataset
    from app.ml.model import train_model, load_model

    # 1. Download de dados
    if args.download or args.force:
        logger.info("=" * 50)
        logger.info("ETAPA 1: Download de dados históricos")
        logger.info("=" * 50)
        results = download_all_leagues(force=args.force)
        for league, files in results.items():
            logger.info(f"  {league}: {len(files)} arquivo(s)")
    else:
        summary = get_data_summary()
        total_files = sum(v["files"] for v in summary.values())
        if total_files == 0:
            logger.warning("Nenhum dado encontrado. Execute com --download primeiro.")
            logger.info("Executando download automático...")
            download_all_leagues()

    # 2. Carrega dados
    logger.info("\n" + "=" * 50)
    logger.info("ETAPA 2: Carregando dados históricos")
    logger.info("=" * 50)
    df = load_all_leagues()

    if df.empty:
        logger.error("Nenhum dado disponível para treino!")
        sys.exit(1)

    logger.info(f"Total: {len(df)} jogos carregados")
    logger.info(f"Período: {df['Date'].min().date()} → {df['Date'].max().date()}")
    logger.info(f"Ligas: {df['league'].nunique()}")

    if args.evaluate:
        logger.info("\nCarregando modelo existente para avaliação...")
        model, feature_names = load_model()
        logger.info("Modelo carregado. Use --download para retreinar.")
        return

    # 3. Engenharia de features
    logger.info("\n" + "=" * 50)
    logger.info("ETAPA 3: Construindo features")
    logger.info("=" * 50)
    logger.info("Isso pode levar alguns minutos...")

    X, y = build_training_dataset(df)

    if len(X) < 100:
        logger.error(f"Poucos dados para treino: {len(X)} amostras")
        sys.exit(1)

    # 4. Treino
    logger.info("\n" + "=" * 50)
    logger.info("ETAPA 4: Treinando modelo XGBoost")
    logger.info("=" * 50)

    metrics = train_model(X, y)

    # 5. Resultado
    logger.info("\n" + "=" * 50)
    logger.info("RESULTADO DO TREINAMENTO")
    logger.info("=" * 50)
    logger.info(f"  Acurácia:      {metrics['accuracy']*100:.1f}%")
    logger.info(f"  Baseline:      {metrics['baseline_accuracy']*100:.1f}%")
    logger.info(f"  Melhora:       +{metrics['improvement']*100:.1f}%")
    logger.info(f"  Log Loss:      {metrics['log_loss']:.4f}")
    logger.info(f"  Treino:        {metrics['train_size']} jogos")
    logger.info(f"  Teste:         {metrics['test_size']} jogos")
    logger.info(f"  Features:      {metrics['feature_count']}")
    logger.info(f"\n  Modelo salvo em: app/ml/models/betai_model.pkl")

    # Aviso de qualidade
    if metrics['improvement'] < 0.02:
        logger.warning("\n⚠️  Melhora abaixo de 2% sobre baseline.")
        logger.warning("   Considere adicionar mais dados ou features.")
    elif metrics['improvement'] >= 0.05:
        logger.info("\n✅ Boa melhora sobre baseline! Modelo pronto para produção.")
    else:
        logger.info("\n✓ Modelo treinado com sucesso.")


if __name__ == "__main__":
    main()