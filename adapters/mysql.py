"""
MySQL/MariaDB adapter for MCP server.
"""

import pymysql
import logging
from typing import Dict, List, Any
from .base import DatabaseAdapter

logger = logging.getLogger(__name__)

class MySQLAdapter(DatabaseAdapter):
    """MySQL/MariaDB 어댑터"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        
    def connect(self):
        """MySQL 데이터베이스 연결 (보안 강화)"""
        try:
            # 보안 강화된 연결 설정
            secure_config = self.config.copy()
            
            # Local infile 비활성화 (보안)
            secure_config['local_infile'] = False
            
            # 연결 타임아웃 설정
            secure_config['connect_timeout'] = 10
            secure_config['read_timeout'] = 30
            secure_config['write_timeout'] = 30
            
            self.connection = pymysql.connect(**secure_config)
            
            # 추가 보안 설정
            with self.connection.cursor() as cursor:
                # SQL 모드 설정 (엄격 모드)
                cursor.execute("SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'")
                
                # Local infile 비활성화 (세션 단위). 권한 부족 시 무시
                try:
                    cursor.execute("SET SESSION local_infile = 0")
                except Exception:
                    pass
                
                # 보안 관련 변수 설정 (권한 없을 수 있음) - 실패해도 무시
                try:
                    cursor.execute("SET SESSION sql_log_bin = 0")  # 바이너리 로그 비활성화 (세션)
                except Exception:
                    pass
                
            logger.info("MySQL 데이터베이스 연결 성공 (보안 강화)")
            
            # 스키마 캐시 로드
            self.identifier_manager.load_schema_cache(self)
            
        except Exception as e:
            logger.error(f"MySQL 연결 실패: {str(e)}")
            raise
            
    def disconnect(self):
        """MySQL 데이터베이스 연결 해제"""
        if self.connection:
            self.connection.close()
            self.connection = None
            
    def _quote_identifier(self, identifier: str) -> str:
        """MySQL 식별자 인용부호 처리"""
        return f"`{identifier}`"
        
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """MySQL 쿼리 실행 (보안 강화)"""
        try:
            # 1. 읽기 전용 모드 검증
            if self.read_only:
                self.validator.validate_query(query, "mysql")
            
            # 2. 쿼리 실행
            with self.connection.cursor() as cursor:
                cursor.execute(query, params or ())
                
                # 결과가 있는 경우에만 컬럼 정보 추출
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"쿼리 실행 실패: {str(e)}")
            raise
            
    def get_tables(self) -> List[str]:
        """테이블 목록 조회"""
        with self.connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            return [row[0] for row in cursor.fetchall()]
            
    def get_table_schema(self, table_name: str) -> List[Dict]:
        """테이블 스키마 조회"""
        with self.connection.cursor() as cursor:
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = cursor.fetchall()
            
            return [
                {
                    "name": col[0],
                    "type": col[1],
                    "nullable": col[2] == "YES",
                    "key": col[3],
                    "default": col[4],
                    "extra": col[5]
                } for col in columns
            ]
            
    def get_foreign_keys(self, table_name: str) -> List[Dict]:
        """외래키 정보 조회"""
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND REFERENCED_TABLE_NAME IS NOT NULL
            """, (self.config["db"], table_name))
            
            foreign_keys = cursor.fetchall()
            return [
                {
                    "column": fk[0],
                    "referenced_table": fk[1],
                    "referenced_column": fk[2]
                } for fk in foreign_keys
            ]
            
    def get_table_stats(self, table_name: str) -> Dict:
        """테이블 통계 정보 (보안 강화)"""
        try:
            # 1. 테이블명 검증
            self.identifier_manager.validate_table_name(table_name)
            
            with self.connection.cursor() as cursor:
                # 2. 안전한 테이블명 사용
                safe_table_name = self.identifier_manager.get_safe_identifier(table_name, "mysql")
                
                # 3. 전체 행 수 조회 (파라미터 바인딩)
                cursor.execute(f"SELECT COUNT(*) FROM {safe_table_name}")
                total_rows = cursor.fetchone()[0]
                
                # 4. 컬럼별 통계
                schema = self.get_table_schema(table_name)
                column_stats = {}
                
                for col in schema:
                    col_name = col['name']
                    
                    # 컬럼명 검증
                    self.identifier_manager.validate_column_name(table_name, col_name)
                    safe_col_name = self.identifier_manager.get_safe_identifier(col_name, "mysql")
                    
                    # NULL 값 비율 (파라미터 바인딩)
                    cursor.execute(f"SELECT COUNT(*) FROM {safe_table_name} WHERE {safe_col_name} IS NULL")
                    null_count = cursor.fetchone()[0]
                    null_ratio = (null_count / total_rows * 100) if total_rows > 0 else 0
                    
                    # 고유값 수 (파라미터 바인딩)
                    cursor.execute(f"SELECT COUNT(DISTINCT {safe_col_name}) FROM {safe_table_name}")
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
            logger.error(f"테이블 통계 조회 실패: {str(e)}")
            raise
            
    def get_table_size(self, table_name: str) -> Dict:
        """테이블 크기 정보"""
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    table_rows,
                    data_length,
                    index_length,
                    data_free
                FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
            """, (self.config["db"], table_name))
            
            result = cursor.fetchone()
            if result:
                rows, data_size, index_size, free_size = result
                return {
                    "rows": rows or 0,
                    "data_size_mb": round((data_size or 0) / (1024 * 1024), 2),
                    "index_size_mb": round((index_size or 0) / (1024 * 1024), 2),
                    "free_size_mb": round((free_size or 0) / (1024 * 1024), 2),
                    "total_size_mb": round(((data_size or 0) + (index_size or 0)) / (1024 * 1024), 2)
                }
            return {}
            
    def get_indexes(self, table_name: str = None) -> Dict:
        """인덱스 정보 조회"""
        with self.connection.cursor() as cursor:
            if table_name:
                cursor.execute("""
                    SELECT 
                        index_name,
                        column_name,
                        cardinality,
                        nullable,
                        index_type
                    FROM information_schema.statistics
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY index_name, seq_in_index
                """, (self.config["db"], table_name))
                
                indexes = cursor.fetchall()
                result = {}
                
                for idx in indexes:
                    index_name = idx[0]
                    if index_name not in result:
                        result[index_name] = {
                            "columns": [],
                            "cardinality": idx[2],
                            "type": idx[4]
                        }
                    
                    result[index_name]["columns"].append({
                        "name": idx[1],
                        "nullable": idx[3]
                    })
                
                return {table_name: result}
            else:
                # 모든 테이블의 인덱스 정보
                cursor.execute("""
                    SELECT 
                        table_name,
                        index_name,
                        column_name,
                        cardinality,
                        nullable,
                        index_type
                    FROM information_schema.statistics
                    WHERE table_schema = %s
                    ORDER BY table_name, index_name, seq_in_index
                """, (self.config["db"],))
                
                indexes = cursor.fetchall()
                result = {}
                
                for idx in indexes:
                    table_name, index_name = idx[0], idx[1]
                    
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
                
                return result
                
    def explain_query(self, query: str) -> Dict:
        """쿼리 실행 계획 분석"""
        with self.connection.cursor() as cursor:
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
            
    def get_db_status(self) -> Dict:
        """데이터베이스 상태 정보"""
        with self.connection.cursor() as cursor:
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
            """, (self.config["db"],))
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