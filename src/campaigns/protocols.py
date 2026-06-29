from typing import Protocol

from src.campaigns.dto import CampaignDto, CreateCampaignCommand
from src.campaigns.snapshots import CampaignStreamSnapshot, CreatedCampaignSnapshot


class CampaignRepositoryProtocol(Protocol):
    async def list_campaigns(self) -> list[CampaignDto]: ...

    async def create_from_snapshot(
        self,
        command: CreateCampaignCommand,
        result: CreatedCampaignSnapshot,
    ) -> CampaignDto: ...

    async def get(self, campaign_id: int) -> CampaignDto: ...

    async def get_by_keitaro_id(self, keitaro_campaign_id: int) -> CampaignDto: ...

    async def upsert_streams_snapshot(
        self,
        campaign_id: int,
        streams: list[CampaignStreamSnapshot],
        pinned_weights_by_stream_id: dict[int, dict[int, int]] | None = None,
    ) -> CampaignDto: ...

