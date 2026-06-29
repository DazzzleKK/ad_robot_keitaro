from __future__ import annotations

import pytest

from src.campaigns.dto import (
    BatchUpdateStreamOffersCommand,
    CampaignDto,
    CampaignStreamDto,
    CreateCampaignCommand,
    CreateCampaignOfferDto,
    StreamOfferDto,
)
from src.campaigns.enums import StreamKind
from src.campaigns.snapshots import CreatedCampaignSnapshot
from src.campaigns.services import normalize_batch_update_stream_offers_command
from src.campaigns.usecases import (
    BatchUpdateStreamOffersUseCase,
    CreateCampaignUseCase,
    FetchCampaignStreamsUseCase,
    GetCampaignEditorUseCase,
    SearchKeitaroOffersUseCase,
)
from src.keitaro.schemas import (
    KeitaroCreatedCampaign,
    KeitaroDictionaryItem,
    KeitaroOfferWeight,
)
from tests.fakes import FakeKeitaroClient


def _build_command(name: str = "Campaign") -> CreateCampaignCommand:
    return CreateCampaignCommand(
        name=name,
        country_code="US",
        domain_id=1,
        group_id=2,
        source_id=3,
        geo_redirect_url="https://example.com",
        offers=[
            CreateCampaignOfferDto(offer_id=101, weight=40),
            CreateCampaignOfferDto(offer_id=102, weight=60),
        ],
    )


def _build_batch_command(
    *,
    add_offer_ids: list[int] | None = None,
    enable_offer_ids: set[int] | None = None,
    remove_offer_ids: set[int] | None = None,
    pinned_weights: dict[int, int] | None = None,
) -> BatchUpdateStreamOffersCommand:
    return BatchUpdateStreamOffersCommand(
        campaign_id=1,
        stream_id=12,
        add_offer_ids=add_offer_ids or [],
        enable_offer_ids=enable_offer_ids or set(),
        remove_offer_ids=remove_offer_ids or set(),
        pinned_weights=pinned_weights or {},
    )


def _build_campaign(created: KeitaroCreatedCampaign, *, active_offer_ids: set[int] | None = None) -> CampaignDto:
    active_offer_ids = active_offer_ids or {101, 102}
    return CampaignDto(
        id=1,
        keitaro_campaign_id=created.id,
        name="Campaign",
        domain_id=1,
        group_id=2,
        source_id=3,
        streams=[
            CampaignStreamDto(
                id=11,
                keitaro_stream_id=created.streams[0].id,
                name=created.streams[0].name,
                kind=StreamKind.GEO_REDIRECT,
                offers=[],
            ),
            CampaignStreamDto(
                id=12,
                keitaro_stream_id=created.streams[1].id,
                name=created.streams[1].name,
                kind=StreamKind.OFFERS,
                offers=[
                    StreamOfferDto(id=21, keitaro_offer_id=101, weight=40, active=101 in active_offer_ids),
                    StreamOfferDto(id=22, keitaro_offer_id=102, weight=60, active=102 in active_offer_ids),
                ],
            ),
        ],
    )


