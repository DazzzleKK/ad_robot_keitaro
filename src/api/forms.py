from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from starlette.datastructures import FormData

from src.campaigns.dto import (
    BatchUpdateStreamOffersCommand,
    CreateCampaignCommand,
    CreateCampaignOfferDto,
)

_MIN_OFFER_ROWS = 3


class FormParseError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class OfferRowForm:
    offer_id: str = ""
    weight: str = ""


@dataclass(frozen=True, slots=True)
class CreateCampaignFormState:
    name: str = ""
    country_code: str = ""
    domain_id: str = ""
    group_id: str = ""
    source_id: str = ""
    geo_redirect_url: str = ""
    offers: list[OfferRowForm] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BatchUpdateStreamOffersForm:
    add_offer_ids: list[int]
    enable_offer_ids: set[int]
    remove_offer_ids: set[int]
    pinned_weights: dict[int, int]


def parse_create_campaign_form(form: FormData | Mapping[str, object]) -> CreateCampaignCommand:
    state = build_create_campaign_form_state(form)
    offers = _parse_offer_rows(form)
    if not offers:
        raise FormParseError("At least one offer row is required.")

    try:
        return CreateCampaignCommand(
            name=_require_text(state.name, "name"),
            country_code=_require_text(state.country_code, "country_code"),
            domain_id=int(_require_text(state.domain_id, "domain_id")),
            group_id=int(_require_text(state.group_id, "group_id")),
            source_id=int(_require_text(state.source_id, "source_id")),
            geo_redirect_url=_require_text(state.geo_redirect_url, "geo_redirect_url"),
            offers=offers,
        )
    except ValueError as exc:
        raise FormParseError(str(exc)) from exc


def build_create_campaign_form_state(
    form: FormData | Mapping[str, object],
) -> CreateCampaignFormState:
    offers = _collect_offer_rows(form)
    if len(offers) < _MIN_OFFER_ROWS:
        offers.extend([OfferRowForm() for _ in range(_MIN_OFFER_ROWS - len(offers))])

    return CreateCampaignFormState(
        name=_get_text(form, "name"),
        country_code=_get_text(form, "country_code"),
        domain_id=_get_text(form, "domain_id"),
        group_id=_get_text(form, "group_id"),
        source_id=_get_text(form, "source_id"),
        geo_redirect_url=_get_text(form, "geo_redirect_url"),
        offers=offers,
    )


def parse_batch_update_stream_offers_form(
    form: FormData | Mapping[str, object],
) -> BatchUpdateStreamOffersForm:
    try:
        return BatchUpdateStreamOffersForm(
            add_offer_ids=_parse_delimited_offer_ids(_get_text(form, "add_offer_ids")),
            enable_offer_ids=_parse_offer_id_set(form, "enable_offer_id"),
            remove_offer_ids=_parse_offer_id_set(form, "remove_offer_id"),
            pinned_weights=_parse_pinned_weights(form),
        )
    except ValueError as exc:
        raise FormParseError("Offer IDs and weights must be integers.") from exc


def build_batch_update_stream_offers_command(
    *,
    campaign_id: int,
    stream_id: int,
    form: FormData | Mapping[str, object],
) -> BatchUpdateStreamOffersCommand:
    parsed = parse_batch_update_stream_offers_form(form)
    return BatchUpdateStreamOffersCommand(
        campaign_id=campaign_id,
        stream_id=stream_id,
        add_offer_ids=parsed.add_offer_ids,
        enable_offer_ids=parsed.enable_offer_ids,
        remove_offer_ids=parsed.remove_offer_ids,
        pinned_weights=parsed.pinned_weights,
    )


def _parse_offer_rows(form: FormData | Mapping[str, object]) -> list[CreateCampaignOfferDto]:
    offer_ids = _get_list(form, "offer_id")
    weights = _get_list(form, "offer_weight")
    row_count = max(len(offer_ids), len(weights))
    offers: list[CreateCampaignOfferDto] = []

    for index in range(row_count):
        raw_offer_id = offer_ids[index] if index < len(offer_ids) else ""
        raw_weight = weights[index] if index < len(weights) else ""

        if not raw_offer_id and not raw_weight:
            continue
        if not raw_offer_id or not raw_weight:
            raise FormParseError("Each offer row needs both an offer ID and weight.")

        try:
            offers.append(CreateCampaignOfferDto(offer_id=int(raw_offer_id), weight=int(raw_weight)))
        except ValueError as exc:
            raise FormParseError("Offer IDs and weights must be integers.") from exc

    return offers


def _collect_offer_rows(form: FormData | Mapping[str, object]) -> list[OfferRowForm]:
    offer_ids = _get_list(form, "offer_id")
    weights = _get_list(form, "offer_weight")
    row_count = max(len(offer_ids), len(weights))
    rows: list[OfferRowForm] = []

    for index in range(row_count):
        rows.append(
            OfferRowForm(
                offer_id=offer_ids[index] if index < len(offer_ids) else "",
                weight=weights[index] if index < len(weights) else "",
            )
        )
    return rows


def _parse_delimited_offer_ids(raw_value: str) -> list[int]:
    parts = raw_value.replace("\n", ",").replace(";", ",").split(",")
    return [
        int(part.strip())
        for part in parts
        if part.strip()
    ]


def _parse_offer_id_set(form: FormData | Mapping[str, object], key: str) -> set[int]:
    return {
        int(raw_offer_id.strip())
        for raw_offer_id in _get_list(form, key)
        if raw_offer_id.strip()
    }


def _parse_pinned_weights(form: FormData | Mapping[str, object]) -> dict[int, int]:
    pinned_weights: dict[int, int] = {}
    for raw_offer_id in _get_list(form, "pinned_offer_id"):
        offer_id = int(raw_offer_id.strip())
        weight = int(_get_text(form, f"pinned_weight_{offer_id}").strip())
        pinned_weights[offer_id] = weight
    return pinned_weights


def _get_text(form: FormData | Mapping[str, object], key: str) -> str:
    value = _get_value(form, key)
    return "" if value is None else str(value)


def _get_list(form: FormData | Mapping[str, object], key: str) -> list[str]:
    if hasattr(form, "getlist"):
        return [str(item) for item in form.getlist(key)]  # type: ignore[attr-defined]

    value = form.get(key)
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [str(value)]


def _get_value(form: FormData | Mapping[str, object], key: str) -> object | None:
    if hasattr(form, "get"):
        return form.get(key)  # type: ignore[call-arg]
    return None


def _require_text(value: str, field_name: str) -> str:
    if not value.strip():
        raise FormParseError(f"{field_name} is required.")
    return value.strip()
