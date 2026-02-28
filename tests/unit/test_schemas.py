from app.models.schemas import BundleCreate, BundleListResponse, BundleResponse


def test_bundle_response_schema() -> None:
    data = {
        "id": 1,
        "title": "Test",
        "filename": "test.itts",
        "s3_key": "bundles/test.itts",
        "reference_voice": "voice1",
        "emotion_voice": "happy",
        "mode": "combined",
        "is_concatenated": False,
        "created_at": "2026-02-28T00:00:00Z",
    }
    bundle = BundleResponse(**data)
    assert bundle.id == 1
    assert bundle.title == "Test"
