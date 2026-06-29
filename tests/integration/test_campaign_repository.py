from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.campaigns.dto import CreateCampaignCommand, CreateCampaignOfferDto
from src.campaigns.enums import StreamKind
from src.campaigns.exceptions import CampaignNotFoundError
from src.campaigns.models import CampaignModel, CampaignStreamModel, StreamOfferModel
from src.campaigns.repositories import CampaignRepository
from src.campaigns.snapshots import (
    CampaignOfferSnapshot,
    CampaignStreamSnapshot,
    CreatedCampaignSnapshot,
)
from src.database import Base, create_engine, create_sessionmaker


def _create_repository(
    tmp_path: Path,
) -> tuple[CampaignRepository, Engine, Session]:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    sessionmaker = create_sessionmaker(engine)
    session = sessionmaker()
    return CampaignRepository(session), engine, session


def _build_command() -> CreateCampaignCommand:
    return CreateCampaignCommand(
        name="Campaign",
        country_code="US",
        domain_id=11,
        group_id=22,
        source_id=33,
        geo_redirect_url="https://example.com",
        offers=[
            CreateCampaignOfferDto(offer_id=101, weight=40),
            CreateCampaignOfferDto(offer_id=102, weight=60),
        ],
    )


def _build_created_campaign() -> CreatedCampaignSnapshot:
    return CreatedCampaignSnapshot(
        campaign_id=5001,
        name="Campaign",
        streams=[
            CampaignStreamSnapshot(
                stream_id=7001,
                name="Geo redirect",
                kind=StreamKind.GEO_REDIRECT,
                offers=[],
            ),
            CampaignStreamSnapshot(
                stream_id=7002,
                name="Offers",
                kind=StreamKind.OFFERS,
                offers=[
                    CampaignOfferSnapshot(offer_id=101, weight=40),
                    CampaignOfferSnapshot(offer_id=102, weight=60),
                ],
            ),
        ],
    )


@pytest.mark.asyncio
async def test_create_and_get_campaign_round_trips_streams_and_offers(tmp_path: Path):
    repository, engine, session = _create_repository(tmp_path)
    try:
        created = await repository.create_from_snapshot(
            _build_command(),
            _build_created_campaign(),
        )

        assert created.keitaro_campaign_id == 5001
        assert created.streams[1].kind is StreamKind.OFFERS
        assert [offer.keitaro_offer_id for offer in created.streams[1].offers] == [
            101,
            102,
        ]

        loaded = await repository.get(created.id)
        assert loaded == created

        loaded_by_keitaro = await repository.get_by_keitaro_id(5001)
        assert loaded_by_keitaro == created

        campaign_rows = session.execute(select(CampaignModel)).scalars().all()
        stream_rows = session.execute(select(CampaignStreamModel)).scalars().all()
        offer_rows = session.execute(select(StreamOfferModel)).scalars().all()

        assert len(campaign_rows) == 1
        assert len(stream_rows) == 2
        assert len(offer_rows) == 2
    finally:
        session.close()
        engine.dispose()


@pytest.mark.asyncio
async def test_upsert_streams_snapshot_keeps_historical_offers_inactive(tmp_path: Path):
    repository, engine, session = _create_repository(tmp_path)
    try:
        created = await repository.create_from_snapshot(
            _build_command(),
            _build_created_campaign(),
        )

        snapshot = [
            CampaignStreamSnapshot(
                stream_id=7002,
                name="Offers",
                kind=StreamKind.OFFERS,
                offers=[CampaignOfferSnapshot(offer_id=102, weight=55)],
            )
        ]

        updated = await repository.upsert_streams_snapshot(created.id, snapshot)
        offers = updated.streams[1].offers
        assert [(offer.keitaro_offer_id, offer.weight, offer.active) for offer in offers] == [
            (101, 40, False),
            (102, 55, True),
        ]

    finally:
        session.close()
        engine.dispose()


@pytest.mark.asyncio
async def test_upsert_streams_snapshot_preserves_disabled_returned_offers(tmp_path: Path):
    repository, engine, session = _create_repository(tmp_path)
    try:
        created = await repository.create_from_snapshot(
            _build_command(),
            _build_created_campaign(),
        )

        snapshot = [
            CampaignStreamSnapshot(
                stream_id=7002,
                name="Offers",
                kind=StreamKind.OFFERS,
                offers=[
                    CampaignOfferSnapshot(offer_id=101, weight=50),
                    CampaignOfferSnapshot(offer_id=102, weight=50),
                    CampaignOfferSnapshot(offer_id=103, weight=0, active=False),
                ],
            )
        ]

        updated = await repository.upsert_streams_snapshot(created.id, snapshot)
        offers = updated.streams[1].offers

        assert [(offer.keitaro_offer_id, offer.weight, offer.active) for offer in offers] == [
            (101, 50, True),
            (102, 50, True),
            (103, 0, False),
        ]
    finally:
        session.close()
        engine.dispose()


@pytest.mark.asyncio
async def test_upsert_streams_snapshot_persists_and_preserves_pinned_weights(
    tmp_path: Path,
):
    repository, engine, session = _create_repository(tmp_path)
    try:
        created = await repository.create_from_snapshot(
            _build_command(),
            _build_created_campaign(),
        )

        snapshot = [
            CampaignStreamSnapshot(
                stream_id=7002,
                name="Offers",
                kind=StreamKind.OFFERS,
                offers=[
                    CampaignOfferSnapshot(offer_id=101, weight=70),
                    CampaignOfferSnapshot(offer_id=102, weight=30),
                ],
            )
        ]

        updated = await repository.upsert_streams_snapshot(
            created.id,
            snapshot,
            pinned_weights_by_stream_id={7002: {101: 70}},
        )
        offers_by_id = {
            offer.keitaro_offer_id: offer
            for offer in updated.streams[1].offers
        }
        assert offers_by_id[101].pinned_weight == 70
        assert offers_by_id[102].pinned_weight is None

        refreshed = await repository.upsert_streams_snapshot(created.id, snapshot)
        refreshed_offers_by_id = {
            offer.keitaro_offer_id: offer
            for offer in refreshed.streams[1].offers
        }
        assert refreshed_offers_by_id[101].pinned_weight == 70
        assert refreshed_offers_by_id[102].pinned_weight is None
    finally:
        session.close()
        engine.dispose()


@pytest.mark.asyncio
async def test_missing_campaign_raises_campaign_not_found(tmp_path: Path):
    repository, engine, session = _create_repository(tmp_path)
    try:
        with pytest.raises(CampaignNotFoundError) as exc_info:
            await repository.get(123)

        assert exc_info.value.campaign_id == 123
    finally:
        session.close()
        engine.dispose()
