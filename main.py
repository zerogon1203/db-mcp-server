from mcp.server.fastmcp import FastMCP
import pymysql
import os
import logging
import sys
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# .env 로드
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "db": os.getenv("DB_NAME"),
    "charset": os.getenv("DB_CHARSET", "utf8mb4")
}

logger.info("MCP 서버 시작")
logger.info(f"데이터베이스 설정: {DB_CONFIG}")

# MCP 서버 생성 (stdio 모드)
mcp = FastMCP(
    name="MySQLPlugin",
    mode="stdio",
    version="1.0.0",
    description="MySQL 데이터베이스 스키마 조회 도구"
)

@mcp.tool()
def get_schema() -> dict:
    """데이터베이스 스키마를 반환합니다."""
    try:
        logger.info("데이터베이스 연결 시도")
        conn = pymysql.connect(**DB_CONFIG)
        logger.info("데이터베이스 연결 성공")
        
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            logger.info(f"테이블 목록: {tables}")
            schema = {}

            for table in tables:
                cursor.execute(f"DESCRIBE `{table}`")
                columns = cursor.fetchall()
                schema[table] = {
                    "columns": [
                        {
                            "Field": col[0],
                            "Type": col[1],
                            "Null": col[2],
                            "Key": col[3],
                            "Default": col[4],
                            "Extra": col[5]
                        } for col in columns
                    ]
                }

                # 외래키 정보
                cursor.execute("""
                    SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND REFERENCED_TABLE_NAME IS NOT NULL
                """, (DB_CONFIG["db"], table))

                foreign_keys = cursor.fetchall()
                if foreign_keys:
                    schema[table]["foreign_keys"] = [
                        {
                            "column": fk[0],
                            "references": {
                                "table": fk[1],
                                "column": fk[2]
                            }
                        } for fk in foreign_keys
                    ]
        conn.close()
        logger.info("스키마 정보 조회 완료")
        return {"schema": schema}
    except Exception as e:
        logger.error(f"스키마 조회 중 오류 발생: {str(e)}")
        raise

@mcp.tool()
def get_table_stats(table_name: str) -> dict:
    """테이블의 기본 통계 정보를 반환합니다."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # 전체 행 수 조회
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            total_rows = cursor.fetchone()[0]
            
            # 컬럼별 통계
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = cursor.fetchall()
            column_stats = {}
            
            for col in columns:
                col_name = col[0]
                # NULL 값 비율
                cursor.execute(f"SELECT COUNT(*) FROM `{table_name}` WHERE `{col_name}` IS NULL")
                null_count = cursor.fetchone()[0]
                null_ratio = (null_count / total_rows * 100) if total_rows > 0 else 0
                
                # 고유값 수
                cursor.execute(f"SELECT COUNT(DISTINCT `{col_name}`) FROM `{table_name}`")
                unique_count = cursor.fetchone()[0]
                
                column_stats[col_name] = {
                    "total_rows": total_rows,
                    "null_count": null_count,
                    "null_ratio": round(null_ratio, 2),
                    "unique_values": unique_count
                }
            
            return {
                "table_name": table_name,
                "total_rows": total_rows,
                "column_stats": column_stats
            }
    except Exception as e:
        logger.error(f"테이블 통계 조회 중 오류 발생: {str(e)}")
        raise
    finally:
        conn.close()

@mcp.tool()
def get_sample_data(table_name: str, limit: int = 5) -> dict:
    """테이블의 샘플 데이터를 반환합니다."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # 컬럼 정보 조회
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = [col[0] for col in cursor.fetchall()]
            
            # 샘플 데이터 조회
            cursor.execute(f"SELECT * FROM `{table_name}` LIMIT {limit}")
            rows = cursor.fetchall()
            
            # 결과 포맷팅
            result = {
                "table_name": table_name,
                "columns": columns,
                "data": [dict(zip(columns, row)) for row in rows]
            }
            
            return result
    except Exception as e:
        logger.error(f"샘플 데이터 조회 중 오류 발생: {str(e)}")
        raise
    finally:
        conn.close()

