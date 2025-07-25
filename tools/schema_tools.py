"""
Schema-related MCP tools.
"""

def register_schema_tools(mcp, adapter):
    """스키마 관련 도구들을 MCP 서버에 등록"""
    
    @mcp.tool()
    def get_schema() -> dict:
        """데이터베이스 스키마를 반환합니다."""
        try:
            with adapter:
                tables = adapter.get_tables()
                schema = {}
                
                for table in tables:
                    columns = adapter.get_table_schema(table)
                    schema[table] = {"columns": columns}
                    
                    # 외래키 정보 추가
                    foreign_keys = adapter.get_foreign_keys(table)
                    if foreign_keys:
                        schema[table]["foreign_keys"] = foreign_keys
                
                return {"schema": schema}
        except Exception as e:
            raise
    
    @mcp.tool()
    def get_table_stats(table_name: str) -> dict:
        """테이블의 기본 통계 정보를 반환합니다."""
        try:
            with adapter:
                return adapter.get_table_stats(table_name)
        except Exception as e:
            raise
    
    @mcp.tool()
    def get_sample_data(table_name: str, limit: int = 5) -> dict:
        """테이블의 샘플 데이터를 반환합니다."""
        try:
            with adapter:
                return adapter.get_sample_data(table_name, limit)
        except Exception as e:
            raise
    
    @mcp.tool()
    def get_column_stats(table_name: str, column_name: str) -> dict:
        """특정 컬럼의 상세 통계 정보를 반환합니다."""
        try:
            with adapter:
                # 컬럼별 상세 통계는 어댑터에서 구현하거나 여기서 처리
                # 우선 기본 통계에서 해당 컬럼만 추출
                table_stats = adapter.get_table_stats(table_name)
                
                if column_name in table_stats.get("column_stats", {}):
                    col_stats = table_stats["column_stats"][column_name]
                    
                    # 컬럼 타입 정보 추가
                    schema = adapter.get_table_schema(table_name)
                    col_type = None
                    for col in schema:
                        if col["name"] == column_name:
                            col_type = col["type"]
                            break
                    
                    return {
                        "table_name": table_name,
                        "column_name": column_name,
                        "column_type": col_type,
                        "stats": col_stats
                    }
                else:
                    raise ValueError(f"컬럼 '{column_name}'이 테이블 '{table_name}'에 존재하지 않습니다.")
        except Exception as e:
            raise 