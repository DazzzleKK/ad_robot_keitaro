from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from src.api.dependencies import get_list_dictionaries_usecase, get_refresh_dictionaries_usecase
from src.api.page_utils import group_dictionaries, render_dictionaries_error, templates
from src.campaigns.exceptions import DictionariesNotLoadedError, KeitaroOperationError

router = APIRouter()


@router.get("/dictionaries", response_class=HTMLResponse)
async def dictionaries_page(
    request: Request,
    usecase=Depends(get_list_dictionaries_usecase),
) -> HTMLResponse:
    try:
        items = await usecase.execute()
    except (DictionariesNotLoadedError, KeitaroOperationError) as exc:
        return render_dictionaries_error(request, exc)
    context = {
        "request": request,
        "title": "Dictionaries",
        "dictionaries": group_dictionaries(items),
        "error": None,
    }
    return templates.TemplateResponse(request=request, name="dictionaries.html", context=context)


@router.post("/dictionaries/refresh")
async def refresh_dictionaries(
    request: Request,
    usecase=Depends(get_refresh_dictionaries_usecase),
) -> Response:
    try:
        await usecase.execute()
    except (DictionariesNotLoadedError, KeitaroOperationError) as exc:
        return render_dictionaries_error(request, exc)
    return RedirectResponse(url="/dictionaries", status_code=303)