@mcp.tool()
def get_column_stats(table_name: str, column_name: str) -> dict:
    """특정 컬럼의 상세 통계 정보를 반환합니다."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # 컬럼 타입 확인
            cursor.execute(f"DESCRIBE `{table_name}` `{column_name}`")
            col_type = cursor.fetchone()[1].lower()
            
            stats = {}
            
            # 숫자형 컬럼인 경우
            if any(num_type in col_type for num_type in ['int', 'float', 'double', 'decimal']):
                cursor.execute(f"""
                    SELECT 
                        MIN(`{column_name}`) as min_value,
                        MAX(`{column_name}`) as max_value,
                        AVG(`{column_name}`) as avg_value,
                        COUNT(*) as total_count,
                        COUNT(DISTINCT `{column_name}`) as unique_count
                    FROM `{table_name}`
                """)
                row = cursor.fetchone()
                stats = {
                    "min_value": row[0],
                    "max_value": row[1],
                    "avg_value": round(float(row[2]), 2) if row[2] is not None else None,
                    "total_count": row[3],
                    "unique_count": row[4]
                }
            
            # 날짜형 컬럼인 경우
            elif any(date_type in col_type for date_type in ['date', 'datetime', 'timestamp']):
                cursor.execute(f"""
                    SELECT 
                        MIN(`{column_name}`) as min_date,
                        MAX(`{column_name}`) as max_date,
                        COUNT(*) as total_count,
                        COUNT(DISTINCT `{column_name}`) as unique_count
                    FROM `{table_name}`
                """)
                row = cursor.fetchone()
                stats = {
                    "min_date": row[0],
                    "max_date": row[1],
                    "total_count": row[2],
                    "unique_count": row[3]
                }
            
            # 문자열 컬럼인 경우
            else:
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as total_count,
                        COUNT(DISTINCT `{column_name}`) as unique_count,
                        AVG(LENGTH(`{column_name}`)) as avg_length
                    FROM `{table_name}`
                """)
                row = cursor.fetchone()
                stats = {
                    "total_count": row[0],
                    "unique_count": row[1],
                    "avg_length": round(float(row[2]), 2) if row[2] is not None else None
                }
            
            return {
                "table_name": table_name,
                "column_name": column_name,
                "column_type": col_type,
                "stats": stats
            }
    except Exception as e:
        logger.error(f"컬럼 통계 조회 중 오류 발생: {str(e)}")
        raise
    finally:
        conn.close()

@mcp.tool()
def execute_query(query: str) -> dict:
    """안전한 읽기 전용 쿼리를 실행합니다."""
    try:
        # SELECT 쿼리만 허용
        if not query.strip().upper().startswith('SELECT'):
            raise ValueError("읽기 전용 쿼리(SELECT)만 실행 가능합니다.")
        
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            result = {
                "columns": columns,
                "data": [dict(zip(columns, row)) for row in rows],
                "row_count": len(rows)
            }
            
            return result
    except Exception as e:
        logger.error(f"쿼리 실행 중 오류 발생: {str(e)}")
        raise
    finally:
        conn.close()

@mcp.tool()
def explain_query(query: str) -> dict:
    """쿼리의 실행 계획을 분석합니다."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # EXPLAIN 실행
            cursor.execute(f"EXPLAIN FORMAT=JSON {query}")
            explain_result = cursor.fetchone()[0]
            
            # 추가 성능 정보 수집
            cursor.execute("SHOW SESSION STATUS LIKE 'Handler%'")
            handler_stats = dict(cursor.fetchall())
            
            return {
                "explain_plan": explain_result,
                "handler_stats": handler_stats
            }
    except Exception as e:
        logger.error(f"쿼리 실행 계획 분석 중 오류 발생: {str(e)}")
        raise
    finally:
        conn.close()

@mcp.tool()
def optimize_query(query: str) -> dict:
    """쿼리 최적화 제안을 제공합니다."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # 현재 쿼리의 실행 계획 분석
            cursor.execute(f"EXPLAIN FORMAT=JSON {query}")
            current_plan = cursor.fetchone()[0]
            
            # 사용된 테이블 식별
            cursor.execute("""
                SELECT TABLE_NAME, COLUMN_NAME, INDEX_NAME
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = %s
            """, (DB_CONFIG["db"],))
            table_indexes = cursor.fetchall()
            
            # 최적화 제안 생성
            suggestions = []
            
            # 1. 인덱스 사용 분석
            if "filesort" in str(current_plan).lower():
                suggestions.append({
                    "type": "index",
                    "message": "정렬 작업이 발생하고 있습니다. ORDER BY 절에 사용된 컬럼에 대한 인덱스 추가를 고려하세요."
                })
            
            # 2. 전체 테이블 스캔 분석
            if "ALL" in str(current_plan):
                suggestions.append({
                    "type": "full_scan",
                    "message": "전체 테이블 스캔이 발생하고 있습니다. WHERE 절에 사용된 컬럼에 대한 인덱스 추가를 고려하세요."
                })
            
            # 3. 임시 테이블 사용 분석
            if "temporary" in str(current_plan).lower():
                suggestions.append({
                    "type": "temporary",
                    "message": "임시 테이블이 사용되고 있습니다. GROUP BY나 ORDER BY 절의 최적화를 고려하세요."
                })
            
            # 4. 서브쿼리 최적화 제안
            if "subquery" in str(current_plan).lower():
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
        logger.error(f"쿼리 최적화 분석 중 오류 발생: {str(e)}")
        raise
    finally:
        conn.close()

