
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BundleCreate(BaseModel):
    title: str


class BundleResponse(BaseModel):
    id: int
    title: str
    filename: str
    s3_key: str
    generated_audio_sha256: Optional[str] = None
    reference_voice: Optional[str] = None
    emotion_voice: Optional[str] = None
    mode: Optional[str] = None
    total_duration_ms: Optional[int] = None
    is_concatenated: bool = False
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class BundleListResponse(BaseModel):
    total: int
    items: list[BundleResponse]
    page: int
    page_size: int


class SegmentResponse(BaseModel):
    id: int
    segment_index: int
    text_prompt: str
    normalized_text: Optional[str] = None
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ExportRequest(BaseModel):
    bundle_id: int
    segment_indices: list[int]
    silence_ms: int = Field(default=100, ge=0, le=5000)


class JobResponse(BaseModel):
    id: int
    type: str
    status: str
    progress: float
    result_bundle_id: Optional[int] = None
    result_export_id: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PlaylistResponse(BaseModel):
    id: int
    name: str
    is_auto_generated: bool
    auto_type: Optional[str] = None
    auto_value: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class PackRequest(BaseModel):
    title: str
    prompt_text: str
    reference_title: str
    emotion_title: str


class DuplicateResponse(BaseModel):
    status: str = "duplicate"
    message: str
    existing_bundle: BundleResponse