class RecordingCampaignRepository:
    def __init__(self, campaign: CampaignDto | None = None) -> None:
        self.campaigns: dict[int, CampaignDto] = {}
        self.created_args: tuple[CreateCampaignCommand, CreatedCampaignSnapshot] | None = None
        self.get_calls: list[int] = []
        self.get_by_keitaro_calls: list[int] = []
        self.upsert_calls: list[tuple[int, list, dict[int, dict[int, int]] | None]] = []
        self.upsert_result: CampaignDto | None = None
        if campaign is not None:
            self.campaigns[campaign.id] = campaign

    async def create_from_snapshot(
        self,
        command: CreateCampaignCommand,
        result: CreatedCampaignSnapshot,
    ) -> CampaignDto:
        self.created_args = (command, result)
        campaign = CampaignDto(
            id=len(self.campaigns) + 1,
            keitaro_campaign_id=result.campaign_id,
            name=result.name,
            domain_id=command.domain_id,
            group_id=command.group_id,
            source_id=command.source_id,
            streams=[
                CampaignStreamDto(
                    id=index + 1,
                    keitaro_stream_id=stream.stream_id,
                    name=stream.name,
                    kind=stream.kind,
                    offers=[
                        StreamOfferDto(
                            id=offer_index + 1,
                            keitaro_offer_id=offer.offer_id,
                            weight=offer.weight,
                            active=offer.active,
                        )
                        for offer_index, offer in enumerate(stream.offers)
                    ],
                )
                for index, stream in enumerate(result.streams)
            ],
        )
        self.campaigns[campaign.id] = campaign
        return campaign

    async def get(self, campaign_id: int) -> CampaignDto:
        self.get_calls.append(campaign_id)
        return self.campaigns[campaign_id]

    async def get_by_keitaro_id(self, keitaro_campaign_id: int) -> CampaignDto:
        self.get_by_keitaro_calls.append(keitaro_campaign_id)
        return next(
            campaign
            for campaign in self.campaigns.values()
            if campaign.keitaro_campaign_id == keitaro_campaign_id
        )

    async def upsert_streams_snapshot(
        self,
        campaign_id: int,
        streams,
        pinned_weights_by_stream_id=None,
    ) -> CampaignDto:
        snapshot = list(streams)
        self.upsert_calls.append((campaign_id, snapshot, pinned_weights_by_stream_id))
        return self.upsert_result or self.campaigns[campaign_id]


@pytest.mark.asyncio
async def test_create_campaign_usecase_calls_client_and_repository():
    client = FakeKeitaroClient()
    repository = RecordingCampaignRepository()
    usecase = CreateCampaignUseCase(client=client, repository=repository)

    created = await usecase.execute(_build_command("First"))

    assert repository.created_args is not None
    command, result = repository.created_args
    assert command.name == "First"
    assert result.campaign_id == 1
    assert created.keitaro_campaign_id == 1
    assert [offer.active for offer in created.streams[1].offers] == [True, True]


@pytest.mark.asyncio
async def test_get_campaign_editor_usecase_returns_repository_campaign():
    created = await FakeKeitaroClient().create_campaign(_build_command())
    repository = RecordingCampaignRepository(_build_campaign(created))
    usecase = GetCampaignEditorUseCase(repository=repository)

    campaign = await usecase.execute(1)

    assert campaign.id == 1
    assert repository.get_calls == [1]


@pytest.mark.asyncio
async def test_search_keitaro_offers_usecase_filters_by_id_or_name():
    client = FakeKeitaroClient(
        offers=[
            KeitaroDictionaryItem(id=101, name="Alpha offer"),
            KeitaroDictionaryItem(id=202, name="Beta offer"),
            KeitaroDictionaryItem(id=303, name="Gamma offer"),
        ],
    )
    usecase = SearchKeitaroOffersUseCase(client=client)

    found_by_name = await usecase.execute("alp")
    found_by_id = await usecase.execute("202")

    assert [(offer.id, offer.name, offer.label) for offer in found_by_name] == [
        (101, "Alpha offer", "101 - Alpha offer"),
    ]
    assert [(offer.id, offer.name, offer.label) for offer in found_by_id] == [
        (202, "Beta offer", "202 - Beta offer"),
    ]


def test_normalize_batch_update_stream_offers_command_drops_removed_pinned_weights():
    command = _build_batch_command(
        remove_offer_ids={101},
        pinned_weights={101: 60, 102: 40},
    )

    normalized = normalize_batch_update_stream_offers_command(command)

    assert normalized == BatchUpdateStreamOffersCommand(
        campaign_id=1,
        stream_id=12,
        add_offer_ids=[],
        enable_offer_ids=set(),
        remove_offer_ids={101},
        pinned_weights={102: 40},
    )


