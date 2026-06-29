from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.campaigns.dto import CampaignDto, CampaignStreamDto, CreateCampaignCommand, StreamOfferDto
from src.campaigns.exceptions import CampaignNotFoundError
from src.campaigns.models import CampaignModel, CampaignStreamModel, StreamOfferModel
from src.campaigns.protocols import CampaignRepositoryProtocol
from src.campaigns.snapshots import (
    CampaignOfferSnapshot,
    CampaignStreamSnapshot,
    CreatedCampaignSnapshot,
)


@dataclass(slots=True)
class CampaignRepository(CampaignRepositoryProtocol):
    _session: Session

    async def list_campaigns(self) -> list[CampaignDto]:
        stmt = (
            select(CampaignModel)
            .options(
                selectinload(CampaignModel.streams).selectinload(CampaignStreamModel.offers),
            )
            .order_by(CampaignModel.id.desc())
        )
        result = self._session.execute(stmt)
        return [_campaign_to_dto(campaign) for campaign in result.scalars().all()]

    async def create_from_snapshot(
        self,
        command: CreateCampaignCommand,
        result: CreatedCampaignSnapshot,
    ) -> CampaignDto:
        campaign = CampaignModel(
            keitaro_campaign_id=result.campaign_id,
            name=result.name,
            domain_id=command.domain_id,
            group_id=command.group_id,
            source_id=command.source_id,
        )
        campaign.streams = [_stream_model_from_snapshot(stream) for stream in result.streams]
        self._session.add(campaign)
        self._session.flush()
        return _campaign_to_dto(campaign)

    async def get(self, campaign_id: int) -> CampaignDto:
        campaign = self._get_campaign_by_id(campaign_id)
        return _campaign_to_dto(campaign)

    async def get_by_keitaro_id(self, keitaro_campaign_id: int) -> CampaignDto:
        campaign = self._get_campaign_by_keitaro_id(keitaro_campaign_id)
        return _campaign_to_dto(campaign)

    async def upsert_streams_snapshot(
        self,
        campaign_id: int,
        streams: list[CampaignStreamSnapshot],
        pinned_weights_by_stream_id: dict[int, dict[int, int]] | None = None,
    ) -> CampaignDto:
        campaign = self._get_campaign_by_id(campaign_id)
        stream_by_keitaro_id = {stream.keitaro_stream_id: stream for stream in campaign.streams}
        pinned_weights_by_stream_id = pinned_weights_by_stream_id or {}

        for snapshot in streams:
            pinned_weights = pinned_weights_by_stream_id.get(snapshot.stream_id)
            stream = self._upsert_stream(
                campaign=campaign,
                snapshot=snapshot,
                stream_by_keitaro_id=stream_by_keitaro_id,
            )
            fetched_offer_ids = self._upsert_stream_offers(
                stream=stream,
                snapshot=snapshot,
                pinned_weights=pinned_weights,
            )
            self._deactivate_missing_offers(
                stream=stream,
                fetched_offer_ids=fetched_offer_ids,
                clear_pinned_weights=pinned_weights is not None,
            )

        self._session.flush()
        return _campaign_to_dto(campaign)

    def _upsert_stream(
        self,
        *,
        campaign: CampaignModel,
        snapshot: CampaignStreamSnapshot,
        stream_by_keitaro_id: dict[int, CampaignStreamModel],
    ) -> CampaignStreamModel:
        stream = stream_by_keitaro_id.get(snapshot.stream_id)
        if stream is None:
            stream = CampaignStreamModel(
                campaign=campaign,
                keitaro_stream_id=snapshot.stream_id,
                name=snapshot.name,
                kind=snapshot.kind,
            )
            self._session.add(stream)
            stream_by_keitaro_id[snapshot.stream_id] = stream
            return stream

        stream.name = snapshot.name
        stream.kind = snapshot.kind
        return stream

    def _upsert_stream_offers(
        self,
        *,
        stream: CampaignStreamModel,
        snapshot: CampaignStreamSnapshot,
        pinned_weights: dict[int, int] | None,
    ) -> set[int]:
        offer_by_keitaro_id = {offer.keitaro_offer_id: offer for offer in stream.offers}
        fetched_offer_ids: set[int] = set()
        for offer_snapshot in snapshot.offers:
            fetched_offer_ids.add(offer_snapshot.offer_id)
            offer = offer_by_keitaro_id.get(offer_snapshot.offer_id)
            if offer is None:
                offer = self._create_stream_offer(
                    stream=stream,
                    offer_snapshot=offer_snapshot,
                    pinned_weights=pinned_weights,
                )
                offer_by_keitaro_id[offer_snapshot.offer_id] = offer
            else:
                self._update_stream_offer(
                    offer=offer,
                    offer_snapshot=offer_snapshot,
                    pinned_weights=pinned_weights,
                )
        return fetched_offer_ids

    def _create_stream_offer(
        self,
        *,
        stream: CampaignStreamModel,
        offer_snapshot: CampaignOfferSnapshot,
        pinned_weights: dict[int, int] | None,
    ) -> StreamOfferModel:
        offer = StreamOfferModel(
            stream=stream,
            keitaro_offer_id=offer_snapshot.offer_id,
            weight=offer_snapshot.weight,
            active=offer_snapshot.active,
            pinned_weight=_pinned_weight_for_offer(
                offer_id=offer_snapshot.offer_id,
                pinned_weights=pinned_weights,
            ),
        )
        self._session.add(offer)
        return offer

    def _update_stream_offer(
        self,
        *,
        offer: StreamOfferModel,
        offer_snapshot: CampaignOfferSnapshot,
        pinned_weights: dict[int, int] | None,
    ) -> None:
        offer.weight = offer_snapshot.weight
        offer.active = offer_snapshot.active
        if pinned_weights is not None:
            offer.pinned_weight = pinned_weights.get(offer_snapshot.offer_id)

    def _deactivate_missing_offers(
        self,
        *,
        stream: CampaignStreamModel,
        fetched_offer_ids: set[int],
        clear_pinned_weights: bool,
    ) -> None:
        for offer in stream.offers:
            if offer.keitaro_offer_id in fetched_offer_ids:
                continue
            offer.active = False
            if clear_pinned_weights:
                offer.pinned_weight = None

    def _get_campaign_by_id(self, campaign_id: int) -> CampaignModel:
        stmt = (
            select(CampaignModel)
            .where(CampaignModel.id == campaign_id)
            .options(
                selectinload(CampaignModel.streams).selectinload(CampaignStreamModel.offers),
            )
        )
        result = self._session.execute(stmt)
        campaign = result.scalar_one_or_none()
        if campaign is None:
            raise CampaignNotFoundError(campaign_id=campaign_id)
        return campaign

    def _get_campaign_by_keitaro_id(self, keitaro_campaign_id: int) -> CampaignModel:
        stmt = (
            select(CampaignModel)
            .where(CampaignModel.keitaro_campaign_id == keitaro_campaign_id)
            .options(
                selectinload(CampaignModel.streams).selectinload(CampaignStreamModel.offers),
            )
        )
        result = self._session.execute(stmt)
        campaign = result.scalar_one_or_none()
        if campaign is None:
            raise CampaignNotFoundError(campaign_id=keitaro_campaign_id)
        return campaign


