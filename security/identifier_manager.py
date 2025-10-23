"""
식별자 관리자 - 테이블명/컬럼명 화이트리스트 관리
"""

import logging
from typing import Set, Dict, List, Optional
from .query_validator import QueryValidator, SecurityError

logger = logging.getLogger(__name__)

class IdentifierManager:
    """식별자 화이트리스트 관리자"""
    
    def __init__(self, validator: QueryValidator = None):
        self.validator = validator or QueryValidator()
        self._table_whitelist: Set[str] = set()
        self._column_whitelist: Dict[str, Set[str]] = {}  # table_name -> set of columns
        self._schema_cache: Dict[str, Dict] = {}
        self._cache_valid = False
        
    def load_schema_cache(self, adapter) -> None:
        """스키마 캐시 로드"""
        try:
            logger.info("스키마 캐시 로딩 중...")
            
            # 테이블 목록 로드
            tables = adapter.get_tables()
            self._table_whitelist = set(tables)
            
            # 각 테이블의 컬럼 정보 로드
            self._column_whitelist.clear()
            for table in tables:
                try:
                    schema = adapter.get_table_schema(table)
                    columns = {col['name'] for col in schema}
                    self._column_whitelist[table] = columns
                    
                    # 스키마 캐시에도 저장
                    self._schema_cache[table] = {
                        'columns': schema,
                        'foreign_keys': adapter.get_foreign_keys(table)
                    }
                except Exception as e:
                    logger.warning(f"테이블 '{table}' 스키마 로드 실패: {e}")
                    self._column_whitelist[table] = set()
                    
            self._cache_valid = True
            logger.info(f"스키마 캐시 로드 완료: {len(tables)}개 테이블")
            
        except Exception as e:
            logger.error(f"스키마 캐시 로드 실패: {e}")
            raise
            
    def validate_table_name(self, table_name: str) -> bool:
        """테이블명 검증"""
        if not self._cache_valid:
            raise SecurityError(
                "스키마 캐시가 로드되지 않았습니다. 먼저 load_schema_cache()를 호출하세요.",
                error_code="SCHEMA_CACHE_NOT_LOADED"
            )
            
        # 화이트리스트 검증
        if table_name not in self._table_whitelist:
            raise SecurityError(
                f"허용되지 않은 테이블명입니다: {table_name}",
                error_code="TABLE_NOT_WHITELISTED",
                available_tables=list(self._table_whitelist)
            )
            
        # 기본 식별자 검증
        return self.validator.validate_identifier(table_name)
        
    def validate_column_name(self, table_name: str, column_name: str) -> bool:
        """컬럼명 검증"""
        # 먼저 테이블명 검증
        self.validate_table_name(table_name)
        
        # 컬럼 화이트리스트 검증
        if table_name not in self._column_whitelist:
            raise SecurityError(
                f"테이블 '{table_name}'의 컬럼 정보를 찾을 수 없습니다.",
                error_code="TABLE_COLUMNS_NOT_FOUND"
            )
            
        if column_name not in self._column_whitelist[table_name]:
            raise SecurityError(
                f"테이블 '{table_name}'에 컬럼 '{column_name}'이 존재하지 않습니다.",
                error_code="COLUMN_NOT_WHITELISTED",
                available_columns=list(self._column_whitelist[table_name])
            )
            
        # 기본 식별자 검증
        return self.validator.validate_identifier(column_name)
        
    def get_safe_identifier(self, identifier: str, db_type: str = "mysql") -> str:
        """안전한 식별자 인용부호 처리"""
        if db_type.lower() == "mysql":
            return f"`{identifier}`"
        elif db_type.lower() == "postgresql":
            return f'"{identifier}"'
        else:
            return identifier
            
    def get_table_schema(self, table_name: str) -> Dict:
        """테이블 스키마 정보 반환"""
        self.validate_table_name(table_name)
        return self._schema_cache.get(table_name, {})
        
    def get_available_tables(self) -> List[str]:
        """사용 가능한 테이블 목록 반환"""
        return list(self._table_whitelist)
        
    def get_available_columns(self, table_name: str) -> List[str]:
        """테이블의 사용 가능한 컬럼 목록 반환"""
        self.validate_table_name(table_name)
        return list(self._column_whitelist.get(table_name, set()))
        
    def invalidate_cache(self) -> None:
        """캐시 무효화"""
        self._cache_valid = False
        self._table_whitelist.clear()
        self._column_whitelist.clear()
        self._schema_cache.clear()
        logger.info("스키마 캐시가 무효화되었습니다.")
        
    def is_cache_valid(self) -> bool:
        """캐시 유효성 확인"""
        return self._cache_valid
        
    def validate_identifier(self, identifier: str) -> bool:
        """
        일반적인 식별자 검증 (화이트리스트 없이)
        
        Args:
            identifier: 검증할 식별자
            
        Returns:
            bool: 검증 통과 여부
            
        Raises:
            SecurityError: 보안 위반 감지 시
        """
        return self.validator.validate_identifier(identifier)
