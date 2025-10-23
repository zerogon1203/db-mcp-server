"""
Base database adapter for MCP server.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple, Optional
import logging
import os

logger = logging.getLogger(__name__)

class DatabaseAdapter(ABC):
    """데이터베이스 어댑터 베이스 클래스"""
    
    def __init__(self, config: dict):
        self.config = config
        self.connection = None
        self.read_only = os.getenv("READ_ONLY", "true").lower() == "true"
        self.strict_readonly = os.getenv("STRICT_READONLY", "true").lower() == "true"
        
        # 보안 검증기 초기화
        from security.query_validator import QueryValidator, SecurityLevel
        from security.identifier_manager import IdentifierManager
        
        self.validator = QueryValidator(SecurityLevel.STRICT if self.strict_readonly else SecurityLevel.NORMAL)
        self.identifier_manager = IdentifierManager(self.validator)
        
    @abstractmethod
    def connect(self):
        """데이터베이스 연결"""
        pass
        
    @abstractmethod
    def disconnect(self):
        """데이터베이스 연결 해제"""
        pass
        
    @abstractmethod
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """쿼리 실행 (SELECT)"""
        pass
        
    @abstractmethod
    def get_tables(self) -> List[str]:
        """테이블 목록 조회"""
        pass
        
    @abstractmethod
    def get_table_schema(self, table_name: str) -> List[Dict]:
        """테이블 스키마 조회"""
        pass
        
    @abstractmethod
    def get_foreign_keys(self, table_name: str) -> List[Dict]:
        """외래키 정보 조회"""
        pass
        
    @abstractmethod
    def get_table_stats(self, table_name: str) -> Dict:
        """테이블 통계 정보"""
        pass
        
    @abstractmethod
    def get_table_size(self, table_name: str) -> Dict:
        """테이블 크기 정보"""
        pass
        
    @abstractmethod
    def get_indexes(self, table_name: str = None) -> Dict:
        """인덱스 정보"""
        pass
        
    @abstractmethod
    def explain_query(self, query: str) -> Dict:
        """쿼리 실행 계획"""
        pass
        
    @abstractmethod
    def get_db_status(self) -> Dict:
        """데이터베이스 상태 정보"""
        pass
        
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.disconnect()
        
    def get_sample_data(self, table_name: str, limit: int = 5) -> Dict:
        """샘플 데이터 조회 (보안 강화)"""
        try:
            # 1. 테이블명 검증
            self.identifier_manager.validate_table_name(table_name)
            
            # 2. 컬럼 정보 먼저 조회
            schema = self.get_table_schema(table_name)
            columns = [col['name'] for col in schema]
            
            # 3. 안전한 쿼리 구성 (파라미터 바인딩 사용)
            safe_table_name = self.identifier_manager.get_safe_identifier(table_name, self.get_db_type())
            query = f"SELECT * FROM {safe_table_name} LIMIT %s"
            
            # 4. 쿼리 검증
            self.validator.validate_query(query, self.get_db_type())
            
            # 5. 파라미터 바인딩으로 실행
            rows = self.execute_query(query, (limit,))
            
            return {
                "table_name": table_name,
                "columns": columns,
                "data": rows
            }
        except Exception as e:
            logger.error(f"샘플 데이터 조회 중 오류 발생: {str(e)}")
            raise
            
    def get_db_type(self) -> str:
        """데이터베이스 타입 반환"""
        return self.config.get('db_type', 'mysql').lower()
            
    @abstractmethod
    def _quote_identifier(self, identifier: str) -> str:
        """식별자 인용부호 처리 (DB별로 다름)"""
        pass 