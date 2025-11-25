"""
src/infrastructure/__init__.py
Expõe as principais classes e funções da infraestrutura
"""

from .database import (
    Database,
    get_database,
    get_db,
    create_test_database
)
from .queue_manager import QueueManager
from .logger import setup_logging, get_logger

__all__ = [
    'Database',
    'get_database',
    'get_db',
    'create_test_database',
    'QueueManager',
    'setup_logging',
    'get_logger',
]
