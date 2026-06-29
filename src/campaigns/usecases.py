from __future__ import annotations

from dataclasses import dataclass

from src.campaigns.dto import (
    BatchUpdateStreamOffersCommand,
    CampaignDto,
    CreateCampaignCommand,
    OfferSearchResultDto,
    OfferWeightDto,
)
from src.campaigns.enums import StreamKind
from src.campaigns.exceptions import CampaignStreamNotFoundError
from src.campaigns.mappers import (
    created_campaign_snapshot_from_keitaro,
    stream_snapshots_from_keitaro,
)
from src.campaigns.protocols import CampaignRepositoryProtocol
from src.campaigns.services import (
    build_equal_weight_offer_batch,
    normalize_batch_update_stream_offers_command,
)
from src.campaigns.snapshots import CampaignOfferSnapshot, CampaignStreamSnapshot
from src.keitaro.protocols import KeitaroClientProtocol
from src.keitaro.schemas import KeitaroOfferWeight


@dataclass(slots=True)
class ListCampaignsUseCase:
    repository: CampaignRepositoryProtocol

    async def execute(self) -> list[CampaignDto]:
        return await self.repository.list_campaigns()


@dataclass(slots=True)
class CreateCampaignUseCase:
    client: KeitaroClientProtocol
    repository: CampaignRepositoryProtocol

    async def execute(self, command: CreateCampaignCommand) -> CampaignDto:
        result = await self.client.create_campaign(command)
        return await self.repository.create_from_snapshot(
            command,
            created_campaign_snapshot_from_keitaro(result),
        )


@dataclass(slots=True)
class GetCampaignEditorUseCase:
    repository: CampaignRepositoryProtocol

    async def execute(self, campaign_id: int) -> CampaignDto:
        return await self.repository.get(campaign_id)


@dataclass(slots=True)
class SearchKeitaroOffersUseCase:
    client: KeitaroClientProtocol

    async def execute(self, query: str) -> list[OfferSearchResultDto]:
        normalized_query = query.strip().lower()
        offers = await self.client.fetch_offers()
        matched_offers = [
            offer
            for offer in offers
            if (
                not normalized_query
                or normalized_query in str(offer.id)
                or normalized_query in offer.name.lower()
            )
        ][:20]
        return [
            OfferSearchResultDto(
                id=offer.id,
                name=offer.name,
                label=f"{offer.id} - {offer.name}",
            )
            for offer in matched_offers
        ]


@dataclass(slots=True)
class FetchCampaignStreamsUseCase:
    client: KeitaroClientProtocol
    repository: CampaignRepositoryProtocol

    async def execute(self, campaign_id: int) -> CampaignDto:
        campaign = await self.repository.get(campaign_id)
        streams = await self.client.fetch_campaign_streams(campaign.keitaro_campaign_id)
        return await self.repository.upsert_streams_snapshot(
            campaign_id,
            stream_snapshots_from_keitaro(streams),
        )


@dataclass(slots=True)
class BatchUpdateStreamOffersUseCase:
    client: KeitaroClientProtocol
    repository: CampaignRepositoryProtocol

    async def execute(self, command: BatchUpdateStreamOffersCommand) -> CampaignDto:
        command = normalize_batch_update_stream_offers_command(command)
        campaign = await self.repository.get(command.campaign_id)
        stream = _find_stream_by_id(campaign, command.stream_id)
        if stream is None or stream.kind is not StreamKind.OFFERS:
            raise CampaignStreamNotFoundError(stream_id=command.stream_id)

        current_offers = [
            OfferWeightDto(
                offer_id=offer.keitaro_offer_id,
                weight=offer.weight,
                active=offer.active,
            )
            for offer in stream.offers
        ]
        updated_offers = build_equal_weight_offer_batch(
            current_offers,
            add_offer_ids=command.add_offer_ids,
            enable_offer_ids=command.enable_offer_ids,
            remove_offer_ids=command.remove_offer_ids,
            pinned_weights=command.pinned_weights,
        )
        await self.client.replace_stream_offers(
            campaign.keitaro_campaign_id,
            stream.keitaro_stream_id,
            _offer_weights_to_keitaro(updated_offers),
        )
        return await self.repository.upsert_streams_snapshot(
            campaign.id,
            [
                CampaignStreamSnapshot(
                    stream_id=stream.keitaro_stream_id,
                    name=stream.name,
                    kind=stream.kind,
                    offers=[
                        CampaignOfferSnapshot(
                            offer_id=offer.offer_id,
                            weight=offer.weight,
                            active=offer.active,
                        )
                        for offer in updated_offers
                    ],
                )
            ],
            pinned_weights_by_stream_id={stream.keitaro_stream_id: command.pinned_weights},
        )


def _find_stream_by_id(campaign: CampaignDto, stream_id: int):
    for stream in campaign.streams:
        if stream.id == stream_id:
            return stream
    return None


def _offer_weights_to_keitaro(offers: list[OfferWeightDto]) -> list[KeitaroOfferWeight]:
    return [
        KeitaroOfferWeight(
            offer_id=offer.offer_id,
            weight=offer.weight,
            active=offer.active,
        )
        for offer in offers
    ]