@mcp.tool()
def get_db_status() -> dict:
    """데이터베이스의 현재 상태 정보를 반환합니다."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # 서버 상태 정보
            cursor.execute("SHOW GLOBAL STATUS")
            global_status = dict(cursor.fetchall())
            
            # 변수 정보
            cursor.execute("SHOW GLOBAL VARIABLES")
            global_variables = dict(cursor.fetchall())
            
            # 프로세스 목록
            cursor.execute("SHOW PROCESSLIST")
            processes = cursor.fetchall()
            
            # 연결 정보
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_connections,
                    COUNT(CASE WHEN command = 'Sleep' THEN 1 END) as sleeping_connections,
                    COUNT(CASE WHEN command != 'Sleep' THEN 1 END) as active_connections
                FROM information_schema.processlist
                WHERE db = %s
            """, (DB_CONFIG["db"],))
            connection_stats = dict(zip(['total', 'sleeping', 'active'], cursor.fetchone()))
            
            return {
                "global_status": {
                    "queries": global_status.get("Questions", 0),
                    "slow_queries": global_status.get("Slow_queries", 0),
                    "threads_connected": global_status.get("Threads_connected", 0),
                    "threads_running": global_status.get("Threads_running", 0),
                    "bytes_received": global_status.get("Bytes_received", 0),
                    "bytes_sent": global_status.get("Bytes_sent", 0)
                },
                "global_variables": {
                    "max_connections": global_variables.get("max_connections", 0),
                    "version": global_variables.get("version", ""),
                    "character_set": global_variables.get("character_set_server", ""),
                    "collation": global_variables.get("collation_server", "")
                },
                "connection_stats": connection_stats,
                "processes": [
                    {
                        "id": p[0],
                        "user": p[1],
                        "host": p[2],
                        "db": p[3],
                        "command": p[4],
                        "time": p[5],
                        "state": p[6],
                        "info": p[7]
                    } for p in processes
                ]
            }
    except Exception as e:
        logger.error(f"데이터베이스 상태 조회 중 오류 발생: {str(e)}")
        raise
    finally:
        conn.close()

@mcp.tool()
def get_table_size() -> dict:
    """테이블별 크기 정보를 반환합니다."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    table_name,
                    table_rows,
                    data_length,
                    index_length,
                    data_free
                FROM information_schema.tables
                WHERE table_schema = %s
            """, (DB_CONFIG["db"],))
            
            tables = cursor.fetchall()
            result = {}
            
            for table in tables:
                table_name = table[0]
                result[table_name] = {
                    "rows": table[1],
                    "data_size_mb": round(table[2] / (1024 * 1024), 2),
                    "index_size_mb": round(table[3] / (1024 * 1024), 2),
                    "free_size_mb": round(table[4] / (1024 * 1024), 2),
                    "total_size_mb": round((table[2] + table[3]) / (1024 * 1024), 2)
                }
            
            return {"tables": result}
    except Exception as e:
        logger.error(f"테이블 크기 조회 중 오류 발생: {str(e)}")
        raise
    finally:
        conn.close()

