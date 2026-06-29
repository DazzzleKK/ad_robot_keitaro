from __future__ import annotations

from dataclasses import replace

from src.campaigns.dto import CreateCampaignCommand
from src.campaigns.exceptions import KeitaroOperationError
from src.campaigns.enums import StreamKind
from src.keitaro.protocols import KeitaroClientProtocol
from src.keitaro.schemas import KeitaroCreatedCampaign, KeitaroDictionaryItem, KeitaroOfferWeight, KeitaroStream


class FakeKeitaroClient(KeitaroClientProtocol):
    def __init__(
        self,
        *,
        domains: list[KeitaroDictionaryItem] | None = None,
        groups: list[KeitaroDictionaryItem] | None = None,
        sources: list[KeitaroDictionaryItem] | None = None,
        offers: list[KeitaroDictionaryItem] | None = None,
    ) -> None:
        self._domains = list(domains) if domains is not None else [
            KeitaroDictionaryItem(id=1, name="Domain A"),
            KeitaroDictionaryItem(id=2, name="Domain B"),
        ]
        self._groups = list(groups) if groups is not None else [
            KeitaroDictionaryItem(id=10, name="Group A"),
            KeitaroDictionaryItem(id=11, name="Group B"),
        ]
        self._sources = list(sources) if sources is not None else [
            KeitaroDictionaryItem(id=20, name="Source A"),
            KeitaroDictionaryItem(id=21, name="Source B"),
        ]
        self._offers = list(offers) if offers is not None else [
            KeitaroDictionaryItem(id=100, name="Offer A"),
            KeitaroDictionaryItem(id=101, name="Offer B"),
        ]
        self._campaigns: dict[int, KeitaroCreatedCampaign] = {}
        self._next_campaign_id = 1
        self._next_stream_id = 1

    async def fetch_domains(self) -> list[KeitaroDictionaryItem]:
        return list(self._domains)

    async def fetch_groups(self) -> list[KeitaroDictionaryItem]:
        return list(self._groups)

    async def fetch_sources(self) -> list[KeitaroDictionaryItem]:
        return list(self._sources)

    async def fetch_offers(self) -> list[KeitaroDictionaryItem]:
        return list(self._offers)

    async def create_campaign(self, command: CreateCampaignCommand) -> KeitaroCreatedCampaign:
        campaign_id = self._next_campaign_id
        self._next_campaign_id += 1

        geo_redirect_stream = KeitaroStream(
            id=self._next_stream_id,
            name=f"{command.name} geo redirect",
            kind=StreamKind.GEO_REDIRECT,
            offers=[],
        )
        self._next_stream_id += 1

        offers_stream = KeitaroStream(
            id=self._next_stream_id,
            name=f"{command.name} offers",
            kind=StreamKind.OFFERS,
            offers=[
                KeitaroOfferWeight(
                    offer_id=offer.offer_id,
                    weight=offer.weight,
                )
                for offer in command.offers
            ],
        )
        self._next_stream_id += 1

        created = KeitaroCreatedCampaign(
            id=campaign_id,
            name=command.name,
            streams=[geo_redirect_stream, offers_stream],
        )
        self._campaigns[campaign_id] = _clone_campaign(created)
        return _clone_campaign(created)

    async def fetch_campaign_streams(self, keitaro_campaign_id: int) -> list[KeitaroStream]:
        campaign = self._campaigns.get(keitaro_campaign_id)
        if campaign is None:
            raise KeitaroOperationError(
                operation="fetch_campaign_streams",
                message=f"Campaign {keitaro_campaign_id} not found",
            )
        return [_clone_stream(stream) for stream in campaign.streams]

    async def replace_stream_offers(
        self,
        keitaro_campaign_id: int,
        keitaro_stream_id: int,
        offers: list[KeitaroOfferWeight],
    ) -> None:
        campaign = self._campaigns.get(keitaro_campaign_id)
        if campaign is None:
            raise KeitaroOperationError(
                operation="replace_stream_offers",
                message=f"Campaign {keitaro_campaign_id} not found",
            )

        stream_index = _find_stream_index(campaign.streams, keitaro_stream_id)
        if stream_index is None:
            raise KeitaroOperationError(
                operation="replace_stream_offers",
                message=f"Stream {keitaro_stream_id} not found in campaign {keitaro_campaign_id}",
            )

        updated_streams = list(campaign.streams)
        updated_streams[stream_index] = replace(updated_streams[stream_index], offers=list(offers))
        self._campaigns[keitaro_campaign_id] = replace(campaign, streams=updated_streams)


def _clone_campaign(campaign: KeitaroCreatedCampaign) -> KeitaroCreatedCampaign:
    return replace(campaign, streams=[_clone_stream(stream) for stream in campaign.streams])


def _clone_stream(stream: KeitaroStream) -> KeitaroStream:
    return replace(
        stream,
        offers=[
            KeitaroOfferWeight(
                offer_id=offer.offer_id,
                weight=offer.weight,
                active=offer.active,
            )
            for offer in stream.offers
        ],
    )


def _find_stream_index(streams: list[KeitaroStream], keitaro_stream_id: int) -> int | None:
    for index, stream in enumerate(streams):
        if stream.id == keitaro_stream_id:
            return index
    return None