@pytest.mark.asyncio
async def test_fetch_campaign_streams_usecase_refreshes_snapshot():
    client = FakeKeitaroClient()
    created = await client.create_campaign(_build_command())
    await client.replace_stream_offers(
        created.id,
        created.streams[1].id,
        [KeitaroOfferWeight(offer_id=102, weight=55)],
    )

    repository = RecordingCampaignRepository(_build_campaign(created))
    usecase = FetchCampaignStreamsUseCase(client=client, repository=repository)

    updated = await usecase.execute(1)

    assert repository.get_calls == [1]
    assert repository.upsert_calls[0][0] == 1
    assert [(offer.offer_id, offer.weight) for offer in repository.upsert_calls[0][1][1].offers] == [
        (102, 55),
    ]
    assert updated == repository.campaigns[1]


@pytest.mark.asyncio
async def test_batch_update_stream_offers_replaces_client_stream_with_equal_weights():
    client = FakeKeitaroClient()
    created = await client.create_campaign(_build_command())
    repository = RecordingCampaignRepository(_build_campaign(created))
    repository.upsert_result = repository.campaigns[1]
    usecase = BatchUpdateStreamOffersUseCase(client=client, repository=repository)

    updated = await usecase.execute(
        _build_batch_command(
            add_offer_ids=[303, 404],
            remove_offer_ids={101},
        )
    )

    streams = await client.fetch_campaign_streams(1)
    assert [(offer.offer_id, offer.weight) for offer in streams[1].offers] == [
        (102, 34),
        (303, 33),
        (404, 33),
    ]
    assert repository.upsert_calls[0][0] == 1
    assert repository.upsert_calls[0][2] == {created.streams[1].id: {}}
    assert [(offer.offer_id, offer.weight) for offer in repository.upsert_calls[0][1][0].offers] == [
        (102, 34),
        (303, 33),
        (404, 33),
    ]
    assert updated == repository.upsert_result


@pytest.mark.asyncio
async def test_batch_update_stream_offers_enables_inactive_and_respects_pinned_weights():
    client = FakeKeitaroClient()
    created = await client.create_campaign(_build_command())
    campaign = _build_campaign(created, active_offer_ids={101})
    repository = RecordingCampaignRepository(campaign)
    repository.upsert_result = campaign
    usecase = BatchUpdateStreamOffersUseCase(client=client, repository=repository)

    updated = await usecase.execute(
        _build_batch_command(
            add_offer_ids=[303],
            enable_offer_ids={102},
            pinned_weights={101: 60},
        )
    )

    streams = await client.fetch_campaign_streams(1)
    assert [(offer.offer_id, offer.weight) for offer in streams[1].offers] == [
        (101, 60),
        (102, 20),
        (303, 20),
    ]
    assert repository.upsert_calls[0][2] == {created.streams[1].id: {101: 60}}
    assert [(offer.offer_id, offer.weight) for offer in repository.upsert_calls[0][1][0].offers] == [
        (101, 60),
        (102, 20),
        (303, 20),
    ]
    assert updated == repository.upsert_result


@pytest.mark.asyncio
async def test_batch_update_stream_offers_drops_removed_pinned_weights():
    client = FakeKeitaroClient()
    created = await client.create_campaign(_build_command())
    repository = RecordingCampaignRepository(_build_campaign(created))
    repository.upsert_result = repository.campaigns[1]
    usecase = BatchUpdateStreamOffersUseCase(client=client, repository=repository)

    await usecase.execute(
        _build_batch_command(
            remove_offer_ids={101},
            pinned_weights={101: 60},
        )
    )

    streams = await client.fetch_campaign_streams(1)
    assert [(offer.offer_id, offer.weight) for offer in streams[1].offers] == [
        (102, 100),
    ]
    assert repository.upsert_calls[0][2] == {created.streams[1].id: {}}
