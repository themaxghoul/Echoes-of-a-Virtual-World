# Task Provider Manager - Orchestrates all task providers
import asyncio
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import random

from .base_provider import (
    BaseTaskProvider, TaskProviderConfig, 
    ProviderTask, TaskSubmission, TaskResult
)
from .toloka_provider import TolokaProvider
from .mturk_provider import MTurkProvider
from .scale_provider import ScaleAIProvider
from .hive_provider import HiveProvider
from .appen_provider import AppenProvider

logger = logging.getLogger(__name__)

class TaskProviderManager:
    """
    Manages multiple task providers and aggregates tasks from all sources.
    Provides unified interface for fetching and submitting tasks.
    """
    
    PROVIDER_CLASSES = {
        "toloka": TolokaProvider,
        "mturk": MTurkProvider,
        "scale_ai": ScaleAIProvider,
        "hive": HiveProvider,
        "appen": AppenProvider
    }
    
    def __init__(self):
        self.providers: Dict[str, BaseTaskProvider] = {}
        self._initialized = False
    
    def _get_provider_config(self, provider_name: str) -> Optional[TaskProviderConfig]:
        """Get configuration for a provider from environment variables"""
        env_prefix = provider_name.upper()
        api_key = os.environ.get(f"{env_prefix}_API_KEY")
        
        if not api_key:
            logger.warning(f"No API key found for {provider_name} (env: {env_prefix}_API_KEY)")
            return None
        
        environment = os.environ.get(f"{env_prefix}_ENVIRONMENT", "sandbox")
        
        return TaskProviderConfig(
            provider_name=provider_name,
            api_key=api_key,
            environment=environment,
            enabled=True
        )
    
    async def initialize_providers(self, provider_names: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Initialize specified providers or all available providers.
        Returns dict of provider_name -> initialization_success
        """
        if provider_names is None:
            provider_names = list(self.PROVIDER_CLASSES.keys())
        
        results = {}
        
        for name in provider_names:
            if name not in self.PROVIDER_CLASSES:
                logger.warning(f"Unknown provider: {name}")
                results[name] = False
                continue
            
            config = self._get_provider_config(name)
            if not config:
                results[name] = False
                continue
            
            try:
                provider_class = self.PROVIDER_CLASSES[name]
                provider = provider_class(config)
                
                success = await provider.initialize()
                if success:
                    self.providers[name] = provider
                    results[name] = True
                    logger.info(f"Provider {name} initialized successfully")
                else:
                    results[name] = False
                    logger.warning(f"Provider {name} initialization failed")
                    
            except Exception as e:
                logger.error(f"Error initializing provider {name}: {e}")
                results[name] = False
        
        self._initialized = len(self.providers) > 0
        return results
    
    async def add_provider(
        self, 
        provider_name: str, 
        api_key: str, 
        environment: str = "sandbox"
    ) -> bool:
        """Add and initialize a single provider"""
        if provider_name not in self.PROVIDER_CLASSES:
            logger.error(f"Unknown provider: {provider_name}")
            return False
        
        config = TaskProviderConfig(
            provider_name=provider_name,
            api_key=api_key,
            environment=environment,
            enabled=True
        )
        
        try:
            provider_class = self.PROVIDER_CLASSES[provider_name]
            provider = provider_class(config)
            
            success = await provider.initialize()
            if success:
                self.providers[provider_name] = provider
                logger.info(f"Provider {provider_name} added successfully")
            return success
            
        except Exception as e:
            logger.error(f"Error adding provider {provider_name}: {e}")
            return False
    
    async def remove_provider(self, provider_name: str) -> bool:
        """Remove and cleanup a provider"""
        if provider_name in self.providers:
            provider = self.providers[provider_name]
            await provider.close()
            del self.providers[provider_name]
            logger.info(f"Provider {provider_name} removed")
            return True
        return False
    
    async def fetch_all_tasks(
        self, 
        task_type: Optional[str] = None,
        limit_per_provider: int = 10,
        shuffle: bool = True
    ) -> List[ProviderTask]:
        """
        Fetch tasks from all active providers.
        Returns aggregated list of tasks.
        """
        all_tasks = []
        
        # Fetch from all providers concurrently
        fetch_tasks = []
        for name, provider in self.providers.items():
            if provider.is_enabled():
                fetch_tasks.append(
                    self._fetch_from_provider(provider, task_type, limit_per_provider)
                )
        
        if fetch_tasks:
            results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error fetching tasks: {result}")
                elif isinstance(result, list):
                    all_tasks.extend(result)
        
        if shuffle:
            random.shuffle(all_tasks)
        
        logger.info(f"Fetched {len(all_tasks)} total tasks from {len(self.providers)} providers")
        return all_tasks
    
    async def _fetch_from_provider(
        self, 
        provider: BaseTaskProvider,
        task_type: Optional[str],
        limit: int
    ) -> List[ProviderTask]:
        """Fetch tasks from a single provider with error handling"""
        try:
            return await provider.fetch_available_tasks(task_type, limit)
        except Exception as e:
            logger.error(f"Error fetching from {provider.name}: {e}")
            return []
    
    async def fetch_tasks_by_provider(
        self, 
        provider_name: str,
        task_type: Optional[str] = None,
        limit: int = 10
    ) -> List[ProviderTask]:
        """Fetch tasks from a specific provider"""
        if provider_name not in self.providers:
            logger.warning(f"Provider {provider_name} not available")
            return []
        
        provider = self.providers[provider_name]
        return await provider.fetch_available_tasks(task_type, limit)
    
    async def submit_task(self, submission: TaskSubmission) -> TaskResult:
        """
        Submit a task response to the appropriate provider.
        Determines provider from task_id prefix.
        """
        # Extract provider from task_id
        provider_name = self._get_provider_from_task_id(submission.task_id)
        
        if not provider_name or provider_name not in self.providers:
            return TaskResult(
                task_id=submission.task_id,
                submission_id="error",
                status="error",
                payout=0.0,
                feedback=f"Unknown provider for task: {submission.task_id}"
            )
        
        provider = self.providers[provider_name]
        return await provider.submit_task_response(submission)
    
    def _get_provider_from_task_id(self, task_id: str) -> Optional[str]:
        """Extract provider name from task_id prefix"""
        for provider_name in self.PROVIDER_CLASSES.keys():
            if task_id.startswith(f"{provider_name}_"):
                return provider_name
        return None
    
    async def get_all_task_types(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get supported task types from all providers"""
        task_types = {}
        
        for name, provider in self.providers.items():
            try:
                types = await provider.get_task_types()
                task_types[name] = types
            except Exception as e:
                logger.error(f"Error getting task types from {name}: {e}")
                task_types[name] = []
        
        return task_types
    
    async def get_balances(self) -> Dict[str, Dict[str, Any]]:
        """Get account balances from all providers"""
        balances = {}
        
        for name, provider in self.providers.items():
            try:
                balance = await provider.get_account_balance()
                balances[name] = balance
            except Exception as e:
                logger.error(f"Error getting balance from {name}: {e}")
                balances[name] = {"error": str(e)}
        
        return balances
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Run health checks on all providers"""
        health_status = {}
        
        for name, provider in self.providers.items():
            try:
                status = await provider.health_check()
                health_status[name] = status
            except Exception as e:
                health_status[name] = {"status": "error", "error": str(e)}
        
        # Add info about unconfigured providers
        for name in self.PROVIDER_CLASSES.keys():
            if name not in health_status:
                health_status[name] = {
                    "status": "not_configured",
                    "reason": "API key not provided"
                }
        
        return health_status
    
    def get_active_providers(self) -> List[str]:
        """Get list of active provider names"""
        return [name for name, provider in self.providers.items() if provider.is_enabled()]
    
    def get_provider_stats(self) -> Dict[str, Any]:
        """Get statistics about providers"""
        return {
            "total_providers": len(self.PROVIDER_CLASSES),
            "configured_providers": len(self.providers),
            "active_providers": len(self.get_active_providers()),
            "provider_names": list(self.providers.keys())
        }
    
    async def close_all(self):
        """Close all provider connections"""
        for provider in self.providers.values():
            try:
                await provider.close()
            except Exception as e:
                logger.error(f"Error closing provider {provider.name}: {e}")
        
        self.providers.clear()
        self._initialized = False
        logger.info("All providers closed")


# Singleton instance
_provider_manager: Optional[TaskProviderManager] = None

def get_provider_manager() -> TaskProviderManager:
    """Get or create the global provider manager instance"""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = TaskProviderManager()
    return _provider_manager

async def initialize_all_providers() -> Dict[str, bool]:
    """Initialize all configured providers"""
    manager = get_provider_manager()
    return await manager.initialize_providers()
