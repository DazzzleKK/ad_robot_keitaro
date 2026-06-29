from src.dictionaries.snapshots import DictionaryItemSnapshot
from src.keitaro.schemas import KeitaroDictionaryItem


def dictionary_snapshots_from_keitaro(
    items: list[KeitaroDictionaryItem],
) -> list[DictionaryItemSnapshot]:
    return [
        DictionaryItemSnapshot(keitaro_id=item.id, name=item.name)
        for item in items
    ]
