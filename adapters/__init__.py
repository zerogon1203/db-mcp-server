"""
Database adapters for different database systems.
"""

from .base import DatabaseAdapter
from .mysql import MySQLAdapter

try:
    from .postgresql import PostgreSQLAdapter
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

__all__ = ['DatabaseAdapter', 'MySQLAdapter']

if POSTGRESQL_AVAILABLE:
    __all__.append('PostgreSQLAdapter')

def get_adapter(db_type: str, config: dict) -> DatabaseAdapter:
    """어댑터 팩토리 함수"""
    if db_type.lower() == 'mysql':
        return MySQLAdapter(config)
    elif db_type.lower() == 'postgresql' and POSTGRESQL_AVAILABLE:
        return PostgreSQLAdapter(config)
    else:
        raise ValueError(f"지원하지 않는 데이터베이스 타입: {db_type}") 