def _stream_model_from_snapshot(stream: CampaignStreamSnapshot) -> CampaignStreamModel:
    stream_model = CampaignStreamModel(
        keitaro_stream_id=stream.stream_id,
        name=stream.name,
        kind=stream.kind,
    )
    stream_model.offers = [
        StreamOfferModel(
            keitaro_offer_id=offer.offer_id,
            weight=offer.weight,
            active=offer.active,
            pinned_weight=None,
        )
        for offer in stream.offers
    ]
    return stream_model


def _pinned_weight_for_offer(
    *,
    offer_id: int,
    pinned_weights: dict[int, int] | None,
) -> int | None:
    if pinned_weights is None:
        return None
    return pinned_weights.get(offer_id)


def _campaign_to_dto(model: CampaignModel) -> CampaignDto:
    return CampaignDto(
        id=model.id,
        keitaro_campaign_id=model.keitaro_campaign_id,
        name=model.name,
        domain_id=model.domain_id,
        group_id=model.group_id,
        source_id=model.source_id,
        streams=[
            _stream_to_dto(stream)
            for stream in sorted(
                model.streams,
                key=lambda item: (item.keitaro_stream_id, item.id),
            )
        ],
    )


def _stream_to_dto(model: CampaignStreamModel) -> CampaignStreamDto:
    return CampaignStreamDto(
        id=model.id,
        keitaro_stream_id=model.keitaro_stream_id,
        name=model.name,
        kind=model.kind,
        offers=[
            _offer_to_dto(offer)
            for offer in sorted(
                model.offers,
                key=lambda item: (item.keitaro_offer_id, item.id),
            )
        ],
    )


def _offer_to_dto(model: StreamOfferModel) -> StreamOfferDto:
    return StreamOfferDto(
        id=model.id,
        keitaro_offer_id=model.keitaro_offer_id,
        weight=model.weight,
        active=model.active,
        pinned_weight=model.pinned_weight,
    )
