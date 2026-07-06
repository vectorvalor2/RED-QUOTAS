import logging
from typing import Dict, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class JobManager:
    """Manages processing jobs and queue"""
    
    def __init__(self, settings):
        self.settings = settings
        self.jobs: Dict[str, dict] = {}
        self.job_queue: List[str] = []
    
    async def initialize(self):
        """Initialize job manager"""
        logger.info("Initializing job manager...")
        # TODO: Connect to Redis/RabbitMQ
    
    async def shutdown(self):
        """Cleanup resources"""
        logger.info("Shutting down job manager")
    
    async def add_job(self, job: dict):
        """Add job to queue"""
        clip_id = job["clip_id"]
        self.jobs[clip_id] = job
        self.job_queue.append(clip_id)
        logger.info(f"Added job {clip_id} to queue")
    
    async def get_job(self, clip_id: str) -> Optional[dict]:
        """Get job details"""
        return self.jobs.get(clip_id)
    
    async def update_job(self, clip_id: str, updates: dict):
        """Update job status"""
        if clip_id in self.jobs:
            self.jobs[clip_id].update(updates)
            logger.info(f"Updated job {clip_id}: {updates}")
    
    async def get_active_jobs(self) -> List[dict]:
        """Get all active jobs"""
        return [j for j in self.jobs.values() if j["status"] == "processing"]
    
    async def get_queued_jobs(self) -> List[dict]:
        """Get all queued jobs"""
        return [j for j in self.jobs.values() if j["status"] == "queued"]
