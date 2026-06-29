from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.database import Base, create_engine, create_sessionmaker
from src.dictionaries.dto import DictionaryType
from src.dictionaries.models import DictionaryItemModel
from src.dictionaries.repositories import DictionaryRepository
from src.dictionaries.snapshots import DictionaryItemSnapshot


def _create_repository(
    tmp_path: Path,
) -> tuple[DictionaryRepository, Engine, Session]:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    sessionmaker = create_sessionmaker(engine)
    session = sessionmaker()
    return DictionaryRepository(session), engine, session


@pytest.mark.asyncio
async def test_replace_items_replaces_existing_rows_and_lists_sorted(tmp_path: Path):
    repository, engine, session = _create_repository(tmp_path)
    try:
        await repository.replace_items(
            DictionaryType.DOMAINS,
            [
                DictionaryItemSnapshot(keitaro_id=20, name="Bravo"),
                DictionaryItemSnapshot(keitaro_id=10, name="Alpha"),
            ],
        )
        await repository.replace_items(
            DictionaryType.DOMAINS,
            [
                DictionaryItemSnapshot(keitaro_id=30, name="Charlie"),
                DictionaryItemSnapshot(keitaro_id=25, name="Delta"),
            ],
        )
        await repository.replace_items(
            DictionaryType.GROUPS,
            [DictionaryItemSnapshot(keitaro_id=5, name="Group")],
        )

        items = await repository.list_items()
        assert [
            (item.dictionary_type, item.keitaro_id, item.name)
            for item in items
        ] == [
            (DictionaryType.DOMAINS, 25, "Delta"),
            (DictionaryType.DOMAINS, 30, "Charlie"),
            (DictionaryType.GROUPS, 5, "Group"),
        ]

        domains_only = await repository.list_items(DictionaryType.DOMAINS)
        assert [
            (item.dictionary_type, item.keitaro_id, item.name)
            for item in domains_only
        ] == [
            (DictionaryType.DOMAINS, 25, "Delta"),
            (DictionaryType.DOMAINS, 30, "Charlie"),
        ]

        rows = session.execute(select(DictionaryItemModel)).scalars().all()
        assert len(rows) == 3
    finally:
        session.close()
        engine.dispose()
