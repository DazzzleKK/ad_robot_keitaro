from __future__ import annotations

from urllib.parse import urljoin

import httpx

from src.campaigns.dto import CreateCampaignCommand
from src.campaigns.exceptions import KeitaroOperationError
from src.keitaro.mappers import map_created_campaign, map_dictionary_items, map_stream, map_stream_list
from src.keitaro.payloads import (
    build_create_campaign_payload,
    build_geo_redirect_stream_payload,
    build_offers_stream_payload,
    build_replace_stream_offers_payload,
)
from src.keitaro.protocols import KeitaroClientProtocol
from src.keitaro.schemas import KeitaroCreatedCampaign, KeitaroDictionaryItem, KeitaroOfferWeight, KeitaroStream


class HttpKeitaroClient(KeitaroClientProtocol):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=30.0)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def fetch_domains(self) -> list[KeitaroDictionaryItem]:
        return await self._fetch_dictionary_items("fetch_domains", "/admin_api/v1/domains")

    async def fetch_groups(self) -> list[KeitaroDictionaryItem]:
        return await self._fetch_dictionary_items("fetch_groups", "/admin_api/v1/groups?type=campaigns")

    async def fetch_sources(self) -> list[KeitaroDictionaryItem]:
        return await self._fetch_dictionary_items("fetch_sources", "/admin_api/v1/traffic_sources")

    async def fetch_offers(self) -> list[KeitaroDictionaryItem]:
        return await self._fetch_dictionary_items("fetch_offers", "/admin_api/v1/offers")

    async def create_campaign(self, command: CreateCampaignCommand) -> KeitaroCreatedCampaign:
        payload = build_create_campaign_payload(command)
        data = await self._request_json("create_campaign", "POST", "/admin_api/v1/campaigns", json=payload)
        campaign = map_created_campaign(data)
        streams = [
            await self._create_campaign_stream(
                campaign.id,
                build_geo_redirect_stream_payload(command),
            ),
            await self._create_campaign_stream(
                campaign.id,
                build_offers_stream_payload(command),
            ),
        ]
        return KeitaroCreatedCampaign(id=campaign.id, name=campaign.name, streams=streams)

    async def _create_campaign_stream(
        self,
        keitaro_campaign_id: int,
        payload: dict[str, object],
    ) -> KeitaroStream:
        payload = {"campaign_id": keitaro_campaign_id, **payload}
        data = await self._request_json(
            "create_campaign_stream",
            "POST",
            "/admin_api/v1/streams",
            json=payload,
        )
        return map_stream(data, operation="create_campaign_stream")

    async def fetch_campaign_streams(self, keitaro_campaign_id: int) -> list[KeitaroStream]:
        path = f"/admin_api/v1/campaigns/{keitaro_campaign_id}/streams"
        data = await self._request_json("fetch_campaign_streams", "GET", path)
        return map_stream_list(data, operation="fetch_campaign_streams")

    async def replace_stream_offers(
        self,
        keitaro_campaign_id: int,
        keitaro_stream_id: int,
        offers: list[KeitaroOfferWeight],
    ) -> None:
        path = f"/admin_api/v1/streams/{keitaro_stream_id}"
        payload = build_replace_stream_offers_payload(offers)
        await self._request_json("replace_stream_offers", "PUT", path, json=payload)

    async def _fetch_dictionary_items(
        self,
        operation: str,
        path: str,
    ) -> list[KeitaroDictionaryItem]:
        data = await self._request_json(operation, "GET", path)
        return map_dictionary_items(data, operation=operation)

    async def _request_json(
        self,
        operation: str,
        method: str,
        path: str,
        *,
        json: object | None = None,
    ) -> object:
        url = urljoin(self._base_url.rstrip("/") + "/", path.lstrip("/"))
        try:
            response = await self._client.request(
                method,
                url,
                headers={"Api-Key": self._api_key, "Connection": "close"},
                json=json,
            )
        except httpx.HTTPError as exc:
            raise self._operation_error(operation, f"{operation} failed while calling Keitaro") from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise self._operation_error(
                operation,
                f"{operation} failed with status {response.status_code}",
            ) from exc

        try:
            return response.json()
        except (TypeError, ValueError) as exc:
            raise self._operation_error(operation, f"{operation} returned invalid JSON") from exc

    def _operation_error(self, operation: str, message: str, *, cause: BaseException | None = None) -> KeitaroOperationError:
        return KeitaroOperationError(operation=operation, message=message, cause=cause)
