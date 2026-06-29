from __future__ import annotations

from collections.abc import Mapping, Sequence

from src.campaigns.enums import StreamKind
from src.campaigns.exceptions import KeitaroOperationError
from src.keitaro.schemas import KeitaroCreatedCampaign, KeitaroDictionaryItem, KeitaroOfferWeight, KeitaroStream


def map_dictionary_items(item: object, *, operation: str) -> list[KeitaroDictionaryItem]:
    return [
        map_dictionary_item(dictionary_item, operation=operation)
        for dictionary_item in _expect_sequence(item, operation)
    ]


def map_dictionary_item(
    item: object,
    *,
    operation: str,
) -> KeitaroDictionaryItem:
    data = _expect_mapping(item, operation)
    try:
        return KeitaroDictionaryItem(id=int(data["id"]), name=str(data["name"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise _operation_error(operation, f"{operation} returned an invalid dictionary item") from exc


def map_created_campaign(item: object) -> KeitaroCreatedCampaign:
    data = _expect_mapping(item, "create_campaign")
    try:
        return KeitaroCreatedCampaign(
            id=int(data["id"]),
            name=str(data["name"]),
            streams=map_stream_list(data.get("streams", []), operation="create_campaign"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _operation_error("create_campaign", "create_campaign returned an invalid campaign") from exc


def map_stream_list(item: object, *, operation: str) -> list[KeitaroStream]:
    data = _expect_sequence(item, operation)
    return [map_stream(stream, operation=operation) for stream in data]


def map_stream(item: object, *, operation: str) -> KeitaroStream:
    data = _expect_mapping(item, operation)
    try:
        return KeitaroStream(
            id=int(data["id"]),
            name=str(data["name"]),
            kind=_map_stream_kind(data),
            offers=[
                map_offer_weight(offer, operation=operation)
                for offer in _expect_sequence(data["offers"], operation)
            ],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _operation_error(operation, f"{operation} returned an invalid stream") from exc


def map_offer_weight(item: object, *, operation: str) -> KeitaroOfferWeight:
    data = _expect_mapping(item, operation)
    try:
        weight = data.get("share", data.get("weight"))
        weight_value = int(weight)
        return KeitaroOfferWeight(
            offer_id=int(data["offer_id"]),
            weight=weight_value,
            active=_map_offer_active(data, weight=weight_value),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _operation_error(operation, f"{operation} returned an invalid stream offer") from exc


def _map_offer_active(data: Mapping[str, object], *, weight: int) -> bool:
    if weight <= 0:
        return False

    state = data.get("state")
    if state is not None:
        return str(state).lower() == "active"

    enabled = data.get("enabled")
    if isinstance(enabled, bool):
        return enabled

    status = data.get("status")
    if status is not None:
        return str(status).lower() == "active"

    return True


def _map_stream_kind(data: Mapping[str, object]) -> StreamKind:
    schema = data.get("schema")
    if schema == "redirect":
        return StreamKind.GEO_REDIRECT
    return StreamKind.OFFERS


def _expect_mapping(item: object, operation: str) -> Mapping[str, object]:
    if not isinstance(item, Mapping):
        raise _operation_error(operation, f"{operation} returned a non-object JSON value")
    return item


def _expect_sequence(item: object, operation: str) -> Sequence[object]:
    if not isinstance(item, Sequence) or isinstance(item, (str, bytes, bytearray)):
        raise _operation_error(operation, f"{operation} returned a non-list JSON value")
    return item


def _operation_error(operation: str, message: str) -> KeitaroOperationError:
    return KeitaroOperationError(operation=operation, message=message)
