from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from src.campaigns.dto import (
    BatchUpdateStreamOffersCommand,
    CampaignDto,
    CampaignStreamDto,
    CreateCampaignCommand,
    OfferSearchResultDto,
    StreamOfferDto,
)
from src.campaigns.enums import StreamKind
from src.dictionaries.dto import DictionaryItemDto, DictionaryType


@dataclass
class FakeListCampaignsUseCase:
    campaigns: list[CampaignDto]
    calls: int = 0

    async def execute(self) -> list[CampaignDto]:
        self.calls += 1
        return list(self.campaigns)


@dataclass
class FakeListDictionariesUseCase:
    items: list[DictionaryItemDto]
    calls: int = 0

    async def execute(self) -> list[DictionaryItemDto]:
        self.calls += 1
        return list(self.items)


@dataclass
class FakeRefreshDictionariesUseCase:
    items: list[DictionaryItemDto] | Exception
    calls: int = 0

    async def execute(self) -> list[DictionaryItemDto]:
        self.calls += 1
        if isinstance(self.items, Exception):
            raise self.items
        return list(self.items)


@dataclass
class FakeCreateCampaignUseCase:
    campaign: CampaignDto
    received_command: CreateCampaignCommand | None = None

    async def execute(self, command: CreateCampaignCommand) -> CampaignDto:
        self.received_command = command
        return self.campaign


@dataclass
class FakeCampaignEditorUseCase:
    campaign: CampaignDto | Exception
    received_campaign_id: int | None = None

    async def execute(self, campaign_id: int) -> CampaignDto:
        self.received_campaign_id = campaign_id
        if isinstance(self.campaign, Exception):
            raise self.campaign
        return self.campaign


@dataclass
class FakeFetchCampaignStreamsUseCase:
    campaign: CampaignDto
    received_campaign_id: int | None = None

    async def execute(self, campaign_id: int) -> CampaignDto:
        self.received_campaign_id = campaign_id
        return self.campaign


@dataclass
class FakeOfferActionUseCase:
    campaign: CampaignDto
    received_command: BatchUpdateStreamOffersCommand | None = None

    async def execute(self, command: BatchUpdateStreamOffersCommand) -> CampaignDto:
        self.received_command = command
        return self.campaign


@dataclass
class FakeSearchKeitaroOffersUseCase:
    offers: list[OfferSearchResultDto] | Exception
    received_query: str | None = None

    async def execute(self, query: str) -> list[OfferSearchResultDto]:
        self.received_query = query
        if isinstance(self.offers, Exception):
            raise self.offers
        return list(self.offers)


def dictionary_items() -> list[DictionaryItemDto]:
    return [
        DictionaryItemDto(
            id=1,
            dictionary_type=DictionaryType.DOMAINS,
            keitaro_id=10,
            name="Domain A",
        ),
        DictionaryItemDto(
            id=2,
            dictionary_type=DictionaryType.GROUPS,
            keitaro_id=20,
            name="Group A",
        ),
        DictionaryItemDto(
            id=3,
            dictionary_type=DictionaryType.SOURCES,
            keitaro_id=30,
            name="Source A",
        ),
        DictionaryItemDto(
            id=4,
            dictionary_type=DictionaryType.OFFERS,
            keitaro_id=40,
            name="Offer A",
        ),
    ]


def campaign() -> CampaignDto:
    return CampaignDto(
        id=55,
        keitaro_campaign_id=99,
        name="Campaign A",
        domain_id=1,
        group_id=2,
        source_id=3,
        streams=[
            CampaignStreamDto(
                id=11,
                keitaro_stream_id=101,
                name="Campaign A geo redirect",
                kind=StreamKind.GEO_REDIRECT,
                offers=[],
            ),
            CampaignStreamDto(
                id=12,
                keitaro_stream_id=102,
                name="Campaign A offers",
                kind=StreamKind.OFFERS,
                offers=[
                    StreamOfferDto(
                        id=21,
                        keitaro_offer_id=101,
                        weight=40,
                        active=True,
                    ),
                    StreamOfferDto(
                        id=22,
                        keitaro_offer_id=102,
                        weight=60,
                        active=False,
                    ),
                ],
            ),
        ],
    )


def override_dependency(app, dependency, value) -> None:
    async def override():
        return value

    app.dependency_overrides[dependency] = override


def form_body(fields: list[tuple[str, str]]) -> tuple[str, dict[str, str]]:
    return urlencode(fields), {"Content-Type": "application/x-www-form-urlencoded"}
