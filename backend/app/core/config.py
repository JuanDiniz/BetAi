from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    # Banco de dados
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # API Football
    API_FOOTBALL_KEY: str
    API_FOOTBALL_URL: str = "https://v3.football.api-sports.io"
    API_ODDS_KEY: str = ""
    
    # Links de afiliado
    AFFILIATE_BETANO: str = ""
    AFFILIATE_BET365: str = ""
    AFFILIATE_BETSSON: str = ""
    AFFILIATE_BETNACIONAL: str = ""
    AFFILIATE_F12BET: str = ""
    AFFILIATE_KTO: str = ""

    # Thresholds
    VALUE_BET_THRESHOLD: float = 0.05
    ODD_CHANGE_THRESHOLD: float = 0.10
    SCRAPE_INTERVAL_MINUTES: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
