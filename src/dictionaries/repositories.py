from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.dictionaries.dto import DictionaryItemDto, DictionaryType
from src.dictionaries.models import DictionaryItemModel
from src.dictionaries.protocols import DictionaryRepositoryProtocol
from src.dictionaries.snapshots import DictionaryItemSnapshot


@dataclass(slots=True)
class DictionaryRepository(DictionaryRepositoryProtocol):
    _session: Session

    async def replace_items(
        self,
        dictionary_type: DictionaryType,
        items: list[DictionaryItemSnapshot],
    ) -> list[DictionaryItemDto]:
        self._session.execute(
            delete(DictionaryItemModel).where(DictionaryItemModel.type == dictionary_type)
        )
        self._session.add_all(
            [
                DictionaryItemModel(
                    type=dictionary_type,
                    keitaro_id=item.keitaro_id,
                    name=item.name,
                )
                for item in items
            ]
        )
        self._session.flush()
        return await self.list_items(dictionary_type)

    async def list_items(
        self,
        dictionary_type: DictionaryType | None = None,
    ) -> list[DictionaryItemDto]:
        stmt = select(DictionaryItemModel)
        if dictionary_type is not None:
            stmt = stmt.where(DictionaryItemModel.type == dictionary_type)
        stmt = stmt.order_by(
            DictionaryItemModel.type,
            DictionaryItemModel.keitaro_id,
            DictionaryItemModel.id,
        )
        result = self._session.execute(stmt)
        return [_dictionary_item_to_dto(model) for model in result.scalars().all()]


def _dictionary_item_to_dto(model: DictionaryItemModel) -> DictionaryItemDto:
    return DictionaryItemDto(
        id=model.id,
        dictionary_type=model.type,
        keitaro_id=model.keitaro_id,
        name=model.name,
    )
