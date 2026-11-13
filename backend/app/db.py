"""MySQL 연결과 스키마 초기화."""

import logging
import time
from collections.abc import Iterator

import pymysql
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ECS에서는 init.sql 을 마운트할 수 없으므로 백엔드가 시작할 때 테이블을 만든다.
SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS links (
        id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        -- 기본 콜레이션은 대소문자를 구분하지 않아 aB12cd 와 Ab12CD 가 같은 코드가 된다.
        code VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
        original_url VARCHAR(2048) NOT NULL,
        title VARCHAR(100) NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_links_code (code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS clicks (
        id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        link_id BIGINT UNSIGNED NOT NULL,
        clicked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        referrer VARCHAR(512) NULL,
        user_agent VARCHAR(512) NULL,
        KEY idx_clicks_link_time (link_id, clicked_at),
        CONSTRAINT fk_clicks_link FOREIGN KEY (link_id)
            REFERENCES links (id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
)


def connect() -> Connection:
    """새 DB 연결을 만든다. 세션 시간대는 KST로 고정해 일별 집계 기준을 맞춘다."""
    settings = get_settings()
    return pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
        connect_timeout=5,
        init_command="SET time_zone = '+09:00'",
    )


def get_db() -> Iterator[Connection]:
    """요청마다 연결을 열고 응답 후 닫는 FastAPI 의존성."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def init_schema() -> None:
    """DB가 준비될 때까지 재시도한 뒤 테이블을 만든다.

    Raises:
        RuntimeError: 정해진 횟수 안에 DB에 연결하지 못한 경우.
    """
    settings = get_settings()
    for attempt in range(1, settings.db_connect_retries + 1):
        try:
            conn = connect()
        except pymysql.err.OperationalError as exc:
            logger.warning(
                "DB 연결 대기 중 (%d/%d): %s",
                attempt,
                settings.db_connect_retries,
                exc.args[0] if exc.args else exc,
            )
            time.sleep(settings.db_connect_delay_seconds)
            continue
        try:
            with conn.cursor() as cursor:
                for statement in SCHEMA_STATEMENTS:
                    cursor.execute(statement)
        finally:
            conn.close()
        logger.info("스키마 준비 완료")
        return
    raise RuntimeError("DB에 연결하지 못했습니다.")
