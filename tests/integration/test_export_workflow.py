import asyncio
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_export_workflow(db_session, sample_itts_bundle, fake_minio) -> None:
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

                export = await client.post(
                    "/api/export",
                    json={
                        "bundle_id": bundle_id,
                        "segment_indices": [0],
                        "silence_ms": 100,
                    },
                )
                assert export.status_code == 201
                job_id = export.json()["job_id"]

                for _ in range(10):
                    status_resp = await client.get(f"/api/jobs/{job_id}")
                    assert status_resp.status_code == 200
                    if status_resp.json()["status"] == "completed":
                        break
                    await asyncio.sleep(0.1)
                else:
                    pytest.fail("Export job did not complete")
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_concat_workflow(db_session, sample_itts_bundle, alt_sample_itts_bundle, fake_minio) -> None:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.services.storage_service.get_minio_client", return_value=fake_minio):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r1 = await client.post(
                    "/api/bundles",
                    files={"file": (sample_itts_bundle.filename, sample_itts_bundle.data, "application/octet-stream")},
                )
                assert r1.status_code == 201
                bundle_id_1 = r1.json()["id"]

                r2 = await client.post(
                    "/api/bundles",
                    files={"file": (alt_sample_itts_bundle.filename, alt_sample_itts_bundle.data, "application/octet-stream")},
                )
                assert r2.status_code == 201
                bundle_id_2 = r2.json()["id"]

                response = await client.post(
                    "/api/concat",
                    json={
                        "title": "Test Concat",
                        "items": [
                            {"bundle_id": bundle_id_1, "segments": [0]},
                            {"bundle_id": bundle_id_2, "segments": [0]},
                        ],
                        "silence_ms": 100,
                    },
                )

                assert response.status_code == 201
                job_id = response.json()["job_id"]

                for _ in range(10):
                    status_resp = await client.get(f"/api/jobs/{job_id}")
                    assert status_resp.status_code == 200
                    if status_resp.json()["status"] == "completed":
                        break
                    await asyncio.sleep(0.1)
                else:
                    pytest.fail("Concat job did not complete")
    finally:
        app.dependency_overrides.clear()
