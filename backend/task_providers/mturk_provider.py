# Amazon MTurk Task Provider
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid
import os

from .base_provider import (
    BaseTaskProvider, TaskProviderConfig, 
    ProviderTask, TaskSubmission, TaskResult
)

logger = logging.getLogger(__name__)

class MTurkProvider(BaseTaskProvider):
    """Amazon Mechanical Turk crowdsourcing platform integration"""
    
    SANDBOX_ENDPOINT = "https://mturk-requester-sandbox.us-east-1.amazonaws.com"
    PRODUCTION_ENDPOINT = "https://mturk-requester.us-east-1.amazonaws.com"
    
    def __init__(self, config: TaskProviderConfig):
        super().__init__(config)
        
        # Parse AWS credentials from api_key (format: ACCESS_KEY:SECRET_KEY)
        if ":" in config.api_key:
            self.access_key, self.secret_key = config.api_key.split(":", 1)
        else:
            self.access_key = config.api_key
            self.secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
        
        self.endpoint_url = (
            self.SANDBOX_ENDPOINT if config.environment == "sandbox"
            else self.PRODUCTION_ENDPOINT
        )
        
        self._client = None
    
    def _get_client(self):
        """Get or create boto3 MTurk client"""
        if self._client is None:
            self._client = boto3.client(
                'mturk',
                region_name='us-east-1',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                endpoint_url=self.endpoint_url
            )
        return self._client
    
    async def initialize(self) -> bool:
        """Initialize MTurk connection"""
        try:
            is_valid = await self.validate_credentials()
            if is_valid:
                self._initialized = True
                logger.info("MTurk provider initialized successfully")
            return is_valid
        except Exception as e:
            logger.error(f"Failed to initialize MTurk: {e}")
            return False
    
    async def validate_credentials(self) -> bool:
        """Validate AWS/MTurk credentials"""
        try:
            client = self._get_client()
            response = client.get_account_balance()
            balance = response.get('AvailableBalance', '0')
            logger.info(f"MTurk credentials valid. Balance: ${balance}")
            return True
        except NoCredentialsError:
            logger.error("MTurk: No AWS credentials found")
            return False
        except ClientError as e:
            logger.error(f"MTurk credential validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"MTurk validation error: {e}")
            return False
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get MTurk account balance"""
        try:
            client = self._get_client()
            response = client.get_account_balance()
            return {
                "provider": "mturk",
                "balance": float(response.get('AvailableBalance', 0)),
                "on_hold": float(response.get('OnHoldBalance', 0)),
                "currency": "USD"
            }
        except Exception as e:
            return {"provider": "mturk", "balance": 0, "error": str(e)}
    
    async def get_task_types(self) -> List[Dict[str, Any]]:
        """Get supported MTurk HIT types"""
        return [
            {
                "id": "image_labeling",
                "name": "Image Labeling",
                "description": "Label or classify images",
                "avg_payout": 0.05,
                "avg_time_seconds": 15
            },
            {
                "id": "text_annotation",
                "name": "Text Annotation",
                "description": "Annotate or classify text content",
                "avg_payout": 0.03,
                "avg_time_seconds": 20
            },
            {
                "id": "survey",
                "name": "Survey/Questions",
                "description": "Answer survey questions",
                "avg_payout": 0.10,
                "avg_time_seconds": 60
            },
            {
                "id": "transcription",
                "name": "Audio Transcription",
                "description": "Transcribe audio clips",
                "avg_payout": 0.15,
                "avg_time_seconds": 120
            },
            {
                "id": "content_moderation",
                "name": "Content Moderation",
                "description": "Review and moderate content",
                "avg_payout": 0.02,
                "avg_time_seconds": 10
            }
        ]
    
    async def fetch_available_tasks(
        self, 
        task_type: Optional[str] = None,
        limit: int = 10
    ) -> List[ProviderTask]:
        """Fetch available HITs from MTurk"""
        tasks = []
        
        try:
            client = self._get_client()
            
            # List reviewable HITs (as a requester, we see our HITs)
            response = client.list_hits(MaxResults=min(limit * 2, 100))
            
            for hit in response.get('HITs', [])[:limit]:
                hit_status = hit.get('HITStatus', '')
                
                # Only include assignable HITs
                if hit_status != 'Assignable':
                    continue
                
                task = ProviderTask(
                    task_id=f"mturk_{hit.get('HITId')}",
                    provider="mturk",
                    task_type=self._infer_task_type(hit),
                    title=hit.get('Title', 'MTurk Task'),
                    description=hit.get('Description', ''),
                    instructions="Complete this HIT according to instructions",
                    payout=float(hit.get('Reward', 0)),
                    estimated_time_seconds=hit.get('AssignmentDurationInSeconds', 300) // 10,
                    data={
                        "hit_type_id": hit.get('HITTypeId'),
                        "max_assignments": hit.get('MaxAssignments', 1),
                        "keywords": hit.get('Keywords', '')
                    },
                    difficulty="medium",
                    expires_at=hit.get('Expiration', '').isoformat() if hit.get('Expiration') else None
                )
                tasks.append(task)
            
            logger.info(f"Fetched {len(tasks)} tasks from MTurk")
            return tasks
            
        except Exception as e:
            logger.error(f"Error fetching MTurk HITs: {e}")
            return tasks
    
    async def submit_task_response(
        self, 
        submission: TaskSubmission
    ) -> TaskResult:
        """Submit HIT assignment response"""
        try:
            # In MTurk, workers submit directly to Amazon
            # As requesters, we approve/reject assignments
            # This simulates what a worker submission would result in
            
            return TaskResult(
                task_id=submission.task_id,
                submission_id=f"assign_{uuid.uuid4().hex[:12]}",
                status="pending",
                payout=0.0,
                feedback="Submission recorded, awaiting approval"
            )
            
        except Exception as e:
            logger.error(f"Error with MTurk submission: {e}")
            return TaskResult(
                task_id=submission.task_id,
                submission_id=str(uuid.uuid4()),
                status="error",
                payout=0.0,
                feedback=str(e)
            )
    
    def _infer_task_type(self, hit: Dict) -> str:
        """Infer task type from HIT metadata"""
        title = hit.get('Title', '').lower()
        keywords = hit.get('Keywords', '').lower()
        
        if any(w in title or w in keywords for w in ['image', 'photo', 'picture']):
            return 'image_labeling'
        elif any(w in title or w in keywords for w in ['transcri', 'audio', 'speech']):
            return 'transcription'
        elif any(w in title or w in keywords for w in ['survey', 'question', 'answer']):
            return 'survey'
        elif any(w in title or w in keywords for w in ['moder', 'review', 'content']):
            return 'content_moderation'
        else:
            return 'text_annotation'
    
    async def close(self):
        """Cleanup"""
        self._client = None
