from typing import Protocol

from src.campaigns.dto import CreateCampaignCommand
from src.keitaro.schemas import KeitaroCreatedCampaign, KeitaroDictionaryItem, KeitaroOfferWeight, KeitaroStream


class KeitaroClientProtocol(Protocol):
    async def fetch_domains(self) -> list[KeitaroDictionaryItem]: ...

    async def fetch_groups(self) -> list[KeitaroDictionaryItem]: ...

    async def fetch_sources(self) -> list[KeitaroDictionaryItem]: ...

    async def fetch_offers(self) -> list[KeitaroDictionaryItem]: ...

    async def create_campaign(self, command: CreateCampaignCommand) -> KeitaroCreatedCampaign: ...

    async def fetch_campaign_streams(self, keitaro_campaign_id: int) -> list[KeitaroStream]: ...

    async def replace_stream_offers(
        self,
        keitaro_campaign_id: int,
        keitaro_stream_id: int,
        offers: list[KeitaroOfferWeight],
    ) -> None: ...
