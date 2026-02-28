
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Bundle(Base):
    __tablename__ = "bundles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    s3_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    manifest_json: Mapped[str] = mapped_column(Text, nullable=False)
    generated_audio_sha256: Mapped[Optional[str]] = mapped_column(String, unique=True)
    reference_voice: Mapped[Optional[str]] = mapped_column(String)
    emotion_voice: Mapped[Optional[str]] = mapped_column(String)
    mode: Mapped[Optional[str]] = mapped_column(String)
    total_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    is_concatenated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_bundle_ids: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    segments: Mapped[list["Segment"]] = relationship(
        "Segment",
        back_populates="bundle",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_bundles_generated_audio_sha256", "generated_audio_sha256"),
    )


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bundle_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bundles.id", ondelete="CASCADE"),
        nullable=False,
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[Optional[str]] = mapped_column(Text)
    start_ms: Mapped[Optional[int]] = mapped_column(Integer)
    end_ms: Mapped[Optional[int]] = mapped_column(Integer)
    filename: Mapped[Optional[str]] = mapped_column(String)
    sha256: Mapped[Optional[str]] = mapped_column(String)

    bundle: Mapped["Bundle"] = relationship("Bundle", back_populates="segments")

    __table_args__ = (
        UniqueConstraint("bundle_id", "segment_index", name="uq_segments_bundle_index"),
    )


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_type: Mapped[Optional[str]] = mapped_column(String)
    auto_value: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_playlists_name", "name"),
    )


class PlaylistEntry(Base):
    __tablename__ = "playlist_entries"

    playlist_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("playlists.id", ondelete="CASCADE"),
        primary_key=True,
    )
    bundle_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bundles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_playlist_entries_playlist_bundle", "playlist_id", "bundle_id"),
    )


class Permission(Base):
    __tablename__ = "permissions"

    playlist_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("playlists.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    can_view: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bundle_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bundles.id", ondelete="CASCADE"),
        nullable=False,
    )
    s3_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    segment_indices: Mapped[str] = mapped_column(Text, nullable=False)
    join_silence_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    input_params: Mapped[str] = mapped_column(Text, nullable=False)
    result_bundle_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("bundles.id"))
    result_export_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("exports.id"))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
