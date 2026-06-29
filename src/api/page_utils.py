from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.api.forms import FormParseError
from src.campaigns.exceptions import (
    CampaignNotFoundError,
    CampaignOfferBatchError,
    CampaignStreamNotFoundError,
    DictionariesNotLoadedError,
    KeitaroOperationError,
)
from src.dictionaries.dto import DictionaryItemDto, DictionaryType

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))


@dataclass(frozen=True, slots=True)
class PageError:
    message: str
    status_code: int


def group_dictionaries(items: Iterable[DictionaryItemDto]) -> dict[DictionaryType, list[DictionaryItemDto]]:
    grouped = {dictionary_type: [] for dictionary_type in DictionaryType}
    for item in items:
        grouped[item.dictionary_type].append(item)
    return grouped


def page_error_from_domain(exc: Exception) -> PageError:
    return PageError(message=message_for_error(exc), status_code=status_code_for_error(exc))


def message_for_error(exc: Exception) -> str:
    if isinstance(
        exc,
        (
            CampaignNotFoundError,
            CampaignOfferBatchError,
            CampaignStreamNotFoundError,
            DictionariesNotLoadedError,
            KeitaroOperationError,
        ),
    ):
        return exc.message
    if isinstance(exc, FormParseError):
        return str(exc)
    return "Unexpected error"


def status_code_for_error(exc: Exception) -> int:
    if isinstance(exc, (CampaignNotFoundError, CampaignStreamNotFoundError)):
        return 404
    if isinstance(exc, KeitaroOperationError):
        return 503
    if isinstance(
        exc,
        (
            CampaignOfferBatchError,
            FormParseError,
            DictionariesNotLoadedError,
        ),
    ):
        return 400
    return 400


def render_dictionaries_error(request: Request, exc: Exception) -> HTMLResponse:
    status_code = status_code_for_error(exc)
    context = {
        "request": request,
        "title": "Dictionaries",
        "dictionaries": group_dictionaries([]),
        "error": PageError(message=message_for_error(exc), status_code=status_code),
    }
    return templates.TemplateResponse(
        request=request,
        name="dictionaries.html",
        context=context,
        status_code=status_code,
    )
