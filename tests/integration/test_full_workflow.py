import asyncio
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_full_workflow(db_session, sample_itts_bundle, fake_minio) -> None:
    """Test complete workflow: upload, export, search, playlists, and download."""
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

                bundles_resp = await client.get("/api/bundles")
                assert bundles_resp.status_code == 200
                bundles_json = bundles_resp.json()
                assert bundles_json["total"] >= 1
                assert any(item["id"] == bundle_id for item in bundles_json["items"])

                search_resp = await client.get("/api/search", params={"emotion": "sample1"})
                assert search_resp.status_code == 200
                assert len(search_resp.json()) >= 1

                segments_resp = await client.get(f"/api/bundles/{bundle_id}/segments")
                assert segments_resp.status_code == 200
                assert len(segments_resp.json()) >= 1

                export_resp = await client.post(
                    "/api/export",
                    json={
                        "bundle_id": bundle_id,
                        "segment_indices": [0],
                        "silence_ms": 100,
                    },
                )
                assert export_resp.status_code == 201
                job_id = export_resp.json()["job_id"]

                result_export_id: int | None = None
                for _ in range(20):
                    status_resp = await client.get(f"/api/jobs/{job_id}")
                    assert status_resp.status_code == 200
                    status_json = status_resp.json()
                    if status_json["status"] == "completed":
                        result_export_id = status_json["result_export_id"]
                        break
                    await asyncio.sleep(0.1)
                else:
                    pytest.fail("Export job did not complete")

                assert result_export_id is not None
                download_resp = await client.get(f"/api/export/{result_export_id}")
                assert download_resp.status_code == 200
                assert download_resp.headers["content-type"] == "audio/wav"
                assert download_resp.content.startswith(b"RIFF")

                playlists_resp = await client.get("/api/playlists")
                assert playlists_resp.status_code == 200
                assert any(p["name"] == "Main" for p in playlists_resp.json())
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_duplicate_detection(db_session, sample_itts_bundle, fake_minio) -> None:
    """Uploading the same ITTS file twice should return 409 duplicate on second upload."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.services.storage_service.get_minio_client", return_value=fake_minio):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                first = await client.post(
                    "/api/bundles",
                    files={"file": (sample_itts_bundle.filename, sample_itts_bundle.data, "application/octet-stream")},
                )
                assert first.status_code == 201

                second = await client.post(
                    "/api/bundles",
                    files={"file": (sample_itts_bundle.filename, sample_itts_bundle.data, "application/octet-stream")},
                )
                assert second.status_code == 409
                assert second.json()["detail"]["status"] == "duplicate"
    finally:
        app.dependency_overrides.clear()
