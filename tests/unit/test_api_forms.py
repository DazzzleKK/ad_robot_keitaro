from __future__ import annotations

import pytest

from src.api.forms import (
    FormParseError,
    build_batch_update_stream_offers_command,
    parse_batch_update_stream_offers_form,
)
from src.campaigns.dto import BatchUpdateStreamOffersCommand


def test_parse_batch_update_stream_offers_form_collects_offer_actions():
    form = {
        "add_offer_ids": "333, 444\n555;666",
        "enable_offer_id": ["101", " 102 ", ""],
        "remove_offer_id": ["201", "202"],
        "pinned_offer_id": ["333", "444"],
        "pinned_weight_333": "70",
        "pinned_weight_444": "30",
    }

    parsed = parse_batch_update_stream_offers_form(form)

    assert parsed.add_offer_ids == [333, 444, 555, 666]
    assert parsed.enable_offer_ids == {101, 102}
    assert parsed.remove_offer_ids == {201, 202}
    assert parsed.pinned_weights == {333: 70, 444: 30}


def test_parse_batch_update_stream_offers_form_keeps_raw_pinned_weights():
    form = {
        "remove_offer_id": ["201"],
        "pinned_offer_id": ["201", "202"],
        "pinned_weight_201": "70",
        "pinned_weight_202": "30",
    }

    parsed = parse_batch_update_stream_offers_form(form)

    assert parsed.remove_offer_ids == {201}
    assert parsed.pinned_weights == {201: 70, 202: 30}


def test_build_batch_update_stream_offers_command_adds_route_ids():
    command = build_batch_update_stream_offers_command(
        campaign_id=55,
        stream_id=12,
        form={
            "add_offer_ids": "333, 444",
            "enable_offer_id": ["103"],
            "remove_offer_id": ["101"],
            "pinned_offer_id": ["333"],
            "pinned_weight_333": "70",
        },
    )

    assert command == BatchUpdateStreamOffersCommand(
        campaign_id=55,
        stream_id=12,
        add_offer_ids=[333, 444],
        enable_offer_ids={103},
        remove_offer_ids={101},
        pinned_weights={333: 70},
    )


def test_parse_batch_update_stream_offers_form_rejects_non_integer_values():
    with pytest.raises(FormParseError, match="Offer IDs and weights must be integers."):
        parse_batch_update_stream_offers_form({"add_offer_ids": "333, bad"})
