from __future__ import annotations

import pytest

from src.api.dependencies import get_batch_update_stream_offers_usecase
from src.campaigns.dto import BatchUpdateStreamOffersCommand
from tests.integration.page_helpers import (
    FakeOfferActionUseCase,
    campaign,
    form_body,
    override_dependency,
)


@pytest.mark.asyncio
async def test_batch_update_offers_redirects_back_to_campaign(app, client):
    usecase = FakeOfferActionUseCase(campaign())
    override_dependency(app, get_batch_update_stream_offers_usecase, usecase)

    body, headers = form_body(
        [
            ("add_offer_ids", "333, 444"),
            ("enable_offer_id", "103"),
            ("remove_offer_id", "101"),
            ("remove_offer_id", "102"),
            ("pinned_offer_id", "333"),
            ("pinned_weight_333", "70"),
        ]
    )
    response = await client.post(
        "/campaigns/55/streams/12/offers/batch",
        content=body,
        headers=headers,
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/campaigns/55"
    assert usecase.received_command == BatchUpdateStreamOffersCommand(
        campaign_id=55,
        stream_id=12,
        add_offer_ids=[333, 444],
        enable_offer_ids={103},
        remove_offer_ids={101, 102},
        pinned_weights={333: 70},
    )
