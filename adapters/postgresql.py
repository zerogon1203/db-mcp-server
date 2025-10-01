"""
PostgreSQL adapter for MCP server.
"""

import logging
from typing import Dict, List, Any
from .base import DatabaseAdapter

logger = logging.getLogger(__name__)

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL 어댑터"""
    
    def __init__(self, config: dict):
        if not PSYCOPG2_AVAILABLE:
            raise ImportError("psycopg2가 설치되지 않았습니다. 'pip install psycopg2-binary'를 실행하세요.")
        super().__init__(config)
        
    def connect(self):
        """PostgreSQL 데이터베이스 연결 (보안 강화)"""
        try:
            # PostgreSQL 연결 파라미터 변환
            pg_config = {
                'host': self.config.get('host', 'localhost'),
                'port': self.config.get('port', 5432),
                'database': self.config.get('db'),
                'user': self.config.get('user'),
                'password': self.config.get('password'),
                'connect_timeout': 10,
                'application_name': 'mcp-db-server-secure'
            }
            
            # SSL 강제 (가능한 경우)
            if 'sslmode' not in pg_config:
                pg_config['sslmode'] = 'prefer'
            
            self.connection = psycopg2.connect(**pg_config)
            self.connection.autocommit = True
            
            # 추가 보안 설정
            with self.connection.cursor() as cursor:
                # 보안 관련 설정
                cursor.execute("SET statement_timeout = '30s'")  # 쿼리 타임아웃
                cursor.execute("SET lock_timeout = '10s'")       # 락 타임아웃
                cursor.execute("SET idle_in_transaction_session_timeout = '60s'")  # 유휴 세션 타임아웃
                
            logger.info("PostgreSQL 데이터베이스 연결 성공 (보안 강화)")
            
            # 스키마 캐시 로드
            self.identifier_manager.load_schema_cache(self)
            
        except Exception as e:
            logger.error(f"PostgreSQL 연결 실패: {str(e)}")
            raise
            
    def disconnect(self):
        """PostgreSQL 데이터베이스 연결 해제"""
        if self.connection:
            self.connection.close()
            self.connection = None
            
    def _quote_identifier(self, identifier: str) -> str:
        """PostgreSQL 식별자 인용부호 처리"""
        return f'"{identifier}"'
        
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """PostgreSQL 쿼리 실행 (보안 강화)"""
        try:
            # 1. 읽기 전용 모드 검증
            if self.read_only:
                self.validator.validate_query(query, "postgresql")
            
            # 2. 쿼리 실행
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params or ())
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"쿼리 실행 실패: {str(e)}")
            raise
            
    def get_tables(self) -> List[str]:
        """테이블 목록 조회"""
        schema = self.config.get('schema', 'public')
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """, (schema,))
            return [row[0] for row in cursor.fetchall()]
            
    def get_table_schema(self, table_name: str) -> List[Dict]:
        """테이블 스키마 조회"""
        schema = self.config.get('schema', 'public')
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """, (schema, table_name))
            
            columns = cursor.fetchall()
            
            # 키 정보 조회
            cursor.execute("""
                SELECT a.attname, i.indisprimary, i.indisunique
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                JOIN pg_class c ON c.oid = i.indrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = %s AND c.relname = %s
            """, (schema, table_name))
            
            key_info = {}
            for row in cursor.fetchall():
                col_name, is_primary, is_unique = row
                key_type = ""
                if is_primary:
                    key_type = "PRI"
                elif is_unique:
                    key_type = "UNI"
                key_info[col_name] = key_type
            
            return [
                {
                    "name": col[0],
                    "type": self._format_pg_type(col[1], col[4], col[5], col[6]),
                    "nullable": col[2] == "YES",
                    "key": key_info.get(col[0], ""),
                    "default": col[3],
                    "extra": ""
                } for col in columns
            ]
            
    def _format_pg_type(self, data_type: str, char_length: int, num_precision: int, num_scale: int) -> str:
        """PostgreSQL 데이터 타입 포맷팅"""
        if data_type in ['character varying', 'varchar']:
            return f"varchar({char_length})" if char_length else "varchar"
        elif data_type == 'character':
            return f"char({char_length})" if char_length else "char"
        elif data_type in ['numeric', 'decimal']:
            if num_precision and num_scale:
                return f"numeric({num_precision},{num_scale})"
            elif num_precision:
                return f"numeric({num_precision})"
            else:
                return "numeric"
        return data_type
        
    def get_foreign_keys(self, table_name: str) -> List[Dict]:
        """외래키 정보 조회"""
        schema = self.config.get('schema', 'public')
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    kcu.column_name,
                    ccu.table_name AS referenced_table,
                    ccu.column_name AS referenced_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu 
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = %s
                    AND tc.table_name = %s
            """, (schema, table_name))
            
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
            
            schema = self.config.get('schema', 'public')
            with self.connection.cursor() as cursor:
                # 2. 안전한 테이블명 사용
                safe_schema = self.identifier_manager.get_safe_identifier(schema, "postgresql")
                safe_table_name = self.identifier_manager.get_safe_identifier(table_name, "postgresql")
                
                # 3. 전체 행 수 조회
                cursor.execute(f'SELECT COUNT(*) FROM {safe_schema}.{safe_table_name}')
                total_rows = cursor.fetchone()[0]
                
                # 4. 컬럼별 통계
                table_schema = self.get_table_schema(table_name)
                column_stats = {}
                
                for col in table_schema:
                    col_name = col['name']
                    
                    # 컬럼명 검증
                    self.identifier_manager.validate_column_name(table_name, col_name)
                    safe_col_name = self.identifier_manager.get_safe_identifier(col_name, "postgresql")
                    
                    # NULL 값 비율
                    cursor.execute(f'SELECT COUNT(*) FROM {safe_schema}.{safe_table_name} WHERE {safe_col_name} IS NULL')
                    null_count = cursor.fetchone()[0]
                    null_ratio = (null_count / total_rows * 100) if total_rows > 0 else 0
                    
                    # 고유값 수
                    cursor.execute(f'SELECT COUNT(DISTINCT {safe_col_name}) FROM {safe_schema}.{safe_table_name}')
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
        schema = self.config.get('schema', 'public')
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    most_common_vals,
                    most_common_freqs,
                    histogram_bounds
                FROM pg_stats
                WHERE schemaname = %s AND tablename = %s
                LIMIT 1
            """, (schema, table_name))
            
            # 테이블 크기 정보
            cursor.execute("""
                SELECT 
                    pg_total_relation_size(c.oid) as total_size,
                    pg_relation_size(c.oid) as table_size,
                    pg_total_relation_size(c.oid) - pg_relation_size(c.oid) as index_size,
                    (SELECT count(*) FROM information_schema.columns WHERE table_schema = %s AND table_name = %s) as column_count
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = %s AND c.relname = %s
            """, (schema, table_name, schema, table_name))
            
            result = cursor.fetchone()
            if result:
                total_size, table_size, index_size, column_count = result
                
                # 행 수 추정
                cursor.execute("""
                    SELECT n_tup_ins - n_tup_del as estimated_rows
                    FROM pg_stat_user_tables
                    WHERE schemaname = %s AND relname = %s
                """, (schema, table_name))
                
                row_count_result = cursor.fetchone()
                estimated_rows = row_count_result[0] if row_count_result else 0
                
                return {
                    "rows": estimated_rows or 0,
                    "data_size_mb": round((table_size or 0) / (1024 * 1024), 2),
                    "index_size_mb": round((index_size or 0) / (1024 * 1024), 2),
                    "free_size_mb": 0.0,  # PostgreSQL doesn't have direct equivalent
                    "total_size_mb": round((total_size or 0) / (1024 * 1024), 2)
                }
            return {}
            
    def get_indexes(self, table_name: str = None) -> Dict:
        """인덱스 정보 조회"""
        schema = self.config.get('schema', 'public')
        with self.connection.cursor() as cursor:
            if table_name:
                cursor.execute("""
                    SELECT 
                        i.relname as index_name,
                        a.attname as column_name,
                        ix.indisunique,
                        ix.indisprimary,
                        am.amname as index_type
                    FROM pg_class t
                    JOIN pg_index ix ON t.oid = ix.indrelid
                    JOIN pg_class i ON i.oid = ix.indexrelid
                    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                    JOIN pg_namespace n ON n.oid = t.relnamespace
                    JOIN pg_am am ON i.relam = am.oid
                    WHERE n.nspname = %s AND t.relname = %s
                    ORDER BY i.relname, a.attnum
                """, (schema, table_name))
                
                indexes = cursor.fetchall()
                result = {}
                
                for idx in indexes:
                    index_name = idx[0]
                    if index_name not in result:
                        result[index_name] = {
                            "columns": [],
                            "cardinality": 0,  # PostgreSQL doesn't provide direct cardinality
                            "type": idx[4],
                            "unique": idx[2],
                            "primary": idx[3]
                        }
                    
                    result[index_name]["columns"].append({
                        "name": idx[1],
                        "nullable": True  # 기본값
                    })
                
                return {table_name: result}
            else:
                # 모든 테이블의 인덱스 정보 (간소화된 버전)
                cursor.execute("""
                    SELECT DISTINCT
                        t.relname as table_name,
                        i.relname as index_name
                    FROM pg_class t
                    JOIN pg_index ix ON t.oid = ix.indrelid
                    JOIN pg_class i ON i.oid = ix.indexrelid
                    JOIN pg_namespace n ON n.oid = t.relnamespace
                    WHERE n.nspname = %s
                    ORDER BY t.relname, i.relname
                """, (schema,))
                
                indexes = cursor.fetchall()
                result = {}
                
                for idx in indexes:
                    table_name, index_name = idx[0], idx[1]
                    if table_name not in result:
                        result[table_name] = {}
                    
                    result[table_name][index_name] = {
                        "columns": [],
                        "cardinality": 0,
                        "type": "btree"  # 기본값
                    }
                
                return result
                
    def explain_query(self, query: str) -> Dict:
        """쿼리 실행 계획 분석"""
        with self.connection.cursor() as cursor:
            # EXPLAIN ANALYZE 실행
            cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}")
            explain_result = cursor.fetchone()[0]
            
            return {
                "explain_plan": explain_result,
                "database_type": "postgresql"
            }
            
    def get_db_status(self) -> Dict:
        """데이터베이스 상태 정보"""
        with self.connection.cursor() as cursor:
            # PostgreSQL 버전
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            
            # 활성 연결 수
            cursor.execute("""
                SELECT count(*) as total_connections,
                       count(case when state = 'active' then 1 end) as active_connections,
                       count(case when state = 'idle' then 1 end) as idle_connections
                FROM pg_stat_activity
                WHERE datname = current_database()
            """)
            conn_stats = cursor.fetchone()
            
            # 데이터베이스 통계
            cursor.execute("""
                SELECT 
                    numbackends,
                    xact_commit,
                    xact_rollback,
                    blks_read,
                    blks_hit,
                    tup_returned,
                    tup_fetched,
                    tup_inserted,
                    tup_updated,
                    tup_deleted
                FROM pg_stat_database
                WHERE datname = current_database()
            """)
            db_stats = cursor.fetchone()
            
            # 진행 중인 쿼리들
            cursor.execute("""
                SELECT 
                    pid,
                    usename,
                    application_name,
                    client_addr,
                    state,
                    query_start,
                    left(query, 100) as query_preview
                FROM pg_stat_activity
                WHERE datname = current_database() AND state = 'active'
                ORDER BY query_start
                LIMIT 10
            """)
            active_queries = cursor.fetchall()
            
            return {
                "global_status": {
                    "version": version,
                    "total_connections": conn_stats[0] if conn_stats else 0,
                    "active_connections": conn_stats[1] if conn_stats else 0,
                    "idle_connections": conn_stats[2] if conn_stats else 0,
                    "transactions_committed": db_stats[1] if db_stats else 0,
                    "transactions_rolled_back": db_stats[2] if db_stats else 0,
                    "blocks_read": db_stats[3] if db_stats else 0,
                    "blocks_hit": db_stats[4] if db_stats else 0
                },
                "connection_stats": {
                    "total": conn_stats[0] if conn_stats else 0,
                    "active": conn_stats[1] if conn_stats else 0,
                    "idle": conn_stats[2] if conn_stats else 0
                },
                "active_queries": [
                    {
                        "pid": q[0],
                        "user": q[1],
                        "application": q[2],
                        "client_addr": str(q[3]) if q[3] else None,
                        "state": q[4],
                        "query_start": q[5],
                        "query_preview": q[6]
                    } for q in active_queries
                ]
            } 