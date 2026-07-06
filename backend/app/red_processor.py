import os
from pathlib import Path
import logging
from datetime import datetime
from typing import Optional
import shutil
import asyncio
import sys

logger = logging.getLogger(__name__)


class REDProcessor:
    """RED (Replicant, Extract, Deduplicate) processor

    This implementation provides a CPU-backed processing path using ffmpeg
    where available. If ffmpeg is not installed, it falls back to the
    simple copy behavior used previously.
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

    async def _run_ffmpeg(self, input_path: str, output_path: str) -> bool:
        """Run ffmpeg asynchronously to transcode input -> output.

        Returns True on success, False otherwise.
        """
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            logger.warning("ffmpeg not found on PATH, cannot run ffmpeg transcode")
            return False

        cmd = [
            ffmpeg,
            '-y',
            '-i', str(input_path),
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            str(output_path)
        ]

        logger.info(f"Running ffmpeg: {' '.join(cmd)}")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Read stderr and log progress snippets
            assert proc.stderr is not None
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                try:
                    decoded = line.decode('utf-8', errors='ignore').strip()
                except Exception:
                    decoded = str(line)
                # Log ffmpeg stderr at debug level to avoid noisy logs by default
                logger.debug(f"ffmpeg: {decoded}")

            returncode = await proc.wait()
            if returncode != 0:
                logger.error(f"ffmpeg failed with return code {returncode}")
                return False

            logger.info(f"ffmpeg completed successfully: {output_path}")
            return True
        except Exception as e:
            logger.exception(f"Error running ffmpeg: {e}")
            return False

    async def process_clip(self, clip_id: str) -> Optional[str]:
        """Process clip through RED pipeline using ffmpeg fallback

        Behavior:
        - Looks for the first uploaded file in storage_path/{clip_id}/
        - Attempts to transcode it to H.264 MP4 via ffmpeg
        - If ffmpeg is not available or the transcode fails, falls back to copying
          the input to output.mp4 (previous behavior)

        Returns path to generated file on success, or None on failure.
        """
        logger.info(f"Processing clip (CPU/ffmpeg fallback): {clip_id}")

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

        # Try ffmpeg transcode first
        success = await self._run_ffmpeg(str(input_path), str(output_path))
        if success:
            return str(output_path)

        # Fallback: copy the input to output
        try:
            # Simulate processing time
            await asyncio.sleep(1)
            shutil.copyfile(input_path, output_path)

            # If copy produced zero-length file, write a small placeholder
            if output_path.stat().st_size == 0:
                with open(output_path, 'wb') as f:
                    f.write(b"RED-QUOTAS-PLACEHOLDER\n")

            logger.info(f"Produced fallback output for {clip_id}: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.exception(f"Error producing fallback output for {clip_id}: {e}")
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
