from __future__ import annotations

from dataclasses import dataclass

from src.dictionaries.dto import DictionaryItemDto, DictionaryType
from src.dictionaries.mappers import dictionary_snapshots_from_keitaro
from src.dictionaries.protocols import DictionaryRepositoryProtocol
from src.keitaro.protocols import KeitaroClientProtocol


@dataclass(slots=True)
class RefreshDictionariesUseCase:
    client: KeitaroClientProtocol
    repository: DictionaryRepositoryProtocol

    async def execute(self) -> list[DictionaryItemDto]:
        await self.repository.replace_items(
            DictionaryType.DOMAINS,
            dictionary_snapshots_from_keitaro(await self.client.fetch_domains()),
        )
        await self.repository.replace_items(
            DictionaryType.GROUPS,
            dictionary_snapshots_from_keitaro(await self.client.fetch_groups()),
        )
        await self.repository.replace_items(
            DictionaryType.SOURCES,
            dictionary_snapshots_from_keitaro(await self.client.fetch_sources()),
        )
        await self.repository.replace_items(
            DictionaryType.OFFERS,
            dictionary_snapshots_from_keitaro(await self.client.fetch_offers()),
        )
        return await self.repository.list_items()


@dataclass(slots=True)
class ListDictionariesUseCase:
    repository: DictionaryRepositoryProtocol

    async def execute(
        self,
        dictionary_type: DictionaryType | None = None,
    ) -> list[DictionaryItemDto]:
        return await self.repository.list_items(dictionary_type)
