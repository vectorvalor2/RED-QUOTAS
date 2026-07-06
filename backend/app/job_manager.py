import logging
from typing import Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class JobManager:
    """Manages processing jobs and queue with simple on-disk persistence"""

    def __init__(self, settings):
        self.settings = settings
        self.jobs: Dict[str, dict] = {}
        self.job_queue: List[str] = []
        self._jobs_file = Path(self.settings.STORAGE_PATH) / "jobs.json"
        Path(self.settings.STORAGE_PATH).mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Initialize job manager and load persisted jobs"""
        logger.info("Initializing job manager...")
        # Load persisted jobs if present
        try:
            if self._jobs_file.exists():
                with open(self._jobs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.jobs = data.get("jobs", {})
                    # Rebuild queue from jobs with queued status
                    self.job_queue = [cid for cid, j in self.jobs.items() if j.get("status") == "queued"]
                    logger.info(f"Loaded {len(self.jobs)} jobs, queued={len(self.job_queue)}")
        except Exception as e:
            logger.warning(f"Failed to load persisted jobs: {e}")

    async def shutdown(self):
        """Cleanup resources and persist jobs"""
        logger.info("Shutting down job manager")
        try:
            self._persist()
        except Exception as e:
            logger.warning(f"Error persisting jobs on shutdown: {e}")

    def _persist(self):
        try:
            with open(self._jobs_file, "w", encoding="utf-8") as f:
                json.dump({"jobs": self.jobs}, f, default=str, indent=2)
        except Exception:
            logger.exception("Failed to persist jobs")

    async def add_job(self, job: dict):
        """Add job to queue and persist it"""
        clip_id = job.get("clip_id")
        if not clip_id:
            raise ValueError("job must include clip_id")

        # Ensure minimal fields
        job.setdefault("status", "queued")
        job.setdefault("progress", 0)
        job.setdefault("created_at", datetime.utcnow().isoformat())

        self.jobs[clip_id] = job
        if clip_id not in self.job_queue and job.get("status") == "queued":
            self.job_queue.append(clip_id)
        logger.info(f"Added job {clip_id} to queue")
        self._persist()

    async def get_job(self, clip_id: str) -> Optional[dict]:
        """Get job details"""
        return self.jobs.get(clip_id)

    async def update_job(self, clip_id: str, updates: dict):
        """Update job status and persist"""
        if clip_id in self.jobs:
            self.jobs[clip_id].update(updates)
            # keep queue consistent
            status = self.jobs[clip_id].get("status")
            if status != "queued" and clip_id in self.job_queue:
                try:
                    self.job_queue.remove(clip_id)
                except ValueError:
                    pass
            if status == "queued" and clip_id not in self.job_queue:
                self.job_queue.append(clip_id)

            logger.info(f"Updated job {clip_id}: {updates}")
            self._persist()

    async def get_active_jobs(self) -> List[dict]:
        """Get all active jobs"""
        return [j for j in self.jobs.values() if j.get("status") == "processing"]

    async def get_queued_jobs(self) -> List[dict]:
        """Get all queued jobs (ordered)"""
        return [self.jobs[cid] for cid in list(self.job_queue) if cid in self.jobs]

    async def pop_next_job(self) -> Optional[dict]:
        """Pop the next queued job and mark it processing"""
        if not self.job_queue:
            return None
        clip_id = self.job_queue.pop(0)
        job = self.jobs.get(clip_id)
        if not job:
            return None
        job["status"] = "processing"
        job["progress"] = 0
        job["started_at"] = datetime.utcnow().isoformat()
        self._persist()
        logger.info(f"Popped job {clip_id} for processing")
        return job
