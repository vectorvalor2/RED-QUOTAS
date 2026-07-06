import uuid
from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class EffectType(str, Enum):
    MOTION_BLUR = "motion_blur"
    NEON_GLOW = "neon_glow"
    TIME_WARP = "time_warp"
    CHROMATIC_ABERRATION = "chromatic_aberration"
    PARTICLE_DISTORTION = "particle_distortion"
    GLITCH = "glitch"

class GenerateRequest(BaseModel):
    effects: List[EffectType] = Field(default=[], description="List of effects to apply")
    duration: float = Field(default=5.0, ge=0.5, le=120.0, description="Duration in seconds")
    resolution: str = Field(default="1920x1080", description="Output resolution (WxH)")
    fps: int = Field(default=60, ge=24, le=120, description="Frames per second")
    effect_params: Optional[Dict[str, float]] = Field(default=None, description="Effect-specific parameters")

class ClipResponse(BaseModel):
    clip_id: str = Field(description="Unique clip identifier")
    status: JobStatus = Field(description="Current processing status")
    progress: int = Field(default=0, ge=0, le=100, description="Processing progress percentage")
    url: Optional[str] = Field(default=None, description="Download URL when completed")
    duration: Optional[float] = Field(default=None, description="Actual clip duration")
    width: Optional[int] = Field(default=None)
    height: Optional[int] = Field(default=None)
    fps: Optional[int] = Field(default=None)
    effects_applied: List[str] = Field(default=[])
    file_size_bytes: Optional[int] = Field(default=None)
    created_at: datetime
    completed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)

class GenerateResponse(BaseModel):
    clip_id: str
    status: JobStatus
    eta_seconds: float
    created_at: datetime

class EffectInfo(BaseModel):
    name: str
    display_name: str
    description: str
    category: str
    params: Dict[str, Any]

class SystemStats(BaseModel):
    gpu_name: str
    gpu_memory_total_mb: int
    gpu_memory_used_mb: int
    gpu_memory_available_mb: int
    active_jobs: int
    queued_jobs: int
    completed_jobs_24h: int
    average_render_time_seconds: float
    uptime_seconds: int

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
