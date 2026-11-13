"""FastAPI 진입점."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_schema
from app.routers import links, redirect

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """요청을 받기 전에 DB 연결을 확인하고 테이블을 준비한다."""
    init_schema()
    yield


app = FastAPI(title="URL Shortener API", lifespan=lifespan)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """컨테이너 헬스체크용 엔드포인트."""
    return {"status": "ok"}


app.include_router(links.router)
# /{code} 가 다른 경로를 가로채지 않도록 마지막에 등록한다.
app.include_router(redirect.router)
