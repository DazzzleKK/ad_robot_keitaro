from __future__ import annotations

from src.campaigns.dto import BatchUpdateStreamOffersCommand, OfferWeightDto
from src.campaigns.exceptions import CampaignOfferBatchError


def normalize_batch_update_stream_offers_command(
    command: BatchUpdateStreamOffersCommand,
) -> BatchUpdateStreamOffersCommand:
    return BatchUpdateStreamOffersCommand(
        campaign_id=command.campaign_id,
        stream_id=command.stream_id,
        add_offer_ids=command.add_offer_ids,
        enable_offer_ids=command.enable_offer_ids,
        remove_offer_ids=command.remove_offer_ids,
        pinned_weights={
            offer_id: weight
            for offer_id, weight in command.pinned_weights.items()
            if offer_id not in command.remove_offer_ids
        },
    )


def build_equal_weight_offer_batch(
    current_offers: list[OfferWeightDto],
    *,
    add_offer_ids: list[int],
    enable_offer_ids: set[int],
    remove_offer_ids: set[int],
    pinned_weights: dict[int, int],
) -> list[OfferWeightDto]:
    final_offer_ids: list[int] = []
    seen_offer_ids: set[int] = set()

    for offer in current_offers:
        if (
            offer.offer_id in remove_offer_ids
            or offer.offer_id in seen_offer_ids
            or (not offer.active and offer.offer_id not in enable_offer_ids)
        ):
            continue
        final_offer_ids.append(offer.offer_id)
        seen_offer_ids.add(offer.offer_id)

    for offer_id in add_offer_ids:
        if offer_id in remove_offer_ids or offer_id in seen_offer_ids:
            continue
        final_offer_ids.append(offer_id)
        seen_offer_ids.add(offer_id)

    if not final_offer_ids:
        raise CampaignOfferBatchError("At least one active offer is required.")

    _validate_pinned_weights(pinned_weights, final_offer_ids)
    unpinned_offer_ids = [
        offer_id
        for offer_id in final_offer_ids
        if offer_id not in pinned_weights
    ]
    weights_by_offer_id = dict(pinned_weights)
    remaining_weight = 100 - sum(pinned_weights.values())
    if unpinned_offer_ids:
        if remaining_weight <= 0:
            raise CampaignOfferBatchError("Pinned weights must leave weight for unpinned offers.")
        weights_by_offer_id.update(
            {
                offer_id: weight
                for offer_id, weight in zip(
                    unpinned_offer_ids,
                    _equal_weights(total=remaining_weight, count=len(unpinned_offer_ids)),
                    strict=True,
                )
            }
        )
    elif remaining_weight != 0:
        raise CampaignOfferBatchError("Pinned weights must add up to 100.")

    return [
        OfferWeightDto(
            offer_id=offer_id,
            weight=weights_by_offer_id[offer_id],
        )
        for offer_id in final_offer_ids
    ]


def _validate_pinned_weights(
    pinned_weights: dict[int, int],
    final_offer_ids: list[int],
) -> None:
    final_offer_id_set = set(final_offer_ids)
    invalid_offer_ids = [
        offer_id
        for offer_id in pinned_weights
        if offer_id not in final_offer_id_set
    ]
    if invalid_offer_ids:
        raise CampaignOfferBatchError("Pinned offers must be active after batch update.")
    if any(weight <= 0 for weight in pinned_weights.values()):
        raise CampaignOfferBatchError("Pinned weights must be positive integers.")
    if sum(pinned_weights.values()) > 100:
        raise CampaignOfferBatchError("Pinned weights cannot exceed 100.")


def _equal_weights(*, total: int, count: int) -> list[int]:
    base_weight = total // count
    remainder = total % count
    return [
        base_weight + (1 if index < remainder else 0)
        for index in range(count)
    ]
