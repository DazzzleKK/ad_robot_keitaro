from __future__ import annotations

import pytest

from src.api.dependencies import get_search_keitaro_offers_usecase
from src.campaigns.dto import OfferSearchResultDto
from tests.integration.page_helpers import (
    FakeSearchKeitaroOffersUseCase,
    override_dependency,
)


@pytest.mark.asyncio
async def test_search_keitaro_offers_returns_matching_options(app, client):
    usecase = FakeSearchKeitaroOffersUseCase(
        offers=[
            OfferSearchResultDto(
                id=101,
                name="Alpha offer",
                label="101 - Alpha offer",
            ),
        ],
    )
    override_dependency(app, get_search_keitaro_offers_usecase, usecase)

    response = await client.get("/keitaro/offers/search", params={"q": "alp"})

    assert response.status_code == 200
    assert usecase.received_query == "alp"
    assert response.json() == [
        {
            "id": 101,
            "name": "Alpha offer",
            "label": "101 - Alpha offer",
        }
    ]
