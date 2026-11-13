"""API 입출력 스키마."""

from datetime import date, datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator

MAX_URL_LENGTH = 2048
MAX_TITLE_LENGTH = 100


class LinkInput(BaseModel):
    """링크 생성·수정 요청. HttpUrl 이 http/https 외 스킴(javascript: 등)을 막는다."""

    url: HttpUrl
    title: str | None = Field(default=None, max_length=MAX_TITLE_LENGTH)

    @field_validator("url")
    @classmethod
    def check_url_length(cls, value: HttpUrl) -> HttpUrl:
        """DB 컬럼 길이를 넘는 URL을 거절한다."""
        if len(str(value)) > MAX_URL_LENGTH:
            raise ValueError(f"URL은 {MAX_URL_LENGTH}자 이하여야 합니다.")
        return value

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        """앞뒤 공백을 지우고 빈 문자열은 None 으로 바꾼다."""
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class LinkOut(BaseModel):
    """링크 한 건과 누적 클릭 수."""

    code: str
    original_url: str
    title: str | None
    created_at: datetime
    clicks: int
    last_clicked_at: datetime | None


class DailyClicks(BaseModel):
    """하루치 클릭 수."""

    date: date
    clicks: int


class StatsOut(BaseModel):
    """링크의 최근 일별 클릭 통계."""

    code: str
    total_clicks: int
    daily: list[DailyClicks]
