"""링크 생성·조회·수정·삭제와 클릭 집계 로직. 모든 쿼리는 파라미터 바인딩을 쓴다."""

import secrets
import string
from datetime import date, timedelta
from typing import Any

import pymysql
from pymysql.connections import Connection

CODE_ALPHABET = string.ascii_letters + string.digits
# Nginx 설정의 리다이렉트 경로 정규식({6})과 같은 값이어야 한다.
CODE_LENGTH = 6
MAX_CODE_ATTEMPTS = 5
MYSQL_DUPLICATE_ENTRY = 1062
MAX_HEADER_LENGTH = 512

LINK_WITH_CLICKS_SQL = """
    SELECT l.id, l.code, l.original_url, l.title, l.created_at,
           COUNT(c.id) AS clicks, MAX(c.clicked_at) AS last_clicked_at
    FROM links l
    LEFT JOIN clicks c ON c.link_id = l.id
"""


class CodeGenerationError(RuntimeError):
    """중복되지 않는 단축 코드를 만들지 못했을 때 발생한다."""


def generate_code(length: int = CODE_LENGTH) -> str:
    """암호학적으로 안전한 난수로 영문 대소문자+숫자 코드를 만든다."""
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))


def create_link(conn: Connection, url: str, title: str | None) -> dict[str, Any]:
    """링크를 저장하고 저장된 행을 돌려준다.

    코드가 겹치면 UNIQUE 제약 위반이 나므로 새 코드로 다시 시도한다.
    조회 후 삽입하는 방식과 달리 동시 요청에서도 중복이 생기지 않는다.

    Raises:
        CodeGenerationError: 정해진 횟수 안에 고유한 코드를 얻지 못한 경우.
    """
    for _ in range(MAX_CODE_ATTEMPTS):
        code = generate_code()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO links (code, original_url, title) VALUES (%s, %s, %s)",
                    (code, url, title),
                )
        except pymysql.err.IntegrityError as exc:
            if exc.args and exc.args[0] == MYSQL_DUPLICATE_ENTRY:
                continue
            raise
        link = get_link(conn, code)
        if link is not None:
            return link
    raise CodeGenerationError("단축 코드를 만들지 못했습니다.")


def list_links(conn: Connection) -> list[dict[str, Any]]:
    """모든 링크를 최신순으로, 클릭 수와 함께 한 번의 쿼리로 가져온다."""
    with conn.cursor() as cursor:
        cursor.execute(
            LINK_WITH_CLICKS_SQL + " GROUP BY l.id ORDER BY l.created_at DESC, l.id DESC"
        )
        return list(cursor.fetchall())


def get_link(conn: Connection, code: str) -> dict[str, Any] | None:
    """코드로 링크 한 건을 클릭 수와 함께 찾는다. 없으면 None."""
    with conn.cursor() as cursor:
        cursor.execute(
            LINK_WITH_CLICKS_SQL + " WHERE l.code = %s GROUP BY l.id",
            (code,),
        )
        return cursor.fetchone()


def find_redirect_target(conn: Connection, code: str) -> dict[str, Any] | None:
    """리다이렉트에 필요한 id와 원본 URL만 가볍게 조회한다."""
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, original_url FROM links WHERE code = %s",
            (code,),
        )
        return cursor.fetchone()


def update_link(
    conn: Connection, code: str, url: str, title: str | None
) -> dict[str, Any] | None:
    """링크의 원본 URL과 메모를 바꾼다. 대상이 없으면 None."""
    if get_link(conn, code) is None:
        return None
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE links SET original_url = %s, title = %s WHERE code = %s",
            (url, title, code),
        )
    return get_link(conn, code)


def delete_link(conn: Connection, code: str) -> bool:
    """링크를 지운다. 클릭 기록은 외래키 CASCADE 로 함께 지워진다."""
    with conn.cursor() as cursor:
        deleted = cursor.execute("DELETE FROM links WHERE code = %s", (code,))
    return deleted > 0


def record_click(
    conn: Connection, link_id: int, referrer: str | None, user_agent: str | None
) -> None:
    """클릭 한 건을 기록한다. 헤더 값은 컬럼 길이에 맞춰 자른다."""
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO clicks (link_id, referrer, user_agent) VALUES (%s, %s, %s)",
            (link_id, _truncate(referrer), _truncate(user_agent)),
        )


def daily_clicks(
    conn: Connection, link_id: int, days: int, today: date
) -> list[dict[str, Any]]:
    """오늘을 포함한 최근 days일의 일별 클릭 수를 날짜순으로 돌려준다."""
    start = today - timedelta(days=days - 1)
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT DATE(clicked_at) AS day, COUNT(*) AS clicks
            FROM clicks
            WHERE link_id = %s AND clicked_at >= %s
            GROUP BY DATE(clicked_at)
            """,
            (link_id, start),
        )
        rows = cursor.fetchall()
    return fill_missing_days({row["day"]: row["clicks"] for row in rows}, days, today)


def fill_missing_days(
    counts: dict[date, int], days: int, today: date
) -> list[dict[str, Any]]:
    """클릭이 없던 날을 0으로 채워 길이가 days인 목록을 만든다."""
    start = today - timedelta(days=days - 1)
    return [
        {"date": start + timedelta(days=offset), "clicks": counts.get(start + timedelta(days=offset), 0)}
        for offset in range(days)
    ]


def _truncate(value: str | None) -> str | None:
    """빈 값은 None 으로, 긴 값은 컬럼 길이로 자른다."""
    if not value:
        return None
    return value[:MAX_HEADER_LENGTH]
