import os
from pathlib import Path
import logging
from datetime import datetime
from typing import Optional
import shutil
import asyncio

logger = logging.getLogger(__name__)

class REDProcessor:
    """RED (Replicant, Extract, Deduplicate) processor

    This implementation provides a minimal CPU-backed processing path
    suitable for end-to-end testing and MVP runs. The real Vulkan
    implementation is still TODO and should replace / extend this class.
    """

    def __init__(self, settings):
        self.settings = settings
        self.storage_path = Path(settings.STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.gpu_available = False
        self.start_time = datetime.utcnow()

    async def initialize(self):
        """Initialize processor"""
        logger.info("Initializing RED processor...")

        if self.settings.ENABLE_GPU:
            try:
                # TODO: Initialize Vulkan engine
                # from vulkan_core import VulkanEngine
                # self.vulkan_engine = VulkanEngine()
                # self.vulkan_engine.initialize()
                self.gpu_available = False  # keep False until Vulkan exists
                logger.info("GPU requested but Vulkan not implemented; falling back to CPU")
            except Exception as e:
                logger.warning(f"GPU not available: {e}")
                self.gpu_available = False

    async def shutdown(self):
        """Cleanup resources"""
        logger.info("Shutting down RED processor")
        if self.gpu_available:
            # TODO: Shutdown Vulkan engine
            pass

    async def save_file(self, clip_id: str, filename: str, contents: bytes):
        """Save uploaded file"""
        file_path = self.storage_path / clip_id / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'wb') as f:
            f.write(contents)

        logger.info(f"Saved file: {file_path}")
        return str(file_path)

    async def process_clip(self, clip_id: str) -> Optional[str]:
        """Process clip through RED pipeline (CPU fallback)

        This minimal implementation looks for any file uploaded under
        storage_path/{clip_id}/ and copies the first file to
        storage_path/{clip_id}/output.mp4 to simulate processing.
        It sleeps briefly to emulate processing time.

        Returns path to generated file on success, or None on failure.
        """
        logger.info(f"Processing clip (CPU fallback): {clip_id}")

        clip_dir = self.storage_path / clip_id
        if not clip_dir.exists():
            logger.error(f"Clip directory not found: {clip_dir}")
            return None

        # find first non-output file
        files = [p for p in clip_dir.iterdir() if p.is_file() and p.name != "output.mp4"]
        if not files:
            logger.error(f"No input files found for clip {clip_id}")
            return None

        input_path = files[0]
        output_path = clip_dir / "output.mp4"

        try:
            # Simulate processing time (short)
            await asyncio.sleep(2)

            # For MVP just copy input to output to produce a result file
            shutil.copyfile(input_path, output_path)

            # If copy produced zero-length file (e.g. a text upload), write a small placeholder
            if output_path.stat().st_size == 0:
                with open(output_path, 'wb') as f:
                    f.write(b"RED-QUOTAS-PLACEHOLDER\n")

            logger.info(f"Produced output for {clip_id}: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.exception(f"Error processing clip {clip_id}: {e}")
            return None

    async def get_stats(self) -> dict:
        """Get system statistics"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        stats = {
            "gpu_name": "RTX 4090" if self.gpu_available else "CPU Only",
            "gpu_memory_total_mb": 24576 if self.gpu_available else 0,
            "gpu_memory_used_mb": 0,
            "gpu_memory_available_mb": 24576 if self.gpu_available else 0,
            "completed_jobs_24h": 0,
            "average_render_time_seconds": 0,
            "uptime_seconds": int(uptime)
        }

        return stats
