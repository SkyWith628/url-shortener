"""링크 관리 API (/api/links)."""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from pymysql.connections import Connection

from app.db import get_db
from app.models.schemas import LinkInput, LinkOut, StatsOut
from app.services import links as link_service

router = APIRouter(prefix="/api/links", tags=["links"])

KST = timezone(timedelta(hours=9))
CODE_PATTERN = r"^[A-Za-z0-9]{6}$"

Db = Annotated[Connection, Depends(get_db)]
Code = Annotated[str, Path(pattern=CODE_PATTERN)]


@router.post("", response_model=LinkOut, status_code=status.HTTP_201_CREATED)
def create_link(body: LinkInput, conn: Db) -> dict:
    """긴 URL을 받아 단축 링크를 만든다."""
    try:
        return link_service.create_link(conn, str(body.url), body.title)
    except link_service.CodeGenerationError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc


@router.get("", response_model=list[LinkOut])
def list_links(conn: Db) -> list[dict]:
    """모든 링크를 최신순으로 돌려준다."""
    return link_service.list_links(conn)


@router.put("/{code}", response_model=LinkOut)
def update_link(code: Code, body: LinkInput, conn: Db) -> dict:
    """링크의 원본 URL과 메모를 수정한다."""
    link = link_service.update_link(conn, code, str(body.url), body.title)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "링크를 찾을 수 없습니다.")
    return link


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(code: Code, conn: Db) -> Response:
    """링크와 그 클릭 기록을 삭제한다."""
    if not link_service.delete_link(conn, code):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "링크를 찾을 수 없습니다.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{code}/stats", response_model=StatsOut)
def link_stats(
    code: Code,
    conn: Db,
    days: Annotated[int, Query(ge=1, le=30)] = 7,
) -> dict:
    """최근 days일의 일별 클릭 수를 돌려준다."""
    link = link_service.get_link(conn, code)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "링크를 찾을 수 없습니다.")
    today = datetime.now(KST).date()
    return {
        "code": link["code"],
        "total_clicks": link["clicks"],
        "daily": link_service.daily_clicks(conn, link["id"], days, today),
    }
