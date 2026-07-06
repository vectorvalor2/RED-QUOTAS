"""Simple worker to process queued jobs.

Run this alongside the FastAPI server (separate process). It uses the
existing JobManager and REDProcessor classes to pick queued jobs,
process them with a CPU fallback, and update job status.

Usage:
  cd backend
  python -m backend.worker

"""
import asyncio
import logging
import signal
from pathlib import Path

from app.config import settings
from app.job_manager import JobManager
from app.red_processor import REDProcessor

logger = logging.getLogger("red.worker")
logging.basicConfig(level=logging.INFO)


class Worker:
    def __init__(self):
        self.settings = settings
        self.job_manager = JobManager(self.settings)
        self.processor = REDProcessor(self.settings)
        self._shutdown = False

    async def start(self):
        await self.job_manager.initialize()
        await self.processor.initialize()
        logger.info("Worker started")

        # graceful shutdown signals
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        try:
            while not self._shutdown:
                # try to pop a job
                job = await self.job_manager.pop_next_job()
                if not job:
                    await asyncio.sleep(1.0)
                    continue

                clip_id = job.get("clip_id")
                logger.info(f"Picked job {clip_id}")

                # update progress
                await self.job_manager.update_job(clip_id, {"progress": 1, "status": "processing"})

                # process
                output_path = await self.processor.process_clip(clip_id)

                if output_path:
                    # update job to completed
                    file_size = 0
                    try:
                        file_size = Path(output_path).stat().st_size
                    except Exception:
                        pass

                    await self.job_manager.update_job(clip_id, {
                        "progress": 100,
                        "status": "completed",
                        "url": f"file://{output_path}",
                        "file_size_bytes": file_size,
                        "completed_at": str(asyncio.get_event_loop().time())
                    })
                    logger.info(f"Job {clip_id} completed")
                else:
                    await self.job_manager.update_job(clip_id, {"progress": 0, "status": "failed", "error_message": "processing failed"})
                    logger.error(f"Job {clip_id} failed")

                # small delay to yield
                await asyncio.sleep(0.1)
        finally:
            await self.processor.shutdown()
            await self.job_manager.shutdown()
            logger.info("Worker shutdown complete")

    async def stop(self):
        logger.info("Worker received stop signal")
        self._shutdown = True


async def main():
    w = Worker()
    await w.start()


if __name__ == "__main__":
    asyncio.run(main())
