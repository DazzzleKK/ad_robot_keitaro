from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.campaigns.repositories import CampaignRepository
from src.campaigns.usecases import (
    BatchUpdateStreamOffersUseCase,
    CreateCampaignUseCase,
    FetchCampaignStreamsUseCase,
    GetCampaignEditorUseCase,
    ListCampaignsUseCase,
    SearchKeitaroOffersUseCase,
)
from src.dictionaries.repositories import DictionaryRepository
from src.dictionaries.usecases import ListDictionariesUseCase, RefreshDictionariesUseCase
from src.keitaro.client import HttpKeitaroClient
from src.settings import Settings


@lru_cache(maxsize=1)
def get_settings_from_env() -> Settings:
    return Settings()


def get_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        return get_settings_from_env()
    return settings


async def get_keitaro_client(settings: Settings = Depends(get_settings)) -> AsyncIterator[HttpKeitaroClient]:
    client = HttpKeitaroClient(
        base_url=settings.keitaro_base_url,
        api_key=settings.keitaro_api_key,
    )
    try:
        yield client
    finally:
        await client.aclose()


async def get_async_session(request: Request) -> AsyncIterator[Session]:
    sessionmaker = getattr(request.app.state, "sessionmaker", None)
    if sessionmaker is None:
        raise RuntimeError("Sessionmaker is not configured")

    with sessionmaker() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def get_campaign_repository(session: Session = Depends(get_async_session)) -> CampaignRepository:
    return CampaignRepository(session)


def get_dictionary_repository(session: Session = Depends(get_async_session)) -> DictionaryRepository:
    return DictionaryRepository(session)


def get_create_campaign_usecase(
    client: HttpKeitaroClient = Depends(get_keitaro_client),
    repository: CampaignRepository = Depends(get_campaign_repository),
) -> CreateCampaignUseCase:
    return CreateCampaignUseCase(client=client, repository=repository)


def get_list_campaigns_usecase(
    repository: CampaignRepository = Depends(get_campaign_repository),
) -> ListCampaignsUseCase:
    return ListCampaignsUseCase(repository=repository)


def get_campaign_editor_usecase(
    repository: CampaignRepository = Depends(get_campaign_repository),
) -> GetCampaignEditorUseCase:
    return GetCampaignEditorUseCase(repository=repository)


def get_search_keitaro_offers_usecase(
    client: HttpKeitaroClient = Depends(get_keitaro_client),
) -> SearchKeitaroOffersUseCase:
    return SearchKeitaroOffersUseCase(client=client)


def get_fetch_campaign_streams_usecase(
    client: HttpKeitaroClient = Depends(get_keitaro_client),
    repository: CampaignRepository = Depends(get_campaign_repository),
) -> FetchCampaignStreamsUseCase:
    return FetchCampaignStreamsUseCase(client=client, repository=repository)


def get_batch_update_stream_offers_usecase(
    client: HttpKeitaroClient = Depends(get_keitaro_client),
    repository: CampaignRepository = Depends(get_campaign_repository),
) -> BatchUpdateStreamOffersUseCase:
    return BatchUpdateStreamOffersUseCase(client=client, repository=repository)


def get_refresh_dictionaries_usecase(
    client: HttpKeitaroClient = Depends(get_keitaro_client),
    repository: DictionaryRepository = Depends(get_dictionary_repository),
) -> RefreshDictionariesUseCase:
    return RefreshDictionariesUseCase(client=client, repository=repository)


def get_list_dictionaries_usecase(
    repository: DictionaryRepository = Depends(get_dictionary_repository),
) -> ListDictionariesUseCase:
    return ListDictionariesUseCase(repository=repository)
