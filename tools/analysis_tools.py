"""
Analysis and performance-related MCP tools.
"""

import logging

logger = logging.getLogger(__name__)

def register_analysis_tools(mcp, adapter):
    """분석 관련 도구들을 MCP 서버에 등록"""
    
    @mcp.tool()
    def execute_query(query: str, params: list = None) -> dict:
        """안전한 읽기 전용 쿼리를 실행합니다.

        Args:
            query: 실행할 SELECT 쿼리 (값은 반드시 %s 플레이스홀더 사용)
            params: 값 파라미터 (리스트/배열). 없으면 None
        """
        try:
            # 1. 쿼리 검증
            adapter.validator.validate_query(query, adapter.get_db_type())
            
            with adapter:
                bound_params = tuple(params) if params is not None else None
                result = adapter.execute_query(query, bound_params)
                return {
                    "columns": list(result[0].keys()) if result else [],
                    "data": result,
                    "row_count": len(result)
                }
        except Exception as e:
            logger.error(f"쿼리 실행 실패: {str(e)}")
            raise
    
    @mcp.tool()
    def explain_query(query: str) -> dict:
        """쿼리의 실행 계획을 분석합니다."""
        try:
            # 1. 쿼리 검증
            adapter.validator.validate_query(query, adapter.get_db_type())
            
            with adapter:
                return adapter.explain_query(query)
        except Exception as e:
            logger.error(f"쿼리 실행 계획 분석 실패: {str(e)}")
            raise
    
    @mcp.tool()
    def optimize_query(query: str) -> dict:
        """쿼리 최적화 제안을 제공합니다."""
        try:
            # 1. 쿼리 검증
            adapter.validator.validate_query(query, adapter.get_db_type())
            
            with adapter:
                # 현재 쿼리의 실행 계획 분석
                current_plan = adapter.explain_query(query)
                
                # 사용된 테이블들의 인덱스 정보
                tables = adapter.get_tables()
                table_indexes = {}
                for table in tables:
                    table_indexes[table] = adapter.get_indexes(table)
                
                # 최적화 제안 생성
                suggestions = []
                
                # 실행 계획 기반 제안 (DB 타입별로 다름)
                plan_str = str(current_plan).lower()
                
                if "filesort" in plan_str or "sort" in plan_str:
                    suggestions.append({
                        "type": "index",
                        "message": "정렬 작업이 발생하고 있습니다. ORDER BY 절에 사용된 컬럼에 대한 인덱스 추가를 고려하세요."
                    })
                
                if "full" in plan_str and "scan" in plan_str:
                    suggestions.append({
                        "type": "full_scan",
                        "message": "전체 테이블 스캔이 발생하고 있습니다. WHERE 절에 사용된 컬럼에 대한 인덱스 추가를 고려하세요."
                    })
                
                if "temporary" in plan_str or "temp" in plan_str:
                    suggestions.append({
                        "type": "temporary",
                        "message": "임시 테이블이 사용되고 있습니다. GROUP BY나 ORDER BY 절의 최적화를 고려하세요."
                    })
                
                if "subquery" in plan_str or "nested" in plan_str:
                    suggestions.append({
                        "type": "subquery",
                        "message": "서브쿼리가 사용되고 있습니다. JOIN으로 변경하는 것을 고려하세요."
                    })
                
                return {
                    "current_plan": current_plan,
                    "suggestions": suggestions,
                    "available_indexes": table_indexes
                }
        except Exception as e:
            raise
    
    @mcp.tool()
    def get_db_status() -> dict:
        """데이터베이스의 현재 상태 정보를 반환합니다."""
        try:
            with adapter:
                return adapter.get_db_status()
        except Exception as e:
            raise
    
    @mcp.tool()
    def get_table_size() -> dict:
        """테이블별 크기 정보를 반환합니다."""
        try:
            with adapter:
                tables = adapter.get_tables()
                result = {}
                
                for table in tables:
                    size_info = adapter.get_table_size(table)
                    if size_info:
                        result[table] = size_info
                
                return {"tables": result}
        except Exception as e:
            raise
    
    @mcp.tool()
    def get_index_usage() -> dict:
        """인덱스 사용 통계를 반환합니다."""
        try:
            with adapter:
                indexes = adapter.get_indexes()
                return {"indexes": indexes}
        except Exception as e:
            raise
    
    @mcp.tool()
    def analyze_performance() -> dict:
        """데이터베이스 성능 병목 지점을 분석합니다."""
        try:
            with adapter:
                tables = adapter.get_tables()
                bottlenecks = []
                
                # 각 테이블의 크기와 인덱스 분석
                for table in tables:
                    size_info = adapter.get_table_size(table)
                    if size_info:
                        rows = size_info.get("rows", 0)
                        data_size = size_info.get("data_size_mb", 0) * 1024 * 1024
                        index_size = size_info.get("index_size_mb", 0) * 1024 * 1024
                        
                        # 큰 테이블 분석
                        if rows > 1000000:
                            bottlenecks.append({
                                "type": "large_table",
                                "table": table,
                                "rows": rows,
                                "message": f"테이블 '{table}'이(가) {rows:,}개의 행을 가지고 있습니다. 파티셔닝을 고려하세요."
                            })
                        
                        # 인덱스 크기가 데이터 크기보다 큰 경우
                        if index_size > data_size * 1.5:
                            bottlenecks.append({
                                "type": "large_index",
                                "table": table,
                                "index_size_mb": round(index_size / (1024 * 1024), 2),
                                "data_size_mb": round(data_size / (1024 * 1024), 2),
                                "message": f"테이블 '{table}'의 인덱스 크기가 데이터 크기보다 큽니다. 불필요한 인덱스를 검토하세요."
                            })
                
                # 인덱스 카디널리티 분석
                all_indexes = adapter.get_indexes()
                for table_name, indexes in all_indexes.items():
                    for index_name, index_info in indexes.items():
                        cardinality = index_info.get("cardinality", 0)
                        if cardinality < 10:
                            bottlenecks.append({
                                "type": "low_cardinality",
                                "table": table_name,
                                "index": index_name,
                                "cardinality": cardinality,
                                "message": f"인덱스 '{index_name}'의 카디널리티가 매우 낮습니다. 이 인덱스의 효율성을 검토하세요."
                            })
                
                return {
                    "slow_queries": 0,  # DB별로 구현 필요
                    "bottlenecks": bottlenecks,
                    "recommendations": [
                        "큰 테이블의 경우 파티셔닝을 고려하세요.",
                        "불필요한 인덱스를 제거하거나 최적화하세요.",
                        "낮은 카디널리티를 가진 인덱스를 검토하세요.",
                        "정기적인 ANALYZE TABLE을 실행하세요."
                    ]
                }
        except Exception as e:
            raise
    
    @mcp.tool()
    def suggest_indexes(table_name: str = None) -> dict:
        """인덱스 생성 제안을 제공합니다."""
        try:
            with adapter:
                # 1. 테이블명 검증 (제공된 경우)
                if table_name:
                    adapter.identifier_manager.validate_table_name(table_name)
                    tables = [table_name]
                else:
                    tables = adapter.get_tables()
                    
                suggestions = {}
                
                for table in tables:
                    # 외래키 확인
                    foreign_keys = adapter.get_foreign_keys(table)
                    
                    # 기존 인덱스 확인
                    existing_indexes = adapter.get_indexes(table).get(table, {})
                    existing_columns = set()
                    for index_info in existing_indexes.values():
                        for col_info in index_info.get("columns", []):
                            existing_columns.add(col_info["name"])
                    
                    table_suggestions = []
                    
                    # 외래키에 대한 인덱스 제안
                    for fk in foreign_keys:
                        if fk["column"] not in existing_columns:
                            table_suggestions.append({
                                "type": "foreign_key",
                                "column": fk["column"],
                                "reason": "외래키 컬럼에 대한 인덱스가 없습니다.",
                                "suggestion": f"CREATE INDEX idx_{table}_{fk['column']} ON {table} ({fk['column']});"
                            })
                    
                    if table_suggestions:
                        suggestions[table] = table_suggestions
                
                return {
                    "suggestions": suggestions,
                    "general_recommendations": [
                        "복합 인덱스는 자주 사용되는 순서대로 컬럼을 배치하세요.",
                        "인덱스는 선택도(카디널리티)가 높은 컬럼부터 포함하세요.",
                        "불필요한 인덱스는 성능에 영향을 줄 수 있으므로 주의하세요."
                    ]
                }
        except Exception as e:
            raise
    
    @mcp.tool()
    def optimize_tables() -> dict:
        """테이블 최적화 제안을 제공합니다."""
        try:
            with adapter:
                tables = adapter.get_tables()
                optimization_suggestions = {}
                
                for table in tables:
                    size_info = adapter.get_table_size(table)
                    table_suggestions = []
                    
                    if size_info:
                        rows = size_info.get("rows", 0)
                        free_size_mb = size_info.get("free_size_mb", 0)
                        data_size_mb = size_info.get("data_size_mb", 0)
                        
                        # 데이터 조각화 분석 (MySQL 전용)
                        if free_size_mb > data_size_mb * 0.1:
                            table_suggestions.append({
                                "type": "fragmentation",
                                "severity": "high",
                                "message": f"테이블 '{table}'이(가) {free_size_mb}MB의 조각화된 공간을 가지고 있습니다.",
                                "suggestion": f"OPTIMIZE TABLE {table};"
                            })
                        
                        # 큰 테이블 분석
                        if rows > 1000000:
                            table_suggestions.append({
                                "type": "large_table",
                                "severity": "medium",
                                "message": f"테이블 '{table}'이(가) {rows:,}개의 행을 가지고 있습니다.",
                                "suggestions": [
                                    f"파티셔닝 고려",
                                    "아카이브 테이블 생성 고려",
                                    "불필요한 데이터 정리"
                                ]
                            })
                    
                    if table_suggestions:
                        optimization_suggestions[table] = table_suggestions
                
                return {
                    "optimization_suggestions": optimization_suggestions,
                    "general_recommendations": [
                        "정기적인 OPTIMIZE TABLE 실행을 고려하세요.",
                        "큰 테이블의 경우 파티셔닝을 검토하세요.",
                        "오래된 통계는 ANALYZE TABLE로 업데이트하세요.",
                        "불필요한 데이터는 아카이브하거나 삭제하세요."
                    ]
                }
        except Exception as e:
            raise