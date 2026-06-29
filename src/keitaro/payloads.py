from __future__ import annotations

from collections.abc import Sequence
import re
from uuid import uuid4

from src.campaigns.dto import CreateCampaignCommand, CreateCampaignOfferDto
from src.keitaro.schemas import KeitaroOfferWeight


def build_create_campaign_payload(command: CreateCampaignCommand) -> dict[str, object]:
    return {
        "name": command.name,
        "alias": _build_campaign_alias(command.name),
        "type": "position",
        "state": "active",
        "domain_id": command.domain_id,
        "group_id": command.group_id,
        "traffic_source_id": command.source_id,
        "cost_type": "CPC",
        "cost_value": 0,
        "cost_currency": "USD",
        "cost_auto": True,
    }


def build_geo_redirect_stream_payload(command: CreateCampaignCommand) -> dict[str, object]:
    return {
        "type": "regular",
        "name": f"{command.country_code.upper()} -> Google",
        "position": 1,
        "state": "active",
        "schema": "redirect",
        "action_type": "http",
        "action_payload": command.geo_redirect_url,
        "collect_clicks": True,
        "filter_or": False,
        "offer_selection": "before_click",
        "filters": [
            {
                "name": "country",
                "mode": "accept",
                "payload": [command.country_code.upper()],
            }
        ],
        "triggers": [],
        "landings": [],
        "offers": [],
    }


def build_offers_stream_payload(command: CreateCampaignCommand) -> dict[str, object]:
    return {
        "type": "regular",
        "name": "Offer fallback",
        "position": 2,
        "state": "active",
        "schema": "landings",
        "action_type": "http",
        "action_payload": "",
        "collect_clicks": True,
        "filter_or": False,
        "offer_selection": "before_click",
        "filters": [],
        "triggers": [],
        "landings": [],
        "offers": [_build_offer_payload(offer) for offer in command.offers],
    }


def build_replace_stream_offers_payload(offers: Sequence[KeitaroOfferWeight]) -> dict[str, object]:
    return {
        "offers": [_build_offer_payload(offer) for offer in offers],
    }


def _build_campaign_alias(name: str) -> str:
    alias = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not alias:
        alias = "campaign"
    return f"{alias[:48]}-{uuid4().hex[:8]}"


def _build_offer_payload(offer: CreateCampaignOfferDto | KeitaroOfferWeight) -> dict[str, int]:
    return {
        "offer_id": offer.offer_id,
        "share": offer.weight,
    }
