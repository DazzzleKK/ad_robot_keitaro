from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from src.api.dependencies import (
    get_batch_update_stream_offers_usecase,
    get_campaign_editor_usecase,
    get_create_campaign_usecase,
    get_fetch_campaign_streams_usecase,
    get_list_campaigns_usecase,
    get_list_dictionaries_usecase,
    get_search_keitaro_offers_usecase,
)
from src.api.campaign_presenters import (
    render_campaign_editor_error,
    render_campaign_editor_page,
    render_campaigns_page,
    render_create_campaign_page,
    safe_list_dictionaries,
)
from src.api.forms import (
    FormParseError,
    build_create_campaign_form_state,
    build_batch_update_stream_offers_command,
    parse_create_campaign_form,
)
from src.api.page_utils import (
    PageError,
    page_error_from_domain,
    message_for_error,
)
from src.campaigns.exceptions import (
    CampaignNotFoundError,
    CampaignOfferBatchError,
    CampaignStreamNotFoundError,
    DictionariesNotLoadedError,
    KeitaroOperationError,
)

router = APIRouter()


@router.get("/campaigns", response_class=HTMLResponse)
async def campaigns_page(
    request: Request,
    usecase=Depends(get_list_campaigns_usecase),
) -> HTMLResponse:
    campaigns = await usecase.execute()
    return render_campaigns_page(request, campaigns)


@router.head("/campaigns")
async def campaigns_page_head() -> Response:
    return Response(status_code=200)


@router.get("/campaigns/new", response_class=HTMLResponse)
async def create_campaign_page(
    request: Request,
    usecase=Depends(get_list_dictionaries_usecase),
) -> HTMLResponse:
    try:
        items = await usecase.execute()
    except (DictionariesNotLoadedError, KeitaroOperationError) as exc:
        return render_create_campaign_page(
            request=request,
            dictionaries=[],
            form_state=build_create_campaign_form_state({}),
            error=page_error_from_domain(exc),
        )
    state = build_create_campaign_form_state({})
    return render_create_campaign_page(
        request=request,
        dictionaries=items,
        form_state=state,
        error=None,
    )


@router.post("/campaigns")
async def create_campaign(
    request: Request,
    usecase=Depends(get_create_campaign_usecase),
    dictionaries_usecase=Depends(get_list_dictionaries_usecase),
) -> Response:
    form = await request.form()
    state = build_create_campaign_form_state(form)
    try:
        command = parse_create_campaign_form(form)
    except FormParseError as exc:
        return render_create_campaign_page(
            request=request,
            dictionaries=await safe_list_dictionaries(dictionaries_usecase),
            form_state=state,
            error=PageError(message=str(exc), status_code=400),
        )

    try:
        campaign = await usecase.execute(command)
    except (CampaignNotFoundError, DictionariesNotLoadedError, KeitaroOperationError) as exc:
        return render_create_campaign_page(
            request=request,
            dictionaries=await safe_list_dictionaries(dictionaries_usecase),
            form_state=state,
            error=page_error_from_domain(exc),
        )

    return RedirectResponse(url=f"/campaigns/{campaign.id}", status_code=303)


@router.get("/campaigns/{campaign_id}", response_class=HTMLResponse)
async def campaign_editor_page(
    request: Request,
    campaign_id: int,
    usecase=Depends(get_campaign_editor_usecase),
) -> HTMLResponse:
    try:
        campaign = await usecase.execute(campaign_id)
    except (CampaignNotFoundError, KeitaroOperationError) as exc:
        return render_campaign_editor_error(request, campaign_id, exc)
    return render_campaign_editor_page(request, campaign)


@router.get("/keitaro/offers/search")
async def search_keitaro_offers(
    q: str = Query(default="", max_length=100),
    usecase=Depends(get_search_keitaro_offers_usecase),
) -> list[dict[str, str | int]]:
    try:
        offers = await usecase.execute(q)
    except KeitaroOperationError as exc:
        raise HTTPException(status_code=503, detail=message_for_error(exc)) from exc

    return [
        {
            "id": offer.id,
            "name": offer.name,
            "label": f"{offer.id} - {offer.name}",
        }
        for offer in offers
    ]


@router.post("/campaigns/{campaign_id}/fetch-streams")
async def fetch_campaign_streams(
    request: Request,
    campaign_id: int,
    usecase=Depends(get_fetch_campaign_streams_usecase),
) -> Response:
    try:
        campaign = await usecase.execute(campaign_id)
    except (CampaignNotFoundError, CampaignStreamNotFoundError, KeitaroOperationError) as exc:
        return render_campaign_editor_error(request, campaign_id, exc)
    return RedirectResponse(url=f"/campaigns/{campaign.id}", status_code=303)


@router.post("/campaigns/{campaign_id}/streams/{stream_id}/offers/batch")
async def batch_update_campaign_offers(
    request: Request,
    campaign_id: int,
    stream_id: int,
    usecase=Depends(get_batch_update_stream_offers_usecase),
) -> Response:
    form = await request.form()
    try:
        command = build_batch_update_stream_offers_command(
            campaign_id=campaign_id,
            stream_id=stream_id,
            form=form,
        )
    except FormParseError as exc:
        return render_campaign_editor_error(
            request,
            campaign_id,
            exc,
        )

    try:
        campaign = await usecase.execute(command)
    except (
        CampaignNotFoundError,
        CampaignStreamNotFoundError,
        CampaignOfferBatchError,
        KeitaroOperationError,
    ) as exc:
        return render_campaign_editor_error(request, campaign_id, exc)
    return RedirectResponse(url=f"/campaigns/{campaign.id}", status_code=303)
