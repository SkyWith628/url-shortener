"""환경변수 기반 설정.

컴포즈에서는 DB_HOST=db(서비스 이름), ECS 단일 태스크에서는 DB_HOST=127.0.0.1 을 쓴다.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """런타임 설정. 비밀번호는 기본값을 두지 않고 반드시 환경변수로 받는다."""

    model_config = SettingsConfigDict(extra="ignore")

    db_host: str = "db"
    db_port: int = 3306
    db_user: str = "shortener"
    db_password: str
    db_name: str = "shortener"

    # DB 컨테이너가 뜰 때까지 기다리는 횟수와 간격
    db_connect_retries: int = 30
    db_connect_delay_seconds: float = 2.0


@lru_cache
def get_settings() -> Settings:
    """설정을 한 번만 읽어 재사용한다."""
    return Settings()
