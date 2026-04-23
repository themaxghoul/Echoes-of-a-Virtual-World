# Base Task Provider - Abstract interface for all task providers
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TaskProviderConfig(BaseModel):
    """Configuration for a task provider"""
    provider_name: str
    api_key: str
    environment: str = "sandbox"  # sandbox or production
    base_url: Optional[str] = None
    rate_limit_per_minute: int = 60
    timeout_seconds: int = 30
    enabled: bool = True

class ProviderTask(BaseModel):
    """Standardized task format across all providers"""
    task_id: str
    provider: str
    task_type: str
    title: str
    description: str
    instructions: str
    payout: float
    estimated_time_seconds: int
    data: Dict[str, Any]
    expires_at: Optional[str] = None
    difficulty: str = "easy"  # easy, medium, hard
    requires_qualification: bool = False

class TaskSubmission(BaseModel):
    """Standardized task submission format"""
    task_id: str
    worker_id: str
    response: Dict[str, Any]
    time_taken_seconds: float
    submitted_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class TaskResult(BaseModel):
    """Standardized task result format"""
    task_id: str
    submission_id: str
    status: str  # pending, approved, rejected
    payout: float
    feedback: Optional[str] = None
    approved_at: Optional[str] = None

class BaseTaskProvider(ABC):
    """Abstract base class for all task providers"""
    
    def __init__(self, config: TaskProviderConfig):
        self.config = config
        self.name = config.provider_name
        self._initialized = False
        logger.info(f"Initializing {self.name} provider")
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize connection to the provider API"""
        pass
    
    @abstractmethod
    async def fetch_available_tasks(
        self, 
        task_type: Optional[str] = None,
        limit: int = 10
    ) -> List[ProviderTask]:
        """Fetch available tasks from the provider"""
        pass
    
    @abstractmethod
    async def submit_task_response(
        self, 
        submission: TaskSubmission
    ) -> TaskResult:
        """Submit a completed task response"""
        pass
    
    @abstractmethod
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get current account balance/credits"""
        pass
    
    @abstractmethod
    async def get_task_types(self) -> List[Dict[str, Any]]:
        """Get supported task types from this provider"""
        pass
    
    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Validate API credentials"""
        pass
    
    def is_enabled(self) -> bool:
        """Check if provider is enabled"""
        return self.config.enabled and self._initialized
    
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health status"""
        try:
            is_valid = await self.validate_credentials()
            return {
                "provider": self.name,
                "status": "healthy" if is_valid else "unhealthy",
                "enabled": self.config.enabled,
                "environment": self.config.environment
            }
        except Exception as e:
            logger.error(f"Health check failed for {self.name}: {e}")
            return {
                "provider": self.name,
                "status": "error",
                "error": str(e)
            }
