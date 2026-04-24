"""
Script de teste do scraper — roda direto no terminal.
Uso: python test_scraper.py
"""

import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()

from app.scrapers.odds_scraper import OddsScraper, calculate_value_bet

API_KEY = os.getenv("API_ODDS_KEY")


async def main():
    print("=" * 60)
    print("BetAI — Teste do Scraper de Odds")
    print("=" * 60)

    scraper = OddsScraper(api_key=API_KEY)

    # Testa só o Brasileirão pra não gastar muitas requisições
    print("\n📡 Buscando odds do Brasileirão...\n")
    odds = await scraper.get_odds("soccer_brazil_campeonato")

    if not odds:
        print("❌ Nenhum jogo encontrado. Pode ser que não haja jogos hoje.")
        await scraper.close()
        return

    parsed = scraper._parse_odds(odds)

    print(f"✅ {len(parsed)} jogos encontrados!\n")
    print("-" * 60)

    for game in parsed[:3]:  # Mostra só os 3 primeiros
        print(f"\n⚽ {game['home_team']} x {game['away_team']}")
        print(f"   🕐 {game['commence_time']}")
        print(f"\n   Odds por casa:")

        for bookmaker, odds_data in game["bookmakers"].items():
            print(
                f"   • {bookmaker:<15} "
                f"Casa: {odds_data['home'] or '-':<8} "
                f"Empate: {odds_data['draw'] or '-':<8} "
                f"Fora: {odds_data['away'] or '-'}"
            )

        print(f"\n   🏆 Melhores odds:")
        best = game["best_odds"]
        print(f"   • Casa:    {best['home']['odd']} ({best['home']['bookmaker']})")
        print(f"   • Empate:  {best['draw']['odd']} ({best['draw']['bookmaker']})")
        print(f"   • Fora:    {best['away']['odd']} ({best['away']['bookmaker']})")

        # Simula análise de value bet com probabilidade fictícia
        # (no produto real vem do modelo de ML)
        fake_model_prob = 0.55  # 55% de chance pra time da casa
        value = calculate_value_bet(fake_model_prob, best['home']['odd'])
        if value:
            print(f"\n   🔥 VALUE BET DETECTADO!")
            print(f"      Modelo: {value['model_probability']*100:.1f}%")
            print(f"      Odd implica: {value['implied_probability']*100:.1f}%")
            print(f"      Edge: +{value['edge_percent']}%")
            print(f"      Expected Value: +{value['expected_value']*100:.1f}%")

        print("-" * 60)

    await scraper.close()
    print("\n✅ Teste concluído!")


if __name__ == "__main__":
    asyncio.run(main())