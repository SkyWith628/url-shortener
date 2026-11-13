"""단축 코드 접속을 원본 URL로 보내는 라우터."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from fastapi.responses import RedirectResponse
from pymysql.connections import Connection

from app.db import get_db
from app.routers.links import CODE_PATTERN
from app.services import links as link_service

router = APIRouter(tags=["redirect"])


@router.get("/{code}", include_in_schema=False)
def follow_link(
    code: Annotated[str, Path(pattern=CODE_PATTERN)],
    request: Request,
    conn: Annotated[Connection, Depends(get_db)],
) -> RedirectResponse:
    """클릭을 기록하고 원본 URL로 302 리다이렉트한다.

    301은 브라우저가 캐시해 이후 클릭이 서버에 오지 않으므로 302와 no-store 를 쓴다.
    """
    target = link_service.find_redirect_target(conn, code)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "존재하지 않는 단축 링크입니다.")
    link_service.record_click(
        conn,
        target["id"],
        request.headers.get("referer"),
        request.headers.get("user-agent"),
    )
    return RedirectResponse(
        target["original_url"],
        status_code=status.HTTP_302_FOUND,
        headers={"Cache-Control": "no-store"},
    )
