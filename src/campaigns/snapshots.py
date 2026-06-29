from dataclasses import dataclass

from src.campaigns.enums import StreamKind


@dataclass(frozen=True)
class CampaignOfferSnapshot:
    offer_id: int
    weight: int
    active: bool = True


@dataclass(frozen=True)
class CampaignStreamSnapshot:
    stream_id: int
    name: str
    kind: StreamKind
    offers: list[CampaignOfferSnapshot]


@dataclass(frozen=True)
class CreatedCampaignSnapshot:
    campaign_id: int
    name: str
    streams: list[CampaignStreamSnapshot]
