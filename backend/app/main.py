import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from datetime import datetime
import uuid

from app.config import settings
from app.models import (
    GenerateRequest, GenerateResponse, ClipResponse, 
    EffectInfo, SystemStats, HealthResponse, JobStatus, EffectType
)
from app.red_processor import REDProcessor
from app.job_manager import JobManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
processor: REDProcessor = None
job_manager: JobManager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global processor, job_manager
    
    # Startup
    logger.info("Starting RED-QUOTAS backend...")
    processor = REDProcessor(settings)
    job_manager = JobManager(settings)
    
    await processor.initialize()
    await job_manager.initialize()
    
    logger.info("Backend initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await processor.shutdown()
    await job_manager.shutdown()

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="Futuristic movie clip generation engine",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=settings.API_VERSION
    )

@app.post("/api/generate", response_model=GenerateResponse)
async def generate_clip(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """
    Generate a movie clip from input file.
    
    Supported formats:
    - Video: MP4, WebM, MOV, AVI
    - Images: PNG, JPG, WEBP
    - 3D: OBJ, GLTF
    - Point Clouds: PLY, PCD
    - Audio: WAV, MP3
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file size
        contents = await file.read()
        file_size_mb = len(contents) / (1024 * 1024)
        
        if file_size_mb > settings.MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max {settings.MAX_FILE_SIZE_MB}MB"
            )
        
        # Create job
        clip_id = str(uuid.uuid4())
        job = {
            "clip_id": clip_id,
            "filename": file.filename,
            "file_size": len(contents),
            "status": JobStatus.QUEUED,
            "created_at": datetime.utcnow(),
            "effects": [],
            "duration": 5.0,
            "fps": 60,
            "resolution": "1920x1080"
        }
        
        # Save file
        await processor.save_file(clip_id, file.filename, contents)
        
        # Queue job
        await job_manager.add_job(job)
        
        # Background processing
        if background_tasks:
            background_tasks.add_task(processor.process_clip, clip_id)
        
        logger.info(f"Created job {clip_id}")
        
        return GenerateResponse(
            clip_id=clip_id,
            status=JobStatus.QUEUED,
            eta_seconds=45.0,
            created_at=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"Error generating clip: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clips/{clip_id}", response_model=ClipResponse)
async def get_clip_status(clip_id: str):
    """
    Get the status and details of a generated clip.
    """
    try:
        job = await job_manager.get_job(clip_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        return ClipResponse(
            clip_id=clip_id,
            status=job["status"],
            progress=job.get("progress", 0),
            url=job.get("url"),
            duration=job.get("duration"),
            width=job.get("width"),
            height=job.get("height"),
            fps=job.get("fps"),
            effects_applied=job.get("effects", []),
            file_size_bytes=job.get("file_size"),
            created_at=job["created_at"],
            completed_at=job.get("completed_at"),
            error_message=job.get("error_message")
        )
    except Exception as e:
        logger.error(f"Error fetching clip {clip_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/effects", response_model=list[EffectInfo])
async def list_effects():
    """
    List all available effects with their parameters.
    """
    effects = [
        EffectInfo(
            name="motion_blur",
            display_name="Motion Blur",
            description="Applies directional motion blur effect",
            category="blur",
            params={
                "strength": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.5},
                "direction": {"type": "float", "min": 0.0, "max": 360.0, "default": 0.0}
            }
        ),
        EffectInfo(
            name="neon_glow",
            display_name="Neon Glow",
            description="Creates a neon glow effect with edge enhancement",
            category="glow",
            params={
                "intensity": {"type": "float", "min": 0.0, "max": 2.0, "default": 1.0},
                "color": {"type": "string", "default": "#00d4ff"}
            }
        ),
        EffectInfo(
            name="time_warp",
            display_name="Time Warp",
            description="Creates a temporal distortion effect",
            category="distortion",
            params={
                "strength": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.5}
            }
        ),
        EffectInfo(
            name="chromatic_aberration",
            display_name="Chromatic Aberration",
            description="Simulates chromatic aberration with color fringing",
            category="distortion",
            params={
                "amount": {"type": "float", "min": 0.0, "max": 10.0, "default": 2.0}
            }
        ),
        EffectInfo(
            name="particle_distortion",
            display_name="Particle Distortion",
            description="Applies particle-based distortion effects",
            category="distortion",
            params={
                "density": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.5},
                "speed": {"type": "float", "min": 0.0, "max": 2.0, "default": 1.0}
            }
        ),
        EffectInfo(
            name="glitch",
            display_name="Glitch",
            description="Creates a digital glitch effect",
            category="distortion",
            params={
                "intensity": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.5},
                "frequency": {"type": "float", "min": 0.0, "max": 10.0, "default": 2.0}
            }
        )
    ]
    return effects

@app.get("/api/stats", response_model=SystemStats)
async def get_stats():
    """
    Get system statistics and GPU information.
    """
    try:
        stats = await processor.get_stats()
        jobs = await job_manager.get_active_jobs()
        queued = await job_manager.get_queued_jobs()
        
        return SystemStats(
            gpu_name=stats.get("gpu_name", "Unknown"),
            gpu_memory_total_mb=stats.get("gpu_memory_total_mb", 0),
            gpu_memory_used_mb=stats.get("gpu_memory_used_mb", 0),
            gpu_memory_available_mb=stats.get("gpu_memory_available_mb", 0),
            active_jobs=len(jobs),
            queued_jobs=len(queued),
            completed_jobs_24h=stats.get("completed_jobs_24h", 0),
            average_render_time_seconds=stats.get("average_render_time_seconds", 0),
            uptime_seconds=stats.get("uptime_seconds", 0)
        )
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/clip/{clip_id}")
async def websocket_clip_progress(websocket: WebSocket, clip_id: str):
    """
    WebSocket endpoint for real-time progress updates.
    """
    await websocket.accept()
    
    try:
        while True:
            job = await job_manager.get_job(clip_id)
            
            if not job:
                await websocket.send_json({
                    "type": "error",
                    "message": "Clip not found"
                })
                break
            
            await websocket.send_json({
                "type": "progress",
                "progress": job.get("progress", 0),
                "status": job["status"],
                "current_frame": job.get("current_frame", 0),
                "total_frames": job.get("total_frames", 0),
                "elapsed_seconds": job.get("elapsed_seconds", 0),
                "eta_seconds": job.get("eta_seconds", 0)
            })
            
            # Check if completed
            if job["status"] in [JobStatus.COMPLETED, JobStatus.FAILED]:
                break
            
            # Wait before next update
            import asyncio
            await asyncio.sleep(1)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

@app.get("/")
async def root():
    """
    API root endpoint with documentation link.
    """
    return {
        "name": "RED-QUOTAS API",
        "version": settings.API_VERSION,
        "docs": "/docs",
        "redoc": "/redoc"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
