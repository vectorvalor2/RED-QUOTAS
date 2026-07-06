import logging
from typing import Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path
import asyncio

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class JobManager:
    """Manages processing jobs and queue with Redis-backed persistence and fallback to on-disk storage."""

    def __init__(self, settings):
        self.settings = settings
        self.jobs: Dict[str, dict] = {}
        self.job_queue: List[str] = []
        self._jobs_file = Path(self.settings.STORAGE_PATH) / "jobs.json"
        Path(self.settings.STORAGE_PATH).mkdir(parents=True, exist_ok=True)

        # Redis keys
        self.queue_key = "red:queue"
        self.processing_key = "red:processing"
        self.jobs_prefix = "red:job:"

        # Redis client (async)
        self._redis: Optional[aioredis.Redis] = None

    async def initialize(self):
        """Initialize job manager and connect to Redis if available, otherwise load persisted jobs"""
        logger.info("Initializing job manager...")
        # Try to connect to Redis
        try:
            if getattr(self.settings, "REDIS_URL", None):
                self._redis = aioredis.from_url(self.settings.REDIS_URL, encoding="utf-8", decode_responses=True)
                await self._redis.ping()
                logger.info(f"Connected to Redis at {self.settings.REDIS_URL}")
                # No need to load on-disk jobs when Redis is authoritative
                return
        except Exception as e:
            logger.warning(f"Redis unavailable ({getattr(self.settings, 'REDIS_URL', None)}): {e}; falling back to disk persistence")
            self._redis = None

        # Fallback: load persisted jobs if present
        try:
            if self._jobs_file.exists():
                with open(self._jobs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.jobs = data.get("jobs", {})
                    # Rebuild queue from jobs with queued status
                    self.job_queue = [cid for cid, j in self.jobs.items() if j.get("status") == "queued"]
                    logger.info(f"Loaded {len(self.jobs)} jobs from disk, queued={len(self.job_queue)}")
        except Exception as e:
            logger.warning(f"Failed to load persisted jobs from disk: {e}")

    async def shutdown(self):
        """Cleanup resources and persist jobs if Redis isn't used"""
        logger.info("Shutting down job manager")
        try:
            if self._redis:
                await self._redis.close()
            else:
                self._persist()
        except Exception as e:
            logger.warning(f"Error during shutdown: {e}")

    def _persist(self):
        try:
            with open(self._jobs_file, "w", encoding="utf-8") as f:
                json.dump({"jobs": self.jobs}, f, default=str, indent=2)
        except Exception:
            logger.exception("Failed to persist jobs to disk")

    async def add_job(self, job: dict):
        """Add job to queue and persist it (Redis or disk)"""
        clip_id = job.get("clip_id")
        if not clip_id:
            raise ValueError("job must include clip_id")

        # Ensure minimal fields
        job.setdefault("status", "queued")
        job.setdefault("progress", 0)
        job.setdefault("created_at", datetime.utcnow().isoformat())

        if self._redis:
            # Store job payload and push to queue (left push -> FIFO with RPOP/LPOP semantics)
            jobs_key = self.jobs_prefix + clip_id
            await self._redis.set(jobs_key, json.dumps(job))
            await self._redis.rpush(self.queue_key, clip_id)
            logger.info(f"Added job {clip_id} to Redis queue")
        else:
            self.jobs[clip_id] = job
            if clip_id not in self.job_queue and job.get("status") == "queued":
                self.job_queue.append(clip_id)
            logger.info(f"Added job {clip_id} to disk queue")
            self._persist()

    async def get_job(self, clip_id: str) -> Optional[dict]:
        """Get job details (from Redis or disk cache)"""
        if self._redis:
            jobs_key = self.jobs_prefix + clip_id
            raw = await self._redis.get(jobs_key)
            if not raw:
                return None
            try:
                return json.loads(raw)
            except Exception:
                return None
        else:
            return self.jobs.get(clip_id)

    async def update_job(self, clip_id: str, updates: dict):
        """Update job status and persist (Redis or disk)"""
        if self._redis:
            jobs_key = self.jobs_prefix + clip_id
            raw = await self._redis.get(jobs_key)
            if not raw:
                logger.warning(f"Cannot update job {clip_id}: job not found in Redis")
                return
            try:
                job = json.loads(raw)
            except Exception:
                job = {}
            job.update(updates)
            await self._redis.set(jobs_key, json.dumps(job))

            # If status changed away from queued, ensure it's not in the queue list
            status = job.get("status")
            if status != "queued":
                try:
                    await self._redis.lrem(self.queue_key, 0, clip_id)
                except Exception:
                    pass

            logger.info(f"Updated job {clip_id} in Redis: {updates}")
        else:
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
        if self._redis:
            ids = await self._redis.lrange(self.processing_key, 0, -1)
            jobs = []
            for cid in ids:
                j = await self.get_job(cid)
                if j:
                    jobs.append(j)
            return jobs
        else:
            return [j for j in self.jobs.values() if j.get("status") == "processing"]

    async def get_queued_jobs(self) -> List[dict]:
        """Get all queued jobs (ordered)"""
        if self._redis:
            ids = await self._redis.lrange(self.queue_key, 0, -1)
            jobs = []
            for cid in ids:
                j = await self.get_job(cid)
                if j:
                    jobs.append(j)
            return jobs
        else:
            return [self.jobs[cid] for cid in list(self.job_queue) if cid in self.jobs]

    async def pop_next_job(self) -> Optional[dict]:
        """Atomically pop the next queued job and mark it processing

        Uses BRPOPLPUSH to move from queue -> processing list atomically when Redis is available.
        Falls back to disk-based pop if Redis unavailable.
        """
        if self._redis:
            try:
                # BRPOPLPUSH from queue -> processing with timeout
                clip_id = await self._redis.brpoplpush(self.queue_key, self.processing_key, timeout=1)
                if not clip_id:
                    return None
                job = await self.get_job(clip_id)
                if not job:
                    # No job metadata found; remove from processing list
                    try:
                        await self._redis.lrem(self.processing_key, 0, clip_id)
                    except Exception:
                        pass
                    return None

                job["status"] = "processing"
                job["progress"] = 0
                job["started_at"] = datetime.utcnow().isoformat()
                await self._redis.set(self.jobs_prefix + clip_id, json.dumps(job))
                logger.info(f"Popped job {clip_id} for processing (Redis)")
                return job
            except Exception as e:
                logger.exception(f"Error popping job from Redis: {e}")
                return None
        else:
            # Disk fallback
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
            logger.info(f"Popped job {clip_id} for processing (disk)")
            return job

    async def ack_completed(self, clip_id: str):
        """Acknowledge a job completed: remove from processing list and delete or keep metadata"""
        if self._redis:
            try:
                await self._redis.lrem(self.processing_key, 0, clip_id)
            except Exception:
                pass
        # Disk mode persists in update_job

    async def requeue_stale_processing(self, max_age_seconds: int = 300):
        """Move stale jobs from processing back to queue (best-effort)."""
        if not self._redis:
            return
        try:
            ids = await self._redis.lrange(self.processing_key, 0, -1)
            for cid in ids:
                job = await self.get_job(cid)
                if not job:
                    continue
                started = job.get("started_at")
                if not started:
                    continue
                try:
                    age = (datetime.utcnow() - datetime.fromisoformat(started)).total_seconds()
                except Exception:
                    age = 0
                if age > max_age_seconds:
                    # remove from processing and push back to queue
                    await self._redis.lrem(self.processing_key, 0, cid)
                    await self._redis.rpush(self.queue_key, cid)
                    logger.info(f"Requeued stale job {cid} (age {age}s)")
        except Exception:
            logger.exception("Error during requeue_stale_processing")
