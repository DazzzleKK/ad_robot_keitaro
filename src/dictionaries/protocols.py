from typing import Protocol

from src.dictionaries.dto import DictionaryItemDto, DictionaryType
from src.dictionaries.snapshots import DictionaryItemSnapshot


class DictionaryRepositoryProtocol(Protocol):
    async def replace_items(
        self,
        dictionary_type: DictionaryType,
        items: list[DictionaryItemSnapshot],
    ) -> list[DictionaryItemDto]: ...

    async def list_items(
        self,
        dictionary_type: DictionaryType | None = None,
    ) -> list[DictionaryItemDto]: ...
