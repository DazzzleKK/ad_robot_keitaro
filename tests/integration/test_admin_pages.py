from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_root_renders_admin_objects(client):
    response = await client.get("/")

    assert response.status_code == 200
    assert "Objects" in response.text
    assert "Campaigns" in response.text
    assert "/campaigns" in response.text