@mcp.tool()
def get_index_usage() -> dict:
    """인덱스 사용 통계를 반환합니다."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # 인덱스 통계 정보
            cursor.execute("""
                SELECT 
                    t.table_name,
                    s.index_name,
                    s.column_name,
                    s.cardinality,
                    s.nullable,
                    s.index_type
                FROM information_schema.statistics s
                JOIN information_schema.tables t
                    ON s.table_schema = t.table_schema
                    AND s.table_name = t.table_name
                WHERE s.table_schema = %s
                ORDER BY t.table_name, s.index_name, s.seq_in_index
            """, (DB_CONFIG["db"],))
            
            indexes = cursor.fetchall()
            result = {}
            
            for idx in indexes:
                table_name = idx[0]
                index_name = idx[1]
                
                if table_name not in result:
                    result[table_name] = {}
                
                if index_name not in result[table_name]:
                    result[table_name][index_name] = {
                        "columns": [],
                        "cardinality": idx[3],
                        "type": idx[5]
                    }
                
                result[table_name][index_name]["columns"].append({
                    "name": idx[2],
                    "nullable": idx[4]
                })
            
            return {"indexes": result}
    except Exception as e:
        logger.error(f"인덱스 사용 통계 조회 중 오류 발생: {str(e)}")
        raise
    finally:
        conn.close()

@mcp.tool()
def analyze_performance() -> dict:
    """데이터베이스 성능 병목 지점을 분석합니다."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # 느린 쿼리 로그 분석
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Slow_queries'")
            slow_queries = cursor.fetchone()[1]
            
            # 테이블 스캔 통계
            cursor.execute("""
                SELECT 
                    table_name,
                    table_rows,
                    data_length,
                    index_length
                FROM information_schema.tables
                WHERE table_schema = %s
            """, (DB_CONFIG["db"],))
            table_stats = cursor.fetchall()
            
            # 인덱스 사용 통계
            cursor.execute("""
                SELECT 
                    table_name,
                    index_name,
                    column_name,
                    cardinality
                FROM information_schema.statistics
                WHERE table_schema = %s
            """, (DB_CONFIG["db"],))
            index_stats = cursor.fetchall()
            
            # 성능 병목 지점 분석
            bottlenecks = []
            
            # 1. 큰 테이블 분석
            for table in table_stats:
                table_name, rows, data_size, index_size = table
                if rows > 1000000:  # 100만 행 이상
                    bottlenecks.append({
                        "type": "large_table",
                        "table": table_name,
                        "rows": rows,
                        "message": f"테이블 '{table_name}'이(가) {rows:,}개의 행을 가지고 있습니다. 파티셔닝을 고려하세요."
                    })
                
                # 인덱스 크기가 데이터 크기보다 큰 경우
                if index_size > data_size * 1.5:  # 인덱스가 데이터의 1.5배 이상
                    bottlenecks.append({
                        "type": "large_index",
                        "table": table_name,
                        "index_size_mb": round(index_size / (1024 * 1024), 2),
                        "data_size_mb": round(data_size / (1024 * 1024), 2),
                        "message": f"테이블 '{table_name}'의 인덱스 크기가 데이터 크기보다 큽니다. 불필요한 인덱스를 검토하세요."
                    })
            
            # 2. 인덱스 카디널리티 분석
            for idx in index_stats:
                table_name, index_name, column_name, cardinality = idx
                if cardinality < 10:  # 카디널리티가 매우 낮은 경우
                    bottlenecks.append({
                        "type": "low_cardinality",
                        "table": table_name,
                        "index": index_name,
                        "column": column_name,
                        "cardinality": cardinality,
                        "message": f"인덱스 '{index_name}'의 카디널리티가 매우 낮습니다. 이 인덱스의 효율성을 검토하세요."
                    })
            
            return {
                "slow_queries": int(slow_queries),
                "bottlenecks": bottlenecks,
                "recommendations": [
                    "큰 테이블의 경우 파티셔닝을 고려하세요.",
                    "불필요한 인덱스를 제거하거나 최적화하세요.",
                    "낮은 카디널리티를 가진 인덱스를 검토하세요.",
                    "정기적인 ANALYZE TABLE을 실행하세요."
                ]
            }
    except Exception as e:
        logger.error(f"성능 분석 중 오류 발생: {str(e)}")
        raise
    finally:
        conn.close()

