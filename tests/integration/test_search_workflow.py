from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_search_endpoint_filters(db_session, sample_itts_bundle, alt_sample_itts_bundle, fake_minio) -> None:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.services.storage_service.get_minio_client", return_value=fake_minio):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                upload_1 = await client.post(
                    "/api/bundles",
                    files={"file": (sample_itts_bundle.filename, sample_itts_bundle.data, "application/octet-stream")},
                )
                assert upload_1.status_code == 201
                upload_2 = await client.post(
                    "/api/bundles",
                    files={"file": (alt_sample_itts_bundle.filename, alt_sample_itts_bundle.data, "application/octet-stream")},
                )
                assert upload_2.status_code == 201
                bundle_2 = upload_2.json()

                query_fragment = str(bundle_2["title"])[:8]
                search_q_resp = await client.get("/api/search", params={"q": query_fragment})
                assert search_q_resp.status_code == 200
                search_q_data = search_q_resp.json()
                assert len(search_q_data) >= 1
                assert any(item["id"] == bundle_2["id"] for item in search_q_data)

                search_ref_resp = await client.get(
                    "/api/search",
                    params={"ref": sample_itts_bundle.reference_title},
                )
                assert search_ref_resp.status_code == 200
                assert len(search_ref_resp.json()) >= 2

                search_emotion_resp = await client.get("/api/search", params={"emotion": "sample1"})
                assert search_emotion_resp.status_code == 200
                assert len(search_emotion_resp.json()) >= 2
    finally:
        app.dependency_overrides.clear()
