from src.campaigns.snapshots import (
    CampaignOfferSnapshot,
    CampaignStreamSnapshot,
    CreatedCampaignSnapshot,
)
from src.keitaro.schemas import KeitaroCreatedCampaign, KeitaroStream


def created_campaign_snapshot_from_keitaro(
    campaign: KeitaroCreatedCampaign,
) -> CreatedCampaignSnapshot:
    return CreatedCampaignSnapshot(
        campaign_id=campaign.id,
        name=campaign.name,
        streams=stream_snapshots_from_keitaro(campaign.streams),
    )


def stream_snapshots_from_keitaro(
    streams: list[KeitaroStream],
) -> list[CampaignStreamSnapshot]:
    return [
        CampaignStreamSnapshot(
            stream_id=stream.id,
            name=stream.name,
            kind=stream.kind,
            offers=[
                CampaignOfferSnapshot(
                    offer_id=offer.offer_id,
                    weight=offer.weight,
                    active=offer.active,
                )
                for offer in stream.offers
            ],
        )
        for stream in streams
    ]
