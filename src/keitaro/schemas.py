from dataclasses import dataclass

from src.campaigns.enums import StreamKind


@dataclass(frozen=True)
class KeitaroOfferWeight:
    offer_id: int
    weight: int
    active: bool = True


@dataclass(frozen=True)
class KeitaroDictionaryItem:
    id: int
    name: str


@dataclass(frozen=True)
class KeitaroStream:
    id: int
    name: str
    kind: StreamKind
    offers: list[KeitaroOfferWeight]


@dataclass(frozen=True)
class KeitaroCreatedCampaign:
    id: int
    name: str
    streams: list[KeitaroStream]
