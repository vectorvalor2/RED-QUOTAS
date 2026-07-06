# Backend API Documentation

## Overview

The RED-QUOTAS backend is a high-performance async processing engine built with FastAPI and Vulkan.

## Base URL

```
http://localhost:8000
```

## Endpoints

### POST /api/generate

Generate a movie clip from an input file.

**Request:**
```http
Content-Type: multipart/form-data

file: <binary file>
effects: JSON array of effect names
duration: float (seconds)
resolution: string ("1920x1080", "3840x2160", etc.)
fps: integer (24, 30, 60)
```

**Response:**
```json
{
  "clip_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "eta_seconds": 45,
  "created_at": "2026-07-06T05:45:00Z"
}
```

### GET /api/clips/{clip_id}

Get the status and details of a generated clip.

**Response:**
```json
{
  "clip_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "url": "s3://red-quotas/clips/550e8400.mp4",
  "duration": 5.2,
  "width": 1920,
  "height": 1080,
  "fps": 60,
  "effects_applied": ["motion_blur", "neon_glow"],
  "file_size_bytes": 125432891,
  "created_at": "2026-07-06T05:45:00Z",
  "completed_at": "2026-07-06T05:46:30Z"
}
```

**Status Values:**
- `queued` - Waiting to process
- `processing` - Currently rendering
- `completed` - Ready for download
- `failed` - Error occurred

### GET /api/effects

List all available effects with parameters.

**Response:**
```json
[
  {
    "name": "motion_blur",
    "display_name": "Motion Blur",
    "description": "Applies directional motion blur effect",
    "category": "blur",
    "params": {
      "strength": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": 0.5
      },
      "direction": {
        "type": "float",
        "min": 0.0,
        "max": 360.0,
        "default": 0.0
      }
    }
  }
]
```

### GET /api/stats

Get system statistics and GPU information.

**Response:**
```json
{
  "gpu_name": "NVIDIA RTX 4090",
  "gpu_memory_total_mb": 24576,
  "gpu_memory_used_mb": 4096,
  "gpu_memory_available_mb": 20480,
  "active_jobs": 3,
  "queued_jobs": 12,
  "completed_jobs_24h": 145,
  "average_render_time_seconds": 28.5,
  "uptime_seconds": 86400
}
```

## WebSocket

### WS /ws/clip/{clip_id}

Real-time progress updates for a clip being processed.

**Message Format:**
```json
{
  "type": "progress",
  "progress": 45,
  "current_frame": 135,
  "total_frames": 300,
  "elapsed_seconds": 12.5,
  "eta_seconds": 15.2
}
```

## Error Responses

**400 Bad Request:**
```json
{
  "error": "invalid_file_format",
  "message": "File format not supported. Supported: mp4, png, jpg, obj, gltf, ply, wav, mp3"
}
```

**429 Too Many Requests:**
```json
{
  "error": "rate_limited",
  "message": "Rate limit exceeded. Max 10 requests per minute.",
  "retry_after_seconds": 45
}
```

**503 Service Unavailable:**
```json
{
  "error": "gpu_overloaded",
  "message": "GPU queue full. Please try again later.",
  "retry_after_seconds": 120
}
```
