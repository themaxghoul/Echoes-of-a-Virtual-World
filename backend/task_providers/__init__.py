# Task Providers Package
# Real micro-task provider integrations for AI Village

from .base_provider import BaseTaskProvider, TaskProviderConfig, ProviderTask, TaskSubmission
from .toloka_provider import TolokaProvider
from .mturk_provider import MTurkProvider
from .scale_provider import ScaleAIProvider
from .hive_provider import HiveProvider
from .appen_provider import AppenProvider
from .provider_manager import TaskProviderManager, get_provider_manager, initialize_all_providers

__all__ = [
    'BaseTaskProvider',
    'TaskProviderConfig',
    'ProviderTask',
    'TaskSubmission',
    'TolokaProvider',
    'MTurkProvider',
    'ScaleAIProvider',
    'HiveProvider',
    'AppenProvider',
    'TaskProviderManager',
    'get_provider_manager',
    'initialize_all_providers'
]
