# Scale AI Task Provider
import aiohttp
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from .base_provider import (
    BaseTaskProvider, TaskProviderConfig, 
    ProviderTask, TaskSubmission, TaskResult
)

logger = logging.getLogger(__name__)

class ScaleAIProvider(BaseTaskProvider):
    """Scale AI data labeling platform integration"""
    
    BASE_URL = "https://api.scale.com/v1"
    SANDBOX_URL = "https://api.scale.com/v1"  # Scale uses same URL, test mode via key
    
    def __init__(self, config: TaskProviderConfig):
        super().__init__(config)
        self.base_url = self.BASE_URL
        self._session: Optional[aiohttp.ClientSession] = None
        self._projects: Dict[str, str] = {}
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                auth=aiohttp.BasicAuth(self.config.api_key, ''),
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            )
        return self._session
    
    async def initialize(self) -> bool:
        """Initialize Scale AI connection"""
        try:
            is_valid = await self.validate_credentials()
            if is_valid:
                self._initialized = True
                logger.info("Scale AI provider initialized successfully")
            return is_valid
        except Exception as e:
            logger.error(f"Failed to initialize Scale AI: {e}")
            return False
    
    async def validate_credentials(self) -> bool:
        """Validate Scale AI API key"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/projects") as resp:
                if resp.status == 200:
                    logger.info("Scale AI credentials validated")
                    return True
                elif resp.status == 401:
                    logger.error("Scale AI: Invalid API key")
                    return False
                else:
                    logger.error(f"Scale AI validation failed: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"Scale AI credential validation error: {e}")
            return False
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get Scale AI account info (balance not directly exposed)"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/projects") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "provider": "scale_ai",
                        "projects_count": len(data.get("docs", [])),
                        "status": "active",
                        "note": "Contact Scale AI for billing details"
                    }
                return {"provider": "scale_ai", "error": "Failed to fetch"}
        except Exception as e:
            return {"provider": "scale_ai", "error": str(e)}
    
    async def get_task_types(self) -> List[Dict[str, Any]]:
        """Get supported Scale AI task types"""
        return [
            {
                "id": "imageannotation",
                "name": "Image Annotation",
                "description": "Draw bounding boxes, polygons, or keypoints",
                "avg_payout": 0.10,
                "avg_time_seconds": 45
            },
            {
                "id": "textannotation",
                "name": "Text Annotation",
                "description": "NER, sentiment, or classification",
                "avg_payout": 0.05,
                "avg_time_seconds": 30
            },
            {
                "id": "comparison",
                "name": "Comparison",
                "description": "Compare items side by side",
                "avg_payout": 0.03,
                "avg_time_seconds": 15
            },
            {
                "id": "categorization",
                "name": "Categorization",
                "description": "Categorize images or text",
                "avg_payout": 0.02,
                "avg_time_seconds": 10
            },
            {
                "id": "transcription",
                "name": "Transcription",
                "description": "Transcribe audio or handwriting",
                "avg_payout": 0.20,
                "avg_time_seconds": 120
            },
            {
                "id": "datacollection",
                "name": "Data Collection",
                "description": "Collect specific data types",
                "avg_payout": 0.15,
                "avg_time_seconds": 60
            }
        ]
    
    async def fetch_available_tasks(
        self, 
        task_type: Optional[str] = None,
        limit: int = 10
    ) -> List[ProviderTask]:
        """Fetch available tasks from Scale AI"""
        tasks = []
        
        try:
            session = await self._get_session()
            
            # Get projects first
            async with session.get(f"{self.base_url}/projects") as resp:
                if resp.status != 200:
                    logger.error(f"Failed to fetch Scale projects: {resp.status}")
                    return tasks
                
                projects_data = await resp.json()
                projects = projects_data.get("docs", [])
            
            # For each project, get pending tasks
            for project in projects[:3]:
                project_name = project.get("name", "Scale Project")
                project_type = project.get("type", "general")
                
                # Get tasks for this project
                params = {"status": "pending", "limit": limit}
                async with session.get(
                    f"{self.base_url}/tasks",
                    params=params
                ) as task_resp:
                    if task_resp.status == 200:
                        task_data = await task_resp.json()
                        
                        for item in task_data.get("docs", [])[:limit]:
                            task = ProviderTask(
                                task_id=f"scale_{item.get('task_id')}",
                                provider="scale_ai",
                                task_type=project_type,
                                title=f"{project_name} - {project_type}",
                                description=item.get("instruction", "Complete this task"),
                                instructions=item.get("instruction", "Follow the guidelines"),
                                payout=self._estimate_payout(project_type),
                                estimated_time_seconds=self._estimate_time(project_type),
                                data=item.get("params", {}),
                                difficulty="medium"
                            )
                            tasks.append(task)
            
            logger.info(f"Fetched {len(tasks)} tasks from Scale AI")
            return tasks[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching Scale AI tasks: {e}")
            return tasks
    
    async def submit_task_response(
        self, 
        submission: TaskSubmission
    ) -> TaskResult:
        """Submit task response to Scale AI"""
        try:
            task_id = submission.task_id.replace("scale_", "")
            
            session = await self._get_session()
            
            payload = {
                "response": submission.response,
                "time_spent_seconds": submission.time_taken_seconds
            }
            
            # Scale AI typically handles this through their managed workforce
            # For integration, we record the submission
            async with session.post(
                f"{self.base_url}/tasks/{task_id}/response",
                json=payload
            ) as resp:
                if resp.status in [200, 201, 202]:
                    return TaskResult(
                        task_id=submission.task_id,
                        submission_id=str(uuid.uuid4()),
                        status="pending",
                        payout=0.0,
                        feedback="Submitted for review"
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
            logger.error(f"Error submitting to Scale AI: {e}")
            return TaskResult(
                task_id=submission.task_id,
                submission_id=str(uuid.uuid4()),
                status="error",
                payout=0.0,
                feedback=str(e)
            )
    
    def _estimate_payout(self, task_type: str) -> float:
        """Estimate payout based on task type"""
        payouts = {
            "imageannotation": 0.10,
            "textannotation": 0.05,
            "comparison": 0.03,
            "categorization": 0.02,
            "transcription": 0.20,
            "datacollection": 0.15
        }
        return payouts.get(task_type.lower(), 0.05)
    
    def _estimate_time(self, task_type: str) -> int:
        """Estimate time in seconds based on task type"""
        times = {
            "imageannotation": 45,
            "textannotation": 30,
            "comparison": 15,
            "categorization": 10,
            "transcription": 120,
            "datacollection": 60
        }
        return times.get(task_type.lower(), 30)
    
    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
