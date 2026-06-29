from dataclasses import dataclass


@dataclass(frozen=True)
class DictionaryItemSnapshot:
    keitaro_id: int
    name: str
