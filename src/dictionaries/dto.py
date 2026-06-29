from dataclasses import dataclass
from enum import StrEnum


class DictionaryType(StrEnum):
    DOMAINS = "domains"
    GROUPS = "groups"
    SOURCES = "sources"
    OFFERS = "offers"


@dataclass(frozen=True)
class DictionaryItemDto:
    id: int
    dictionary_type: DictionaryType
    keitaro_id: int
    name: str
