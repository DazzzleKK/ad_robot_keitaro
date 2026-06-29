from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from src.main import create_app
from src.settings import Settings


@pytest.fixture
def app():
    return create_app(
        Settings(
            database_url="sqlite:///:memory:",
            keitaro_base_url="https://keitaro.example",
            keitaro_api_key="test-key",
        )
    )


@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clear_overrides(app):
    yield
    app.dependency_overrides.clear()