@mcp.tool()
def suggest_indexes(table_name: str = None) -> dict:
    """인덱스 생성 제안을 제공합니다."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # 테이블 목록 조회
            if table_name:
                tables = [(table_name,)]
            else:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
            
            suggestions = {}
            
            for table in tables:
                table_name = table[0]
                
                # 1. 외래키 컬럼 분석
                cursor.execute("""
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = %s 
                    AND REFERENCED_TABLE_NAME IS NOT NULL
                """, (DB_CONFIG["db"], table_name))
                foreign_keys = [row[0] for row in cursor.fetchall()]
                
                # 2. WHERE 절에서 자주 사용되는 컬럼 분석
                cursor.execute("""
                    SELECT COLUMN_NAME, COUNT(*) as usage_count
                    FROM INFORMATION_SCHEMA.STATISTICS
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = %s
                    GROUP BY COLUMN_NAME
                    ORDER BY usage_count DESC
                """, (DB_CONFIG["db"], table_name))
                column_usage = cursor.fetchall()
                
                # 3. ORDER BY, GROUP BY에서 사용되는 컬럼 분석
                cursor.execute("""
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.STATISTICS
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = %s
                    AND INDEX_NAME = 'PRIMARY'
                """, (DB_CONFIG["db"], table_name))
                primary_keys = [row[0] for row in cursor.fetchall()]
                
                table_suggestions = []
                
                # 외래키에 대한 인덱스 제안
                for fk in foreign_keys:
                    if fk not in primary_keys:
                        table_suggestions.append({
                            "type": "foreign_key",
                            "column": fk,
                            "reason": "외래키 컬럼에 대한 인덱스가 없습니다.",
                            "suggestion": f"CREATE INDEX idx_{table_name}_{fk} ON {table_name} ({fk});"
                        })
                
                # 자주 사용되는 컬럼에 대한 인덱스 제안
                for col, usage in column_usage:
                    if col not in primary_keys and col not in foreign_keys:
                        table_suggestions.append({
                            "type": "frequent_usage",
                            "column": col,
                            "usage_count": usage,
                            "reason": f"컬럼이 {usage}번 사용되었습니다.",
                            "suggestion": f"CREATE INDEX idx_{table_name}_{col} ON {table_name} ({col});"
                        })
                
                if table_suggestions:
                    suggestions[table_name] = table_suggestions
            
            return {
                "suggestions": suggestions,
                "general_recommendations": [
                    "복합 인덱스는 자주 사용되는 순서대로 컬럼을 배치하세요.",
                    "인덱스는 선택도(카디널리티)가 높은 컬럼부터 포함하세요.",
                    "불필요한 인덱스는 성능에 영향을 줄 수 있으므로 주의하세요."
                ]
            }
    except Exception as e:
        logger.error(f"인덱스 제안 생성 중 오류 발생: {str(e)}")
        raise
    finally:
        conn.close()

@mcp.tool()
def optimize_tables() -> dict:
    """테이블 최적화 제안을 제공합니다."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # 테이블 상태 분석
            cursor.execute("""
                SELECT 
                    table_name,
                    table_rows,
                    data_length,
                    index_length,
                    data_free,
                    update_time
                FROM information_schema.tables
                WHERE table_schema = %s
            """, (DB_CONFIG["db"],))
            tables = cursor.fetchall()
            
            optimization_suggestions = {}
            
            for table in tables:
                table_name, rows, data_size, index_size, free_size, update_time = table
                
                # 테이블별 최적화 제안
                table_suggestions = []
                
                # 1. 데이터 조각화 분석
                if free_size > data_size * 0.1:  # 여유 공간이 10% 이상
                    table_suggestions.append({
                        "type": "fragmentation",
                        "severity": "high",
                        "message": f"테이블 '{table_name}'이(가) {round(free_size / (1024 * 1024), 2)}MB의 조각화된 공간을 가지고 있습니다.",
                        "suggestion": f"OPTIMIZE TABLE {table_name};"
                    })
                
                # 2. 오래된 업데이트 시간 분석
                if update_time:
                    from datetime import datetime
                    last_update = datetime.strptime(str(update_time), '%Y-%m-%d %H:%M:%S')
                    if (datetime.now() - last_update).days > 30:
                        table_suggestions.append({
                            "type": "stale_stats",
                            "severity": "medium",
                            "message": f"테이블 '{table_name}'의 통계가 {last_update.strftime('%Y-%m-%d')} 이후 업데이트되지 않았습니다.",
                            "suggestion": f"ANALYZE TABLE {table_name};"
                        })
                
                # 3. 큰 테이블 분석
                if rows > 1000000:  # 100만 행 이상
                    table_suggestions.append({
                        "type": "large_table",
                        "severity": "medium",
                        "message": f"테이블 '{table_name}'이(가) {rows:,}개의 행을 가지고 있습니다.",
                        "suggestions": [
                            f"파티셔닝 고려: ALTER TABLE {table_name} PARTITION BY RANGE (id) (...);",
                            "아카이브 테이블 생성 고려",
                            "불필요한 데이터 정리"
                        ]
                    })
                
                if table_suggestions:
                    optimization_suggestions[table_name] = table_suggestions
            
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
        logger.error(f"테이블 최적화 제안 생성 중 오류 발생: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    try:
        logger.info("MCP 서버 실행")
        mcp.run()
    except Exception as e:
        logger.error(f"MCP 서버 실행 중 오류 발생: {str(e)}")
        raise