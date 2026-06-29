from __future__ import annotations

import pytest

from src.api.dependencies import (
    get_create_campaign_usecase,
    get_list_dictionaries_usecase,
)
from src.campaigns.dto import CreateCampaignCommand, CreateCampaignOfferDto
from tests.integration.page_helpers import (
    FakeCreateCampaignUseCase,
    FakeListDictionariesUseCase,
    campaign,
    dictionary_items,
    form_body,
    override_dependency,
)


@pytest.mark.asyncio
async def test_create_campaign_page_renders_form_with_dictionary_options(app, client):
    usecase = FakeListDictionariesUseCase(dictionary_items())
    override_dependency(app, get_list_dictionaries_usecase, usecase)

    response = await client.get("/campaigns/new")

    assert response.status_code == 200
    assert "Create campaign" in response.text
    assert "Domain A" in response.text
    assert 'value="10"' in response.text
    assert 'value="20"' in response.text
    assert 'value="30"' in response.text
    assert "offer_weight" in response.text


@pytest.mark.asyncio
async def test_create_campaign_post_parses_form_and_redirects(app, client):
    list_usecase = FakeListDictionariesUseCase(dictionary_items())
    create_usecase = FakeCreateCampaignUseCase(campaign())
    override_dependency(app, get_list_dictionaries_usecase, list_usecase)
    override_dependency(app, get_create_campaign_usecase, create_usecase)

    body, headers = form_body(
        [
            ("name", "Campaign A"),
            ("country_code", "US"),
            ("domain_id", "10"),
            ("group_id", "20"),
            ("source_id", "30"),
            ("geo_redirect_url", "https://example.com"),
            ("offer_id", "101"),
            ("offer_weight", "40"),
            ("offer_id", "102"),
            ("offer_weight", "60"),
            ("offer_id", ""),
            ("offer_weight", ""),
        ]
    )

    response = await client.post(
        "/campaigns",
        content=body,
        headers=headers,
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/campaigns/55"
    assert create_usecase.received_command == CreateCampaignCommand(
        name="Campaign A",
        country_code="US",
        domain_id=10,
        group_id=20,
        source_id=30,
        geo_redirect_url="https://example.com",
        offers=[
            CreateCampaignOfferDto(offer_id=101, weight=40),
            CreateCampaignOfferDto(offer_id=102, weight=60),
        ],
    )


@pytest.mark.asyncio
async def test_create_campaign_post_with_partial_offer_row_shows_error(app, client):
    list_usecase = FakeListDictionariesUseCase(dictionary_items())
    create_usecase = FakeCreateCampaignUseCase(campaign())
    override_dependency(app, get_list_dictionaries_usecase, list_usecase)
    override_dependency(app, get_create_campaign_usecase, create_usecase)

    body, headers = form_body(
        [
            ("name", "Campaign A"),
            ("country_code", "US"),
            ("domain_id", "1"),
            ("group_id", "2"),
            ("source_id", "3"),
            ("geo_redirect_url", "https://example.com"),
            ("offer_id", "101"),
            ("offer_weight", "40"),
            ("offer_id", "202"),
        ]
    )

    response = await client.post(
        "/campaigns",
        content=body,
        headers=headers,
    )

    assert response.status_code == 400
    assert "Each offer row needs both an offer ID and weight." in response.text
