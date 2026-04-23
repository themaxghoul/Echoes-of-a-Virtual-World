# Appen Task Provider - Data Annotation Platform
import aiohttp
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
import json

from .base_provider import (
    BaseTaskProvider, TaskProviderConfig, 
    ProviderTask, TaskSubmission, TaskResult
)

logger = logging.getLogger(__name__)

class AppenProvider(BaseTaskProvider):
    """Appen (formerly Figure Eight) data annotation platform integration"""
    
    BASE_URL = "https://api.appen.com/v1"
    
    def __init__(self, config: TaskProviderConfig):
        super().__init__(config)
        self.base_url = self.BASE_URL
        self._session: Optional[aiohttp.ClientSession] = None
        self._jobs: Dict[str, str] = {}  # job_id -> job_alias
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            )
        return self._session
    
    async def initialize(self) -> bool:
        """Initialize Appen connection"""
        try:
            is_valid = await self.validate_credentials()
            if is_valid:
                self._initialized = True
                logger.info("Appen provider initialized successfully")
            return is_valid
        except Exception as e:
            logger.error(f"Failed to initialize Appen: {e}")
            return False
    
    async def validate_credentials(self) -> bool:
        """Validate Appen API key"""
        try:
            session = await self._get_session()
            # List jobs to validate credentials
            async with session.get(
                f"{self.base_url}/jobs.json",
                params={"key": self.config.api_key}
            ) as resp:
                if resp.status == 200:
                    logger.info("Appen credentials validated")
                    return True
                elif resp.status == 401:
                    logger.error("Appen: Invalid API key")
                    return False
                else:
                    logger.warning(f"Appen validation response: {resp.status}")
                    return resp.status != 403
        except Exception as e:
            logger.error(f"Appen credential validation error: {e}")
            return False
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get Appen account info"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/jobs.json",
                params={"key": self.config.api_key}
            ) as resp:
                if resp.status == 200:
                    jobs = await resp.json()
                    return {
                        "provider": "appen",
                        "active_jobs": len(jobs) if isinstance(jobs, list) else 0,
                        "status": "active",
                        "note": "Contact Appen for billing details"
                    }
                return {"provider": "appen", "error": "Failed to fetch"}
        except Exception as e:
            return {"provider": "appen", "error": str(e)}
    
    async def get_task_types(self) -> List[Dict[str, Any]]:
        """Get supported Appen task types"""
        return [
            {
                "id": "image_annotation",
                "name": "Image Annotation",
                "description": "Label objects in images with bounding boxes",
                "avg_payout": 0.08,
                "avg_time_seconds": 40
            },
            {
                "id": "text_annotation",
                "name": "Text Annotation",
                "description": "Label entities and classify text",
                "avg_payout": 0.04,
                "avg_time_seconds": 25
            },
            {
                "id": "audio_transcription",
                "name": "Audio Transcription",
                "description": "Transcribe audio recordings",
                "avg_payout": 0.25,
                "avg_time_seconds": 180
            },
            {
                "id": "video_annotation",
                "name": "Video Annotation",
                "description": "Annotate objects across video frames",
                "avg_payout": 0.50,
                "avg_time_seconds": 300
            },
            {
                "id": "data_collection",
                "name": "Data Collection",
                "description": "Collect specific types of data",
                "avg_payout": 0.15,
                "avg_time_seconds": 60
            },
            {
                "id": "sentiment_analysis",
                "name": "Sentiment Analysis",
                "description": "Classify text sentiment",
                "avg_payout": 0.02,
                "avg_time_seconds": 10
            },
            {
                "id": "intent_classification",
                "name": "Intent Classification",
                "description": "Classify user intent from text",
                "avg_payout": 0.03,
                "avg_time_seconds": 15
            }
        ]
    
    async def fetch_available_tasks(
        self, 
        task_type: Optional[str] = None,
        limit: int = 10
    ) -> List[ProviderTask]:
        """Fetch available jobs/tasks from Appen"""
        tasks = []
        
        try:
            session = await self._get_session()
            
            # Get active jobs
            async with session.get(
                f"{self.base_url}/jobs.json",
                params={"key": self.config.api_key}
            ) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to fetch Appen jobs: {resp.status}")
                    return tasks
                
                jobs = await resp.json()
                if not isinstance(jobs, list):
                    jobs = []
            
            # Process each job
            for job in jobs[:limit]:
                job_id = job.get("id")
                
                # Get job details
                async with session.get(
                    f"{self.base_url}/jobs/{job_id}.json",
                    params={"key": self.config.api_key}
                ) as job_resp:
                    if job_resp.status == 200:
                        job_data = await job_resp.json()
                        
                        task = ProviderTask(
                            task_id=f"appen_{job_id}",
                            provider="appen",
                            task_type=self._infer_task_type(job_data),
                            title=job_data.get("title", "Appen Job"),
                            description=job_data.get("instructions", ""),
                            instructions=job_data.get("instructions", "Complete the task"),
                            payout=float(job_data.get("payment_cents", 5)) / 100,
                            estimated_time_seconds=job_data.get("time_per_assignment", 60),
                            data={
                                "job_id": job_id,
                                "units_count": job_data.get("units_count", 0),
                                "state": job_data.get("state", "unknown")
                            },
                            difficulty="medium"
                        )
                        tasks.append(task)
            
            logger.info(f"Fetched {len(tasks)} tasks from Appen")
            return tasks
            
        except Exception as e:
            logger.error(f"Error fetching Appen tasks: {e}")
            return tasks
    
    async def submit_task_response(
        self, 
        submission: TaskSubmission
    ) -> TaskResult:
        """Submit task response to Appen"""
        try:
            job_id = submission.task_id.replace("appen_", "")
            
            session = await self._get_session()
            
            # Submit unit response
            payload = {
                "key": self.config.api_key,
                "unit": {
                    "data": submission.response,
                    "judgment": True
                }
            }
            
            async with session.post(
                f"{self.base_url}/jobs/{job_id}/units.json",
                json=payload
            ) as resp:
                if resp.status in [200, 201]:
                    result = await resp.json()
                    return TaskResult(
                        task_id=submission.task_id,
                        submission_id=str(result.get("id", uuid.uuid4())),
                        status="pending",
                        payout=0.0,
                        feedback="Submission recorded"
                    )
                else:
                    error = await resp.text()
                    return TaskResult(
                        task_id=submission.task_id,
                        submission_id=str(uuid.uuid4()),
                        status="error",
                        payout=0.0,
                        feedback=f"Submission failed: {error}"
                    )
                    
        except Exception as e:
            logger.error(f"Error submitting to Appen: {e}")
            return TaskResult(
                task_id=submission.task_id,
                submission_id=str(uuid.uuid4()),
                status="error",
                payout=0.0,
                feedback=str(e)
            )
    
    async def upload_data_csv(self, job_id: str, csv_path: str) -> Dict[str, Any]:
        """Upload CSV data to an Appen job"""
        try:
            session = await self._get_session()
            
            with open(csv_path, 'rb') as csv_file:
                async with session.put(
                    f"{self.base_url}/jobs/{job_id}/upload",
                    data=csv_file,
                    params={"key": self.config.api_key},
                    headers={"Content-Type": "text/csv"}
                ) as resp:
                    if resp.status == 200:
                        return {"success": True, "job_id": job_id}
                    else:
                        return {"success": False, "error": await resp.text()}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_job_results(self, job_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get completed results from an Appen job"""
        try:
            session = await self._get_session()
            
            async with session.get(
                f"{self.base_url}/jobs/{job_id}/results.json",
                params={"key": self.config.api_key, "limit": limit}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return []
        except Exception as e:
            logger.error(f"Error fetching Appen results: {e}")
            return []
    
    def _infer_task_type(self, job_data: Dict) -> str:
        """Infer task type from job metadata"""
        title = job_data.get("title", "").lower()
        instructions = job_data.get("instructions", "").lower()
        
        if any(w in title or w in instructions for w in ['image', 'photo', 'picture', 'visual']):
            return 'image_annotation'
        elif any(w in title or w in instructions for w in ['audio', 'transcri', 'speech']):
            return 'audio_transcription'
        elif any(w in title or w in instructions for w in ['video', 'frame']):
            return 'video_annotation'
        elif any(w in title or w in instructions for w in ['sentiment', 'emotion']):
            return 'sentiment_analysis'
        elif any(w in title or w in instructions for w in ['intent', 'classify']):
            return 'intent_classification'
        elif any(w in title or w in instructions for w in ['collect', 'gather']):
            return 'data_collection'
        else:
            return 'text_annotation'
    
    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
