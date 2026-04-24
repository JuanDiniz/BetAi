"""
Models do banco de dados.

Tabelas:
- Game: jogos de futebol
- Odd: odds coletadas por casa e jogo
- Alert: alertas gerados (value bet, odd promocional, etc)
"""

from datetime import datetime
from sqlalchemy import (
    String, Float, Boolean, DateTime, Text,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Game(Base):
    """Jogos de futebol monitorados."""

    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    sport_key: Mapped[str] = mapped_column(String(64))
    sport_title: Mapped[str] = mapped_column(String(128))
    home_team: Mapped[str] = mapped_column(String(128))
    away_team: Mapped[str] = mapped_column(String(128))
    commence_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Probabilidades calculadas pelo modelo de ML
    prob_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    prob_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    prob_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relacionamentos
    odds: Mapped[list["Odd"]] = relationship(back_populates="game")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="game")

    __table_args__ = (
        Index("ix_games_commence_time", "commence_time"),
        Index("ix_games_sport_key", "sport_key"),
    )

    def __repr__(self):
        return f"<Game {self.home_team} x {self.away_team}>"


class Odd(Base):
    """
    Odds coletadas por casa de aposta.
    Cada coleta gera um registro — mantém histórico completo.
    """

    __tablename__ = "odds"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("games.id"), nullable=False
    )
    bookmaker: Mapped[str] = mapped_column(String(64))

    # Odds do resultado final (1x2)
    odd_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    odd_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    odd_away: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Melhor odd disponível no momento da coleta
    best_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_home_bookmaker: Mapped[str | None] = mapped_column(String(64), nullable=True)
    best_draw_bookmaker: Mapped[str | None] = mapped_column(String(64), nullable=True)
    best_away_bookmaker: Mapped[str | None] = mapped_column(String(64), nullable=True)

    collected_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relacionamento
    game: Mapped["Game"] = relationship(back_populates="odds")

    __table_args__ = (
        Index("ix_odds_game_id", "game_id"),
        Index("ix_odds_bookmaker", "bookmaker"),
        Index("ix_odds_collected_at", "collected_at"),
    )

    def __repr__(self):
        return f"<Odd {self.bookmaker} | {self.game_id}>"


class Alert(Base):
    """
    Alertas gerados pelo sistema.
    Tipos: value_bet, odd_promo, odd_dropping, promo_code, cashback
    """

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    game_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("games.id"), nullable=True
    )

    # Tipo do alerta
    alert_type: Mapped[str] = mapped_column(String(32))
    # value_bet | odd_promo | odd_dropping | promo_code | cashback

    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text)

    # Dados específicos do alerta (JSON como string)
    extra_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Bookmaker envolvido
    bookmaker: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Value bet específico
    edge: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # home | draw | away

    # Controle
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relacionamento
    game: Mapped["Game | None"] = relationship(back_populates="alerts")

    __table_args__ = (
        Index("ix_alerts_alert_type", "alert_type"),
        Index("ix_alerts_is_active", "is_active"),
        Index("ix_alerts_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<Alert {self.alert_type} | {self.title[:30]}>"