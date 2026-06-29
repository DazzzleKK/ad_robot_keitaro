from __future__ import annotations

import json

import httpx
import pytest

from src.campaigns.dto import CreateCampaignCommand, CreateCampaignOfferDto
from src.campaigns.enums import StreamKind
from src.campaigns.exceptions import KeitaroOperationError
from src.keitaro.client import HttpKeitaroClient
from src.keitaro.schemas import KeitaroCreatedCampaign, KeitaroDictionaryItem, KeitaroOfferWeight, KeitaroStream


def _build_command() -> CreateCampaignCommand:
    return CreateCampaignCommand(
        name="Campaign",
        country_code="US",
        domain_id=1,
        group_id=2,
        source_id=3,
        geo_redirect_url="https://example.com",
        offers=[CreateCampaignOfferDto(offer_id=101, weight=40), CreateCampaignOfferDto(offer_id=102, weight=60)],
    )


def _build_adapter(handler):
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    adapter = HttpKeitaroClient(
        base_url="https://keitaro.example",
        api_key="api-key",
        http_client=client,
    )
    return adapter, client


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "path", "payload"),
    [
        ("fetch_domains", "/admin_api/v1/domains", [{"id": 10, "name": "Domain A"}]),
        ("fetch_groups", "/admin_api/v1/groups?type=campaigns", [{"id": 20, "name": "Group A"}]),
        ("fetch_sources", "/admin_api/v1/traffic_sources", [{"id": 30, "name": "Source A"}]),
        ("fetch_offers", "/admin_api/v1/offers", [{"id": 40, "name": "Offer A"}]),
    ],
)
async def test_dictionary_methods_send_api_key_header_and_map_items(method_name, path, payload):
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        assert request.headers["Api-Key"] == "api-key"
        assert request.method == "GET"
        assert request.url.raw_path.decode() == path
        return httpx.Response(200, json=payload)

    adapter, client = _build_adapter(handler)
    try:
        result = await getattr(adapter, method_name)()
    finally:
        await client.aclose()

    assert seen_requests
    assert result == [KeitaroDictionaryItem(id=payload[0]["id"], name=payload[0]["name"])]


@pytest.mark.asyncio
async def test_create_campaign_sends_expected_payload_and_maps_response():
    command = _build_command()
    expected_campaign_payload = {
        "name": "Campaign",
        "type": "position",
        "state": "active",
        "domain_id": 1,
        "group_id": 2,
        "traffic_source_id": 3,
        "cost_type": "CPC",
        "cost_value": 0,
        "cost_currency": "USD",
        "cost_auto": True,
    }
    seen_stream_payloads: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Api-Key"] == "api-key"
        if request.url.path == "/admin_api/v1/campaigns":
            assert request.method == "POST"
            payload = json.loads(request.content.decode())
            alias = payload.pop("alias")
            assert alias.startswith("campaign-")
            assert len(alias) == len("campaign-") + 8
            assert payload == expected_campaign_payload
            return httpx.Response(200, json={"id": 77, "name": "Campaign"})

        assert request.method == "POST"
        assert request.url.path == "/admin_api/v1/streams"
        payload = json.loads(request.content.decode())
        seen_stream_payloads.append(payload)
        assert payload["campaign_id"] == 77
        if len(seen_stream_payloads) == 1:
            assert payload["schema"] == "redirect"
            assert payload["action_payload"] == "https://example.com"
            assert payload["filters"] == [{"name": "country", "mode": "accept", "payload": ["US"]}]
            return httpx.Response(
                200,
                json={
                    "id": 91,
                    "name": "US -> Google",
                    "schema": "redirect",
                    "offers": [],
                },
            )

        assert payload["schema"] == "landings"
        assert payload["offers"] == [
            {"offer_id": 101, "share": 40},
            {"offer_id": 102, "share": 60},
        ]
        return httpx.Response(
            200,
            json={
                "id": 92,
                "name": "Offer fallback",
                "schema": "landings",
                "offers": [
                    {"offer_id": 101, "share": 40},
                    {"offer_id": 102, "share": 60},
                ],
            },
        )

    adapter, client = _build_adapter(handler)
    try:
        created = await adapter.create_campaign(command)
    finally:
        await client.aclose()

    assert created == KeitaroCreatedCampaign(
        id=77,
        name="Campaign",
        streams=[
            KeitaroStream(id=91, name="US -> Google", kind=StreamKind.GEO_REDIRECT, offers=[]),
            KeitaroStream(
                id=92,
                name="Offer fallback",
                kind=StreamKind.OFFERS,
                offers=[
                    KeitaroOfferWeight(offer_id=101, weight=40),
                    KeitaroOfferWeight(offer_id=102, weight=60),
                ],
            ),
        ],
    )


