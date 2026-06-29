from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from src.api.page_utils import templates

router = APIRouter()


@router.get("/", include_in_schema=False)
async def index(request: Request) -> HTMLResponse:
    context = {
        "request": request,
        "title": "Admin",
        "objects": [
            {
                "name": "Campaigns",
                "url": "/campaigns",
                "description": "Campaigns stored in the local database.",
            }
        ],
        "error": None,
    }
    return templates.TemplateResponse(request=request, name="admin_index.html", context=context)
