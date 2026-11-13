"""DB 없이 검증할 수 있는 로직의 단위 테스트."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.models.schemas import MAX_URL_LENGTH, LinkInput
from app.services.links import CODE_ALPHABET, CODE_LENGTH, fill_missing_days, generate_code


def test_generate_code_uses_expected_length_and_alphabet() -> None:
    code = generate_code()
    assert len(code) == CODE_LENGTH
    assert set(code) <= set(CODE_ALPHABET)


def test_generate_code_is_not_constant() -> None:
    assert len({generate_code() for _ in range(50)}) > 1


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", "ftp://example.com/file", "example.com", "", "http://"],
)
def test_link_input_rejects_non_http_urls(url: str) -> None:
    with pytest.raises(ValidationError):
        LinkInput(url=url)


def test_link_input_accepts_http_and_https() -> None:
    assert str(LinkInput(url="https://example.com/a?b=1").url) == "https://example.com/a?b=1"
    assert str(LinkInput(url="http://example.com").url).startswith("http://example.com")


def test_link_input_rejects_too_long_url() -> None:
    with pytest.raises(ValidationError):
        LinkInput(url="https://example.com/" + "a" * MAX_URL_LENGTH)


def test_link_input_normalizes_title() -> None:
    assert LinkInput(url="https://example.com", title="  메모  ").title == "메모"
    assert LinkInput(url="https://example.com", title="   ").title is None
    assert LinkInput(url="https://example.com").title is None


def test_link_input_rejects_too_long_title() -> None:
    with pytest.raises(ValidationError):
        LinkInput(url="https://example.com", title="가" * 101)


def test_fill_missing_days_fills_zero_and_keeps_order() -> None:
    today = date(2026, 11, 13)
    result = fill_missing_days({date(2026, 11, 12): 3, date(2026, 11, 7): 1}, 7, today)
    assert [row["date"] for row in result][0] == date(2026, 11, 7)
    assert [row["date"] for row in result][-1] == today
    assert [row["clicks"] for row in result] == [1, 0, 0, 0, 0, 3, 0]


def test_fill_missing_days_ignores_out_of_range_days() -> None:
    result = fill_missing_days({date(2026, 1, 1): 9}, 1, date(2026, 11, 13))
    assert result == [{"date": date(2026, 11, 13), "clicks": 0}]
