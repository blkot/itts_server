from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_playlists_endpoints_workflow(db_session, sample_itts_bundle, fake_minio) -> None:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.services.storage_service.get_minio_client", return_value=fake_minio):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                upload = await client.post(
                    "/api/bundles",
                    files={"file": (sample_itts_bundle.filename, sample_itts_bundle.data, "application/octet-stream")},
                )
                assert upload.status_code == 201
                bundle_id = upload.json()["id"]

                playlists_resp = await client.get("/api/playlists")
                assert playlists_resp.status_code == 200
                playlists = playlists_resp.json()
                assert len(playlists) >= 1
                assert any(item["name"] == "Main" for item in playlists)

                main_playlist = next(item for item in playlists if item["name"] == "Main")
                main_bundles_resp = await client.get(f"/api/playlists/{main_playlist['id']}/bundles")
                assert main_bundles_resp.status_code == 200
                main_bundles = main_bundles_resp.json()
                assert len(main_bundles) == 1
                assert main_bundles[0]["id"] == bundle_id

                create_resp = await client.post("/api/playlists", params={"name": "Manual Mix"})
                assert create_resp.status_code == 201
                created = create_resp.json()
                assert created["name"] == "Manual Mix"
                assert created["is_auto_generated"] is False

                delete_resp = await client.delete(f"/api/playlists/{created['id']}")
                assert delete_resp.status_code == 204

                missing_delete_resp = await client.delete(f"/api/playlists/{created['id']}")
                assert missing_delete_resp.status_code == 404
    finally:
        app.dependency_overrides.clear()
