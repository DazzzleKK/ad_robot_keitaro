from __future__ import annotations

import pytest

from src.api.dependencies import (
    get_campaign_editor_usecase,
    get_fetch_campaign_streams_usecase,
    get_list_campaigns_usecase,
)
from src.campaigns.exceptions import CampaignNotFoundError
from tests.integration.page_helpers import (
    FakeCampaignEditorUseCase,
    FakeFetchCampaignStreamsUseCase,
    FakeListCampaignsUseCase,
    campaign,
    override_dependency,
)


@pytest.mark.asyncio
async def test_campaigns_page_renders_database_campaigns(app, client):
    usecase = FakeListCampaignsUseCase([campaign()])
    override_dependency(app, get_list_campaigns_usecase, usecase)

    response = await client.get("/campaigns")

    assert response.status_code == 200
    assert "Campaign A" in response.text
    assert "99" in response.text
    assert usecase.calls == 1


@pytest.mark.asyncio
async def test_campaigns_page_allows_head(client):
    response = await client.head("/campaigns")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_campaign_editor_renders_active_and_inactive_offers(app, client):
    editor_usecase = FakeCampaignEditorUseCase(campaign())
    override_dependency(app, get_campaign_editor_usecase, editor_usecase)

    response = await client.get("/campaigns/55")

    assert response.status_code == 200
    assert "Campaign A" in response.text
    assert "Remove" in response.text
    assert "Search offers" in response.text
    assert "Cancel changes" in response.text
    assert "Apply batch" in response.text
    assert "Inactive" in response.text
    assert response.text.index("Offer 101") < response.text.index("Offer 102")


@pytest.mark.asyncio
async def test_campaign_editor_not_found_returns_error_block(app, client):
    editor_usecase = FakeCampaignEditorUseCase(CampaignNotFoundError(campaign_id=999))
    override_dependency(app, get_campaign_editor_usecase, editor_usecase)

    response = await client.get("/campaigns/999")

    assert response.status_code == 404
    assert "Campaign 999 not found" in response.text


@pytest.mark.asyncio
async def test_fetch_streams_redirects_back_to_campaign(app, client):
    usecase = FakeFetchCampaignStreamsUseCase(campaign())
    override_dependency(app, get_fetch_campaign_streams_usecase, usecase)

    response = await client.post("/campaigns/55/fetch-streams", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/campaigns/55"
    assert usecase.received_campaign_id == 55
