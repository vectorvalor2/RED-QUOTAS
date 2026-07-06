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
        self._tasks = []

    async def start(self):
        await self.job_manager.initialize()
        await self.processor.initialize()
        logger.info("Worker started")

        # graceful shutdown signals
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
            except NotImplementedError:
                # signal handlers not available on Windows event loop
                pass

        concurrency = getattr(self.settings, "WORKERS", 4)
        logger.info(f"Starting worker with concurrency={concurrency}")

        # Start background requeue task
        requeue_task = asyncio.create_task(self._requeue_loop())
        self._tasks.append(requeue_task)

        # Start worker tasks
        for i in range(concurrency):
            t = asyncio.create_task(self._worker_loop(i))
            self._tasks.append(t)

        # Wait until tasks finish (they run until stop requested)
        await asyncio.gather(*self._tasks, return_exceptions=True)

        # cleanup
        await self.processor.shutdown()
        await self.job_manager.shutdown()
        logger.info("Worker shutdown complete")

    async def stop(self):
        logger.info("Worker received stop signal")
        self._shutdown = True
        # cancel worker tasks
        for t in self._tasks:
            t.cancel()

    async def _requeue_loop(self):
        # periodically requeue stale processing jobs
        while not self._shutdown:
            try:
                await self.job_manager.requeue_stale_processing(max_age_seconds=300)
            except Exception:
                logger.exception("Error in requeue loop")
            await asyncio.sleep(60)

    async def _worker_loop(self, idx: int):
        logger.info(f"Worker task {idx} started")
        while not self._shutdown:
            try:
                job = await self.job_manager.pop_next_job()
                if not job:
                    await asyncio.sleep(1.0)
                    continue

                clip_id = job.get("clip_id")
                logger.info(f"[{idx}] Picked job {clip_id}")

                # update progress
                await self.job_manager.update_job(clip_id, {"progress": 1, "status": "processing"})

                # process
                output = await self.processor.process_clip(clip_id)

                if output:
                    # determine url
                    presigned = output.get("presigned_url") if isinstance(output, dict) else None
                    local_path = output.get("local_path") if isinstance(output, dict) else output

                    # update job to completed
                    file_size = 0
                    try:
                        file_size = Path(local_path).stat().st_size if local_path else 0
                    except Exception:
                        pass

                    url = presigned if presigned else (f"file://{local_path}" if local_path else None)

                    await self.job_manager.update_job(clip_id, {
                        "progress": 100,
                        "status": "completed",
                        "url": url,
                        "file_size_bytes": file_size,
                        "completed_at": Path(local_path).stat().st_mtime if local_path else None
                    })

                    # ack / remove from processing list if Redis in use
                    try:
                        await self.job_manager.ack_completed(clip_id)
                    except Exception:
                        pass

                    logger.info(f"[{idx}] Job {clip_id} completed")
                else:
                    await self.job_manager.update_job(clip_id, {"progress": 0, "status": "failed", "error_message": "processing failed"})
                    logger.error(f"[{idx}] Job {clip_id} failed")

                # small delay to yield
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Unexpected error in worker loop")
                await asyncio.sleep(1.0)


async def main():
    w = Worker()
    await w.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
