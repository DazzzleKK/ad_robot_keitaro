from __future__ import annotations

from collections.abc import Iterable

from fastapi import Request
from fastapi.responses import HTMLResponse

from src.api.forms import CreateCampaignFormState
from src.api.page_utils import (
    PageError,
    group_dictionaries,
    message_for_error,
    status_code_for_error,
    templates,
)
from src.campaigns.dto import CampaignDto
from src.campaigns.exceptions import DictionariesNotLoadedError, KeitaroOperationError
from src.dictionaries.dto import DictionaryItemDto


def render_campaigns_page(request: Request, campaigns: list[CampaignDto]) -> HTMLResponse:
    context = {
        "request": request,
        "title": "Campaigns",
        "campaigns": campaigns,
        "error": None,
    }
    return templates.TemplateResponse(request=request, name="campaigns_list.html", context=context)


def render_create_campaign_page(
    *,
    request: Request,
    dictionaries: Iterable[DictionaryItemDto],
    form_state: CreateCampaignFormState,
    error: PageError | None,
) -> HTMLResponse:
    context = {
        "request": request,
        "title": "Create campaign",
        "dictionaries": group_dictionaries(dictionaries),
        "form": form_state,
        "error": error,
    }
    return templates.TemplateResponse(
        request=request,
        name="campaigns_create.html",
        context=context,
        status_code=error.status_code if error is not None else 200,
    )


def render_campaign_editor_page(request: Request, campaign: CampaignDto) -> HTMLResponse:
    context = {
        "request": request,
        "title": f"Campaign {campaign.id}",
        "campaign": campaign,
        "error": None,
    }
    return templates.TemplateResponse(request=request, name="campaigns_editor.html", context=context)


def render_campaign_editor_error(request: Request, campaign_id: int, exc: Exception) -> HTMLResponse:
    status_code = status_code_for_error(exc)
    context = {
        "request": request,
        "title": f"Campaign {campaign_id}",
        "campaign": None,
        "error": PageError(message=message_for_error(exc), status_code=status_code),
    }
    return templates.TemplateResponse(
        request=request,
        name="campaigns_editor.html",
        context=context,
        status_code=status_code,
    )


async def safe_list_dictionaries(usecase) -> list[DictionaryItemDto]:
    try:
        return await usecase.execute()
    except (DictionariesNotLoadedError, KeitaroOperationError):
        return []
