import asyncio
import io
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app


class _FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def close(self) -> None:
        return None

    def release_conn(self) -> None:
        return None


class _FakeMinio:
    def __init__(self) -> None:
        self._objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, bucket: str, key: str, data, length: int):
        payload = data.read(length)
        self._objects[(bucket, key)] = payload

    def get_object(self, bucket: str, key: str) -> _FakeResponse:
        return _FakeResponse(self._objects[(bucket, key)])

    def remove_object(self, bucket: str, key: str) -> None:
        self._objects.pop((bucket, key), None)

    def stat_object(self, bucket: str, key: str) -> dict:
        if (bucket, key) not in self._objects:
            raise KeyError(key)
        return {"size": len(self._objects[(bucket, key)])}


@pytest.mark.asyncio
async def test_export_workflow(db_session) -> None:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    fake_minio = _FakeMinio()

    try:
        with patch("app.services.storage_service.get_minio_client", return_value=fake_minio):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                with open("tests/fixtures/spk_1772197182_1772197202988.itts", "rb") as f:
                    upload = await client.post(
                        "/api/bundles",
                        files={"file": ("test.itts", f, "application/octet-stream")},
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
async def test_concat_workflow(db_session) -> None:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    fake_minio = _FakeMinio()

    try:
        with patch("app.services.storage_service.get_minio_client", return_value=fake_minio):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                with open("tests/fixtures/spk_1772197182_1772197202988.itts", "rb") as f1:
                    r1 = await client.post(
                        "/api/bundles",
                        files={"file": ("test1.itts", f1, "application/octet-stream")},
                    )
                assert r1.status_code == 201
                bundle_id_1 = r1.json()["id"]

                with open("tests/fixtures/spk_1772197204_1772197238887.itts", "rb") as f2:
                    r2 = await client.post(
                        "/api/bundles",
                        files={"file": ("test2.itts", f2, "application/octet-stream")},
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
