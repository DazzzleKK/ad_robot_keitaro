from dataclasses import FrozenInstanceError
from inspect import iscoroutinefunction, signature

import pytest

from src.campaigns.dto import (
    CampaignDto,
    CampaignStreamDto,
    CreateCampaignCommand,
    CreateCampaignOfferDto,
    OfferWeightDto,
    StreamOfferDto,
)
from src.campaigns.enums import StreamKind
from src.campaigns.exceptions import (
    CampaignError,
    CampaignOfferBatchError,
    CampaignNotFoundError,
    CampaignStreamNotFoundError,
    DictionariesNotLoadedError,
    KeitaroOperationError,
)
from src.campaigns.protocols import CampaignRepositoryProtocol
from src.dictionaries.dto import DictionaryItemDto, DictionaryType
from src.dictionaries.protocols import DictionaryRepositoryProtocol
from src.keitaro.protocols import KeitaroClientProtocol
from src.keitaro.schemas import KeitaroCreatedCampaign, KeitaroDictionaryItem, KeitaroOfferWeight, KeitaroStream
from src.shared.exceptions import AppError, DomainError, InfraError


def test_shared_exception_hierarchy_and_codes():
    assert AppError.code == "internal_error"
    assert DomainError.code == "domain_error"
    assert InfraError.code == "infra_error"

    err = AppError("boom")
    assert err.message == "boom"
    assert str(err) == "boom"

    cause = ValueError("bad")
    chained = AppError("boom", cause=cause)
    assert chained.__cause__ is cause


def test_domain_enums_and_dtos_are_frozen():
    assert StreamKind.GEO_REDIRECT.value == "geo_redirect"
    assert StreamKind.OFFERS.value == "offers"
    assert DictionaryType.DOMAINS.value == "domains"
    assert DictionaryType.GROUPS.value == "groups"
    assert DictionaryType.SOURCES.value == "sources"
    assert DictionaryType.OFFERS.value == "offers"

    offer = CreateCampaignOfferDto(offer_id=10, weight=20)
    with pytest.raises(FrozenInstanceError):
        offer.weight = 30  # type: ignore[misc]

    offer_weight = OfferWeightDto(offer_id=10, weight=20)
    assert offer_weight.active is True

    command = CreateCampaignCommand(
        name="Campaign",
        country_code="US",
        domain_id=1,
        group_id=2,
        source_id=3,
        geo_redirect_url="https://example.com",
        offers=[offer],
    )
    assert command.offers == [offer]

    stream_offer = StreamOfferDto(id=1, keitaro_offer_id=10, weight=20, active=True)
    stream = CampaignStreamDto(
        id=2,
        keitaro_stream_id=30,
        name="Offers",
        kind=StreamKind.OFFERS,
        offers=[stream_offer],
    )
    campaign = CampaignDto(
        id=4,
        keitaro_campaign_id=5,
        name="Campaign",
        domain_id=1,
        group_id=2,
        source_id=3,
        streams=[stream],
    )

    assert campaign.streams[0].offers[0].active is True


def test_keitaro_and_dictionary_dtos_are_frozen():
    item = KeitaroDictionaryItem(id=1, name="Alpha")
    stream = KeitaroStream(
        id=2,
        name="Geo",
        kind=StreamKind.GEO_REDIRECT,
        offers=[KeitaroOfferWeight(offer_id=3, weight=50)],
    )
    created = KeitaroCreatedCampaign(id=4, name="Campaign", streams=[stream])
    dictionary_item = DictionaryItemDto(
        id=5,
        dictionary_type=DictionaryType.DOMAINS,
        keitaro_id=6,
        name="Domain",
    )

    assert item.name == "Alpha"
    assert created.streams[0].kind is StreamKind.GEO_REDIRECT
    assert dictionary_item.dictionary_type is DictionaryType.DOMAINS


def test_campaign_exception_codes_and_context_fields():
    base = CampaignError("campaign error")
    not_found = CampaignNotFoundError(campaign_id=1)
    stream_missing = CampaignStreamNotFoundError(stream_id=8)
    batch = CampaignOfferBatchError("bad batch")
    keitaro = KeitaroOperationError(message="kt failed", operation="create_campaign")
    dictionaries = DictionariesNotLoadedError()

    assert base.code == "campaign_error"
    assert not_found.code == "campaign_not_found"
    assert not_found.campaign_id == 1
    assert stream_missing.code == "campaign_stream_not_found"
    assert stream_missing.stream_id == 8
    assert batch.code == "campaign_offer_batch_error"
    assert keitaro.code == "keitaro_operation_error"
    assert keitaro.operation == "create_campaign"
    assert dictionaries.code == "dictionaries_not_loaded"


def test_protocol_signatures_match_public_contract():
    keitaro_methods = {
        "fetch_domains": ["self"],
        "fetch_groups": ["self"],
        "fetch_sources": ["self"],
        "fetch_offers": ["self"],
        "create_campaign": ["self", "command"],
        "fetch_campaign_streams": ["self", "keitaro_campaign_id"],
        "replace_stream_offers": ["self", "keitaro_campaign_id", "keitaro_stream_id", "offers"],
    }
    for method_name, params in keitaro_methods.items():
        method = getattr(KeitaroClientProtocol, method_name)
        assert iscoroutinefunction(method)
        assert list(signature(method).parameters) == params

    campaign_methods = {
        "list_campaigns": ["self"],
        "create_from_snapshot": ["self", "command", "result"],
        "get": ["self", "campaign_id"],
        "get_by_keitaro_id": ["self", "keitaro_campaign_id"],
        "upsert_streams_snapshot": ["self", "campaign_id", "streams", "pinned_weights_by_stream_id"],
    }
    for method_name, params in campaign_methods.items():
        method = getattr(CampaignRepositoryProtocol, method_name)
        assert iscoroutinefunction(method)
        assert list(signature(method).parameters) == params

    dictionary_methods = {
        "replace_items": ["self", "dictionary_type", "items"],
        "list_items": ["self", "dictionary_type"],
    }
    for method_name, params in dictionary_methods.items():
        method = getattr(DictionaryRepositoryProtocol, method_name)
        assert iscoroutinefunction(method)
        assert list(signature(method).parameters) == params
