from dataclasses import dataclass

from src.campaigns.enums import StreamKind


@dataclass(frozen=True)
class CreateCampaignOfferDto:
    offer_id: int
    weight: int


@dataclass(frozen=True)
class OfferWeightDto:
    offer_id: int
    weight: int
    active: bool = True


@dataclass(frozen=True)
class CreateCampaignCommand:
    name: str
    country_code: str
    domain_id: int
    group_id: int
    source_id: int
    geo_redirect_url: str
    offers: list[CreateCampaignOfferDto]


@dataclass(frozen=True)
class BatchUpdateStreamOffersCommand:
    campaign_id: int
    stream_id: int
    add_offer_ids: list[int]
    enable_offer_ids: set[int]
    remove_offer_ids: set[int]
    pinned_weights: dict[int, int]


@dataclass(frozen=True)
class StreamOfferDto:
    id: int
    keitaro_offer_id: int
    weight: int
    active: bool
    pinned_weight: int | None = None


@dataclass(frozen=True)
class CampaignStreamDto:
    id: int
    keitaro_stream_id: int
    name: str
    kind: StreamKind
    offers: list[StreamOfferDto]


@dataclass(frozen=True)
class CampaignDto:
    id: int
    keitaro_campaign_id: int
    name: str
    domain_id: int
    group_id: int
    source_id: int
    streams: list[CampaignStreamDto]


@dataclass(frozen=True)
class OfferSearchResultDto:
    id: int
    name: str
    label: str
