from __future__ import annotations

import pytest

from src.dictionaries.dto import DictionaryItemDto, DictionaryType
from src.dictionaries.snapshots import DictionaryItemSnapshot
from src.dictionaries.usecases import ListDictionariesUseCase, RefreshDictionariesUseCase
from src.keitaro.schemas import KeitaroDictionaryItem


class InMemoryDictionaryRepository:
    def __init__(self) -> None:
        self.items: dict[DictionaryType, list[DictionaryItemDto]] = {
            dictionary_type: []
            for dictionary_type in DictionaryType
        }
        self.replace_calls: list[tuple[DictionaryType, list[DictionaryItemSnapshot]]] = []

    async def replace_items(
        self,
        dictionary_type: DictionaryType,
        items: list[DictionaryItemSnapshot],
    ) -> list[DictionaryItemDto]:
        self.replace_calls.append((dictionary_type, list(items)))
        self.items[dictionary_type] = [
            DictionaryItemDto(
                id=index + 1,
                dictionary_type=dictionary_type,
                keitaro_id=item.keitaro_id,
                name=item.name,
            )
            for index, item in enumerate(items)
        ]
        return list(self.items[dictionary_type])

    async def list_items(
        self,
        dictionary_type: DictionaryType | None = None,
    ) -> list[DictionaryItemDto]:
        if dictionary_type is not None:
            return list(self.items[dictionary_type])
        return [
            item
            for dictionary_items in self.items.values()
            for item in dictionary_items
        ]


class StubKeitaroClient:
    def __init__(self) -> None:
        self.domains = [KeitaroDictionaryItem(id=10, name="Domain X")]
        self.groups = [KeitaroDictionaryItem(id=20, name="Group X")]
        self.sources = [KeitaroDictionaryItem(id=30, name="Source X")]
        self.offers = [KeitaroDictionaryItem(id=40, name="Offer X")]

    async def fetch_domains(self) -> list[KeitaroDictionaryItem]:
        return list(self.domains)

    async def fetch_groups(self) -> list[KeitaroDictionaryItem]:
        return list(self.groups)

    async def fetch_sources(self) -> list[KeitaroDictionaryItem]:
        return list(self.sources)

    async def fetch_offers(self) -> list[KeitaroDictionaryItem]:
        return list(self.offers)


@pytest.mark.asyncio
async def test_refresh_dictionaries_replaces_each_dictionary_and_returns_all_items():
    client = StubKeitaroClient()
    repository = InMemoryDictionaryRepository()
    usecase = RefreshDictionariesUseCase(client=client, repository=repository)

    items = await usecase.execute()

    assert [call[0] for call in repository.replace_calls] == [
        DictionaryType.DOMAINS,
        DictionaryType.GROUPS,
        DictionaryType.SOURCES,
        DictionaryType.OFFERS,
    ]
    assert [item.dictionary_type for item in items] == [
        DictionaryType.DOMAINS,
        DictionaryType.GROUPS,
        DictionaryType.SOURCES,
        DictionaryType.OFFERS,
    ]
    assert [item.keitaro_id for item in items] == [10, 20, 30, 40]


@pytest.mark.asyncio
async def test_list_dictionaries_delegates_to_repository_filter():
    repository = InMemoryDictionaryRepository()
    repository.items[DictionaryType.DOMAINS] = [
        DictionaryItemDto(
            id=1,
            dictionary_type=DictionaryType.DOMAINS,
            keitaro_id=10,
            name="Domain X",
        ),
    ]
    repository.items[DictionaryType.OFFERS] = [
        DictionaryItemDto(
            id=2,
            dictionary_type=DictionaryType.OFFERS,
            keitaro_id=40,
            name="Offer X",
        ),
    ]
    usecase = ListDictionariesUseCase(repository=repository)

    all_items = await usecase.execute()
    offer_items = await usecase.execute(DictionaryType.OFFERS)

    assert [item.dictionary_type for item in all_items] == [
        DictionaryType.DOMAINS,
        DictionaryType.OFFERS,
    ]
    assert offer_items == repository.items[DictionaryType.OFFERS]
