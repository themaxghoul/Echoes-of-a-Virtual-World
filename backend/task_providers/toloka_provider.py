# Toloka Task Provider - Yandex Crowdsourcing Platform
import aiohttp
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid

from .base_provider import (
    BaseTaskProvider, TaskProviderConfig, 
    ProviderTask, TaskSubmission, TaskResult
)

logger = logging.getLogger(__name__)

class TolokaProvider(BaseTaskProvider):
    """Toloka (Yandex) crowdsourcing platform integration"""
    
    SANDBOX_URL = "https://sandbox.toloka.dev/api/v1"
    PRODUCTION_URL = "https://toloka.dev/api/v1"
    
    # Toloka task type mappings
    TASK_TYPE_MAP = {
        "image_tagging": "image_classification",
        "image_comparison": "side_by_side",
        "content_rating": "content_moderation",
        "sentiment_label": "text_classification",
        "text_categorization": "text_classification",
        "object_detection": "bounding_box"
    }
    
    def __init__(self, config: TaskProviderConfig):
        super().__init__(config)
        self.base_url = (
            self.SANDBOX_URL if config.environment == "sandbox" 
            else self.PRODUCTION_URL
        )
        self._session: Optional[aiohttp.ClientSession] = None
        self._projects: Dict[str, str] = {}  # task_type -> project_id
        self._pools: Dict[str, str] = {}  # task_type -> pool_id
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"OAuth {self.config.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            )
        return self._session
    
    async def initialize(self) -> bool:
        """Initialize Toloka connection and verify credentials"""
        try:
            is_valid = await self.validate_credentials()
            if is_valid:
                self._initialized = True
                logger.info(f"Toloka provider initialized successfully")
            return is_valid
        except Exception as e:
            logger.error(f"Failed to initialize Toloka: {e}")
            return False
    
    async def validate_credentials(self) -> bool:
        """Validate Toloka API credentials"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/requester") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"Toloka account verified: {data.get('id')}")
                    return True
                elif resp.status == 401:
                    logger.error("Toloka: Invalid API key")
                    return False
                else:
                    logger.error(f"Toloka validation failed: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"Toloka credential validation error: {e}")
            return False
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get Toloka account balance"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/requester") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "provider": "toloka",
                        "balance": data.get("balance", 0),
                        "currency": "USD",
                        "account_id": data.get("id")
                    }
                return {"provider": "toloka", "balance": 0, "error": "Failed to fetch"}
        except Exception as e:
            return {"provider": "toloka", "balance": 0, "error": str(e)}
    
    async def get_task_types(self) -> List[Dict[str, Any]]:
        """Get supported Toloka task types"""
        return [
            {
                "id": "image_classification",
                "name": "Image Classification",
                "description": "Classify images into categories",
                "avg_payout": 0.02,
                "avg_time_seconds": 10
            },
            {
                "id": "content_moderation",
                "name": "Content Moderation",
                "description": "Rate content safety/appropriateness",
                "avg_payout": 0.015,
                "avg_time_seconds": 8
            },
            {
                "id": "text_classification",
                "name": "Text Classification",
                "description": "Classify text sentiment or category",
                "avg_payout": 0.01,
                "avg_time_seconds": 6
            },
            {
                "id": "bounding_box",
                "name": "Object Detection",
                "description": "Draw bounding boxes around objects",
                "avg_payout": 0.05,
                "avg_time_seconds": 30
            },
            {
                "id": "side_by_side",
                "name": "Image Comparison",
                "description": "Compare two items and select better one",
                "avg_payout": 0.015,
                "avg_time_seconds": 8
            }
        ]
    
    async def fetch_available_tasks(
        self, 
        task_type: Optional[str] = None,
        limit: int = 10
    ) -> List[ProviderTask]:
        """Fetch available tasks from Toloka pools"""
        tasks = []
        
        try:
            session = await self._get_session()
            
            # Get active pools
            async with session.get(
                f"{self.base_url}/pools",
                params={"status": "OPEN", "limit": 50}
            ) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to fetch Toloka pools: {resp.status}")
                    return tasks
                
                pools_data = await resp.json()
                pools = pools_data.get("items", [])
            
            # For each pool, get available tasks
            for pool in pools[:5]:  # Limit to 5 pools
                pool_id = pool.get("id")
                pool_type = pool.get("private_name", "general")
                
                async with session.get(
                    f"{self.base_url}/tasks",
                    params={"pool_id": pool_id, "limit": limit}
                ) as task_resp:
                    if task_resp.status == 200:
                        task_data = await task_resp.json()
                        
                        for item in task_data.get("items", [])[:limit]:
                            task = ProviderTask(
                                task_id=f"toloka_{item.get('id')}",
                                provider="toloka",
                                task_type=self._map_task_type(pool_type),
                                title=pool.get("public_name", "Toloka Task"),
                                description=pool.get("public_description", ""),
                                instructions=pool.get("public_instructions", "Complete this task"),
                                payout=float(pool.get("reward_per_assignment", 0.01)),
                                estimated_time_seconds=int(pool.get("assignment_max_duration_seconds", 300) / 10),
                                data=item.get("input_values", {}),
                                difficulty="medium",
                                expires_at=pool.get("will_expire")
                            )
                            tasks.append(task)
            
            logger.info(f"Fetched {len(tasks)} tasks from Toloka")
            return tasks[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching Toloka tasks: {e}")
            return tasks
    
    async def submit_task_response(
        self, 
        submission: TaskSubmission
    ) -> TaskResult:
        """Submit task response to Toloka"""
        try:
            # Extract Toloka task ID
            toloka_task_id = submission.task_id.replace("toloka_", "")
            
            session = await self._get_session()
            
            # Create assignment response
            payload = {
                "task_id": toloka_task_id,
                "solutions": [{"output_values": submission.response}]
            }
            
            async with session.post(
                f"{self.base_url}/assignments",
                json=payload
            ) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    return TaskResult(
                        task_id=submission.task_id,
                        submission_id=data.get("id", str(uuid.uuid4())),
                        status="pending",
                        payout=0.0,  # Will be updated on approval
                        feedback=None
                    )
                else:
                    error_text = await resp.text()
                    logger.error(f"Toloka submission failed: {error_text}")
                    return TaskResult(
                        task_id=submission.task_id,
                        submission_id=str(uuid.uuid4()),
                        status="rejected",
                        payout=0.0,
                        feedback=f"Submission failed: {error_text}"
                    )
                    
        except Exception as e:
            logger.error(f"Error submitting to Toloka: {e}")
            return TaskResult(
                task_id=submission.task_id,
                submission_id=str(uuid.uuid4()),
                status="error",
                payout=0.0,
                feedback=str(e)
            )
    
    def _map_task_type(self, toloka_type: str) -> str:
        """Map Toloka task type to standard type"""
        type_lower = toloka_type.lower()
        for standard, toloka in self.TASK_TYPE_MAP.items():
            if toloka in type_lower or standard in type_lower:
                return standard
        return "general"
    
    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
