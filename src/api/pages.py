from __future__ import annotations

from fastapi import APIRouter

from src.api import admin_pages, campaign_pages, dictionary_pages

router = APIRouter()
router.include_router(admin_pages.router)
router.include_router(campaign_pages.router)
router.include_router(dictionary_pages.router)
