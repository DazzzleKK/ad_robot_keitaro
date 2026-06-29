from __future__ import annotations

import pytest

from src.api.dependencies import (
    get_list_dictionaries_usecase,
    get_refresh_dictionaries_usecase,
)
from src.campaigns.exceptions import KeitaroOperationError
from tests.integration.page_helpers import (
    FakeListDictionariesUseCase,
    FakeRefreshDictionariesUseCase,
    dictionary_items,
    override_dependency,
)


@pytest.mark.asyncio
async def test_dictionaries_page_renders_cached_items(app, client):
    usecase = FakeListDictionariesUseCase(dictionary_items())
    override_dependency(app, get_list_dictionaries_usecase, usecase)

    response = await client.get("/dictionaries")

    assert response.status_code == 200
    assert "Keitaro dictionaries" in response.text
    assert "Domain A" in response.text
    assert "Offer A" in response.text


@pytest.mark.asyncio
async def test_refresh_dictionaries_redirects_back_to_page(app, client):
    usecase = FakeRefreshDictionariesUseCase(dictionary_items())
    override_dependency(app, get_refresh_dictionaries_usecase, usecase)

    response = await client.post("/dictionaries/refresh", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/dictionaries"
    assert usecase.calls == 1


@pytest.mark.asyncio
async def test_refresh_dictionaries_error_renders_error_page(app, client):
    usecase = FakeRefreshDictionariesUseCase(
        KeitaroOperationError(
            operation="fetch_domains",
            message="Keitaro unavailable",
        ),
    )
    override_dependency(app, get_refresh_dictionaries_usecase, usecase)

    response = await client.post("/dictionaries/refresh")

    assert response.status_code == 503
    assert "Keitaro unavailable" in response.text
    assert usecase.calls == 1