@pytest.mark.asyncio
async def test_fetch_campaign_streams_maps_response_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Api-Key"] == "api-key"
        assert request.method == "GET"
        assert request.url.path == "/admin_api/v1/campaigns/77/streams"
        return httpx.Response(
            200,
            json=[
                {
                    "id": 91,
                    "name": "Campaign geo redirect",
                    "schema": "redirect",
                    "offers": [],
                },
                {
                    "id": 92,
                    "name": "Campaign offers",
                    "schema": "landings",
                    "offers": [
                        {"offer_id": 101, "share": 40},
                        {"offer_id": 102, "share": 60, "state": "disabled"},
                        {"offer_id": 103, "share": 0, "state": "active"},
                    ],
                },
            ],
        )

    adapter, client = _build_adapter(handler)
    try:
        streams = await adapter.fetch_campaign_streams(77)
    finally:
        await client.aclose()

    assert streams == [
        KeitaroStream(id=91, name="Campaign geo redirect", kind=StreamKind.GEO_REDIRECT, offers=[]),
        KeitaroStream(
            id=92,
            name="Campaign offers",
            kind=StreamKind.OFFERS,
            offers=[
                KeitaroOfferWeight(offer_id=101, weight=40),
                KeitaroOfferWeight(offer_id=102, weight=60, active=False),
                KeitaroOfferWeight(offer_id=103, weight=0, active=False),
            ],
        ),
    ]


@pytest.mark.asyncio
async def test_replace_stream_offers_sends_expected_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Api-Key"] == "api-key"
        assert request.method == "PUT"
        assert request.url.path == "/admin_api/v1/streams/92"
        assert json.loads(request.content.decode()) == {
            "offers": [{"offer_id": 101, "share": 55}],
        }
        return httpx.Response(200, json={"status": "ok"})

    adapter, client = _build_adapter(handler)
    try:
        result = await adapter.replace_stream_offers(77, 92, [KeitaroOfferWeight(offer_id=101, weight=55)])
    finally:
        await client.aclose()

    assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "handler"),
    [
        (
            "fetch_domains",
            lambda request: (_ for _ in ()).throw(httpx.ConnectError("boom", request=request)),
        ),
        ("fetch_groups", lambda request: httpx.Response(500, json={"error": "nope"})),
        ("fetch_sources", lambda request: httpx.Response(200, text="not-json")),
        ("fetch_offers", lambda request: httpx.Response(200, json=[{"name": "Offer A"}])),
        ("create_campaign", lambda request: httpx.Response(200, json={"id": 77})),
    ],
)
async def test_http_errors_and_payload_shape_errors_translate_to_operation_error(method_name, handler):
    def wrapped_handler(request: httpx.Request) -> httpx.Response:
        result = handler(request)
        if isinstance(result, httpx.Response):
            return result
        raise AssertionError("unreachable")

    adapter, client = _build_adapter(wrapped_handler)
    try:
        with pytest.raises(KeitaroOperationError) as error:
            if method_name == "create_campaign":
                await adapter.create_campaign(_build_command())
            else:
                await getattr(adapter, method_name)()
    finally:
        await client.aclose()

    assert error.value.operation == method_name
