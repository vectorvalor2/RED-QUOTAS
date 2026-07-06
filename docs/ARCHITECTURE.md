# RED-QUOTAS Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Frontend (React)                      │
│              WebGL Preview + File Upload UI                  │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/WebSocket
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend Server                      │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │  REST API   │  │ Job Queue    │  │ WebSocket Hub   │   │
│  │  Endpoints  │  │ (RabbitMQ)   │  │ (Real-time)     │   │
│  └─────────────┘  └──────────────┘  └─────────────────┘   │
│         │                │                      │           │
│         └────────┬───────┴──────────────────────┘           │
│                  ↓                                           │
│         ┌────────────────┐                                   │
│         │ File Service   │                                   │
│         │ - Parse        │                                   │
│         │ - Validate     │                                   │
│         │ - Normalize    │                                   │
│         └────────┬───────┘                                   │
└─────────────────┼──────────────────────────────────────────┘
                  │ Python Bindings
                  ↓
┌─────────────────────────────────────────────────────────────┐
│           Vulkan + SIMD Processing Engine (C++)             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         RED Framework: Extract → Replicant → Dedup   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │   EXTRACT   │→ │ REPLICANT   │→ │ DEDUPLICATE │  │  │
│  │  │ (Parse fmt) │  │ (GPU Effects)  │ (Frame Cache)  │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │      GPU Compute Pipeline (Vulkan Shaders)           │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │  │
│  │  │ extract  │ │ replicant│ │ deduplicate  │effects│  │  │
│  │  │ .comp    │ │ .comp    │ │ .comp    │ │.comp   │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │      SIMD Processor (CPU SIMD Optimization)          │  │
│  │  AVX2/AVX-512, ARM NEON - Parallel frame ops         │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │      GPU Memory Management                            │  │
│  │  - Frame buffer pools                                │  │
│  │  - LRU cache for deduplication                       │  │
│  │  - Streaming pipeline                               │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ↓ Encoded Video
                  ┌───────────────────┐
                  │  Storage Backend  │
                  │  (S3 / Local)     │
                  └───────────────────┘
```

## Data Flow

### 1. Input Processing

**User uploads file** → **FastAPI receives** → **Queued in job manager**

- File validation (format, size, duration)
- Metadata extraction
- Job creation with processing params

### 2. Processing Pipeline

```
Input File
    ↓
[EXTRACT] → Normalize to float32 RGBA
    ↓
[REPLICANT] → Apply effects with GPU compute shaders
    ↓         (motion blur, neon glow, distortion, etc.)
    ↓
[DEDUPLICATE] → Frame delta compression & caching
    ↓          (Reduce memory bandwidth)
    ↓
[EFFECTS] → Post-processing (bloom, color grading)
    ↓
Output Video (H.264/HEVC)
```

### 3. GPU Compute Pipeline

**Vulkan Compute Shaders** dispatch in stages:

1. **extract.comp** - Input format conversion
   - Handles: H.264, HEVC, VP9, PNG, JPEG, WEBP
   - Output: Normalized float32 buffers

2. **replicant.comp** - Effect composition
   - Vectorized operations across frame
   - Multiple effects in single pass when possible
   - Uses push constants for per-frame params

3. **deduplicate.comp** - Frame comparison
   - Compute pixel-wise differences
   - Store delta frames for keyframes
   - GPU-resident LRU cache

4. **effects.comp** - Final pass
   - Color grading
   - Bloom/glow accumulation
   - Distortion warping

### 4. SIMD Optimization

CPU-side parallelization:

```c++
// Example: Frame extraction with SIMD
#pragma omp parallel for simd collapse(2)
for (uint32_t y = 0; y < height; ++y) {
    for (uint32_t x = 0; x < width; ++x) {
        // 8x AVX2 operations per iteration
        __m256 rgba = _mm256_loadu_ps(&input[idx]);
        rgba = _mm256_mul_ps(rgba, scale);  // Normalize
        _mm256_storeu_ps(&output[idx], rgba);
    }
}
```

## Technology Choices

### Backend
- **FastAPI**: Async HTTP framework, auto API docs
- **Pydantic**: Data validation
- **RabbitMQ/Redis**: Job queuing
- **uvicorn**: ASGI server

### GPU
- **Vulkan**: Cross-platform GPU compute
- **GLSL 4.5**: Compute shaders
- **shaderc**: GLSL → SPIR-V compilation

### SIMD
- **AVX2/AVX-512**: x86-64 optimization
- **ARM NEON**: Mobile optimization
- **OpenMP**: CPU parallelization

### Frontend
- **React 18**: Component framework
- **WebGL/WebGPU**: Client-side preview
- **Tailwind CSS**: Styling

## Performance Targets

| Resolution | FPS | Hardware | Time |
|------------|-----|----------|------|
| 1080p | 60 | RTX 4090 | 15s |
| 1080p | 30 | RTX 3060 | 25s |
| 4K | 30 | RTX 4090 | 45s |
| 4K | 24 | RTX 3060 | 90s |

## Scalability

### Single Instance
- Max GPU memory: 24GB (RTX 4090)
- Concurrent jobs: 3-4
- Queue depth: 50+

### Distributed
- Multiple worker pods with Kubernetes
- Redis-backed job queue
- Load balancer with sticky sessions
- S3-compatible storage

## Security

- Input file validation (size, format, mime type)
- Rate limiting per IP
- CORS for frontend
- API key for programmatic access
- Sandboxed GPU processing
