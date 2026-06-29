from __future__ import annotations

import pytest

from src.campaigns.dto import CreateCampaignCommand, CreateCampaignOfferDto
from src.campaigns.enums import StreamKind
from src.campaigns.exceptions import KeitaroOperationError
from src.keitaro.schemas import KeitaroDictionaryItem, KeitaroOfferWeight
from tests.fakes import FakeKeitaroClient


def _build_command(name: str = "Campaign") -> CreateCampaignCommand:
    return CreateCampaignCommand(
        name=name,
        country_code="US",
        domain_id=1,
        group_id=2,
        source_id=3,
        geo_redirect_url="https://example.com",
        offers=[CreateCampaignOfferDto(offer_id=101, weight=40), CreateCampaignOfferDto(offer_id=102, weight=60)],
    )


@pytest.mark.asyncio
async def test_create_campaign_persists_deterministic_streams_and_fetches_back():
    client = FakeKeitaroClient()

    created = await client.create_campaign(_build_command("First"))
    second = await client.create_campaign(_build_command("Second"))
    streams = await client.fetch_campaign_streams(created.id)

    assert created.id == 1
    assert [stream.id for stream in created.streams] == [1, 2]
    assert created.streams[0].kind is StreamKind.GEO_REDIRECT
    assert created.streams[1].kind is StreamKind.OFFERS
    assert [offer.offer_id for offer in created.streams[1].offers] == [101, 102]
    assert second.id == 2
    assert [stream.id for stream in second.streams] == [3, 4]
    assert streams == created.streams


@pytest.mark.asyncio
async def test_replace_stream_offers_updates_only_target_stream():
    client = FakeKeitaroClient()
    created = await client.create_campaign(_build_command())
    offers_stream = created.streams[1]

    await client.replace_stream_offers(
        created.id,
        offers_stream.id,
        [KeitaroOfferWeight(offer_id=102, weight=55)],
    )

    streams = await client.fetch_campaign_streams(created.id)
    assert [stream.id for stream in streams] == [1, 2]
    assert streams[0].offers == []
    assert [(offer.offer_id, offer.weight) for offer in streams[1].offers] == [(102, 55)]


@pytest.mark.asyncio
async def test_missing_campaign_or_stream_raises_keitaro_operation_error():
    client = FakeKeitaroClient()
    created = await client.create_campaign(_build_command())

    with pytest.raises(KeitaroOperationError) as campaign_error:
        await client.fetch_campaign_streams(999)
    assert campaign_error.value.operation == "fetch_campaign_streams"

    with pytest.raises(KeitaroOperationError) as stream_error:
        await client.replace_stream_offers(created.id, 999, [])
    assert stream_error.value.operation == "replace_stream_offers"

    with pytest.raises(KeitaroOperationError) as missing_campaign_error:
        await client.replace_stream_offers(999, created.streams[1].id, [])
    assert missing_campaign_error.value.operation == "replace_stream_offers"


@pytest.mark.asyncio
async def test_dictionary_fetch_methods_return_defaults_and_custom_lists():
    custom_domains = [KeitaroDictionaryItem(id=10, name="Domain X")]
    custom_groups = [KeitaroDictionaryItem(id=20, name="Group X")]
    custom_sources = [KeitaroDictionaryItem(id=30, name="Source X")]
    custom_offers = [KeitaroDictionaryItem(id=40, name="Offer X")]

    custom_client = FakeKeitaroClient(
        domains=custom_domains,
        groups=custom_groups,
        sources=custom_sources,
        offers=custom_offers,
    )
    default_client = FakeKeitaroClient()

    assert await custom_client.fetch_domains() == custom_domains
    assert await custom_client.fetch_groups() == custom_groups
    assert await custom_client.fetch_sources() == custom_sources
    assert await custom_client.fetch_offers() == custom_offers

    assert await default_client.fetch_domains()
    assert await default_client.fetch_groups()
    assert await default_client.fetch_sources()
    assert await default_client.fetch_offers()
