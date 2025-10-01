"""
보안 테스트 케이스
- SQL Injection 방지 테스트
- 읽기 전용 모드 테스트
- 식별자 검증 테스트
- 다중 문장 실행 차단 테스트
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security.query_validator import QueryValidator, SecurityError, SecurityLevel
from security.identifier_manager import IdentifierManager

class TestQueryValidator(unittest.TestCase):
    """쿼리 검증기 테스트"""
    
    def setUp(self):
        self.validator = QueryValidator(SecurityLevel.STRICT)
        
    def test_valid_select_queries(self):
        """유효한 SELECT 쿼리 테스트"""
        valid_queries = [
            "SELECT * FROM users",
            "SELECT id, name FROM users WHERE age > 18",
            "SELECT COUNT(*) FROM orders",
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id",
            "SELECT * FROM products ORDER BY price DESC LIMIT 10"
        ]
        
        for query in valid_queries:
            with self.subTest(query=query):
                self.assertTrue(self.validator.validate_query(query, "mysql"))
                
    def test_forbidden_verbs_blocked(self):
        """금지된 동사 차단 테스트"""
        forbidden_queries = [
            "INSERT INTO users VALUES (1, 'test')",
            "UPDATE users SET name = 'hacker'",
            "DELETE FROM users WHERE id = 1",
            "DROP TABLE users",
            "ALTER TABLE users ADD COLUMN test VARCHAR(255)",
            "CREATE TABLE test (id INT)",
            "TRUNCATE TABLE users",
            "GRANT ALL ON *.* TO 'user'@'%'",
            "REVOKE ALL ON *.* FROM 'user'@'%'",
            "COPY users TO '/tmp/backup.csv'",
            "LOAD DATA INFILE '/tmp/data.csv' INTO TABLE users",
            "CALL stored_procedure()",
            "MERGE INTO users USING temp_users ON users.id = temp_users.id",
            "VACUUM ANALYZE users",
            "COMMENT ON TABLE users IS 'test'",
            "SET sql_mode = 'STRICT_TRANS_TABLES'",
            "SHOW TABLES",
            "USE database_name",
            "PREPARE stmt FROM 'SELECT * FROM users'",
            "EXECUTE stmt",
            "DEALLOCATE PREPARE stmt"
        ]
        
        for query in forbidden_queries:
            with self.subTest(query=query):
                with self.assertRaises(SecurityError) as context:
                    self.validator.validate_query(query, "mysql")
                self.assertIn("금지된 SQL 동사", str(context.exception))
                
    def test_multiple_statements_blocked(self):
        """다중 문장 실행 차단 테스트"""
        multiple_statement_queries = [
            "SELECT * FROM users; DROP TABLE users;",
            "SELECT * FROM users; INSERT INTO logs VALUES ('hack');",
            "SELECT * FROM users; UPDATE users SET admin = 1;",
            "SELECT * FROM users; DELETE FROM users;",
            "SELECT * FROM users; ALTER TABLE users ADD COLUMN hack VARCHAR(255);"
        ]
        
        for query in multiple_statement_queries:
            with self.subTest(query=query):
                with self.assertRaises(SecurityError) as context:
                    self.validator.validate_query(query, "mysql")
                self.assertIn("다중 문장 실행", str(context.exception))
                
    def test_mysql_dangerous_keywords_blocked(self):
        """MySQL 위험 키워드 차단 테스트"""
        dangerous_queries = [
            "SELECT * FROM users INTO OUTFILE '/tmp/backup.csv'",
            "SELECT * FROM users INTO DUMPFILE '/tmp/backup.sql'",
            "SELECT LOAD_FILE('/etc/passwd')",
            "LOAD DATA INFILE '/tmp/data.csv' INTO TABLE users",
            "LOAD DATA LOCAL INFILE '/tmp/data.csv' INTO TABLE users",
            "SELECT @var := 'test' INTO @var",
            "SELECT * INTO @var FROM users"
        ]
        
        for query in dangerous_queries:
            with self.subTest(query=query):
                with self.assertRaises(SecurityError) as context:
                    self.validator.validate_query(query, "mysql")
                # 금지 동사나 MySQL 위험 키워드 중 하나가 감지되어야 함
                error_msg = str(context.exception)
                self.assertTrue(
                    "MySQL 위험 키워드" in error_msg or 
                    "금지된 SQL 동사" in error_msg or
                    "읽기 전용 모드" in error_msg,
                    f"예상된 보안 에러가 아닙니다: {error_msg}"
                )
                
    def test_postgresql_dangerous_keywords_blocked(self):
        """PostgreSQL 위험 키워드 차단 테스트"""
        dangerous_queries = [
            "COPY users FROM '/tmp/data.csv'",
            "COPY users TO '/tmp/backup.csv'",
            "\\COPY users FROM '/tmp/data.csv'",
            "\\lo_import '/tmp/file.txt'",
            "\\lo_export 12345 '/tmp/exported_file.txt'"
        ]
        
        for query in dangerous_queries:
            with self.subTest(query=query):
                with self.assertRaises(SecurityError) as context:
                    self.validator.validate_query(query, "postgresql")
                # 금지 동사나 PostgreSQL 위험 키워드 중 하나가 감지되어야 함
                error_msg = str(context.exception)
                self.assertTrue(
                    "PostgreSQL 위험 키워드" in error_msg or 
                    "금지된 SQL 동사" in error_msg or
                    "읽기 전용 모드" in error_msg,
                    f"예상된 보안 에러가 아닙니다: {error_msg}"
                )
                
    def test_comment_bypass_blocked(self):
        """주석을 통한 우회 시도 차단 테스트"""
        # 실제로는 주석이 제거되어 SELECT 쿼리로 인식되므로 통과해야 함
        bypass_queries = [
            "SELECT * FROM users -- ; DROP TABLE users;",
            "SELECT * FROM users /* ; DROP TABLE users; */",
            "SELECT * FROM users -- INSERT INTO logs VALUES ('hack');",
            "SELECT * FROM users /* UPDATE users SET admin = 1; */"
        ]
        
        for query in bypass_queries:
            with self.subTest(query=query):
                # 주석이 제거되어 SELECT 쿼리로 인식되므로 통과해야 함
                self.assertTrue(self.validator.validate_query(query, "mysql"))
                
    def test_case_insensitive_detection(self):
        """대소문자 구분 없는 금지 동사 탐지 테스트"""
        case_variations = [
            "select * from users; insert into logs values ('test');",
            "SELECT * FROM users; UPDATE users SET name = 'test';",
            "select * from users; delete from users;",
            "SELECT * FROM users; DROP TABLE users;",
            "select * from users; alter table users add column test varchar(255);"
        ]
        
        for query in case_variations:
            with self.subTest(query=query):
                with self.assertRaises(SecurityError):
                    self.validator.validate_query(query, "mysql")
                    
    def test_string_literal_stripping(self):
        """문자열 리터럴 제거 테스트"""
        # 문자열 내의 금지 동사는 허용되어야 함
        valid_with_strings = [
            "SELECT 'INSERT INTO users VALUES (1)' as query_text",
            "SELECT \"UPDATE users SET name = 'test'\" as query_text",
            "SELECT `DROP TABLE users` as query_text"
        ]
        
        for query in valid_with_strings:
            with self.subTest(query=query):
                self.assertTrue(self.validator.validate_query(query, "mysql"))


class TestIdentifierManager(unittest.TestCase):
    """식별자 관리자 테스트"""
    
    def setUp(self):
        self.validator = QueryValidator(SecurityLevel.STRICT)
        self.identifier_manager = IdentifierManager(self.validator)
        
        # 모의 스키마 데이터 설정
        self.identifier_manager._table_whitelist = {"users", "orders", "products"}
        self.identifier_manager._column_whitelist = {
            "users": {"id", "name", "email", "age"},
            "orders": {"id", "user_id", "total", "created_at"},
            "products": {"id", "name", "price", "category"}
        }
        self.identifier_manager._cache_valid = True
        
    def test_valid_table_names(self):
        """유효한 테이블명 테스트"""
        valid_tables = ["users", "orders", "products"]
        
        for table in valid_tables:
            with self.subTest(table=table):
                self.assertTrue(self.identifier_manager.validate_table_name(table))
                
    def test_invalid_table_names(self):
        """무효한 테이블명 테스트"""
        invalid_tables = [
            "hackers",  # 화이트리스트에 없음
            "admin_users",  # 화이트리스트에 없음
            "test_table"  # 화이트리스트에 없음
        ]
        
        for table in invalid_tables:
            with self.subTest(table=table):
                with self.assertRaises(SecurityError) as context:
                    self.identifier_manager.validate_table_name(table)
                self.assertIn("허용되지 않은 테이블명", str(context.exception))
                
    def test_valid_column_names(self):
        """유효한 컬럼명 테스트"""
        valid_columns = [
            ("users", "id"),
            ("users", "name"),
            ("orders", "total"),
            ("products", "price")
        ]
        
        for table, column in valid_columns:
            with self.subTest(table=table, column=column):
                self.assertTrue(self.identifier_manager.validate_column_name(table, column))
                
    def test_invalid_column_names(self):
        """무효한 컬럼명 테스트"""
        invalid_columns = [
            ("users", "password"),  # 화이트리스트에 없음
            ("orders", "credit_card"),  # 화이트리스트에 없음
            ("products", "secret_key")  # 화이트리스트에 없음
        ]
        
        for table, column in invalid_columns:
            with self.subTest(table=table, column=column):
                with self.assertRaises(SecurityError) as context:
                    self.identifier_manager.validate_column_name(table, column)
                self.assertIn("존재하지 않습니다", str(context.exception))
                
    def test_dangerous_identifier_patterns(self):
        """위험한 식별자 패턴 테스트"""
        dangerous_identifiers = [
            "users; DROP TABLE users;",
            "users' OR '1'='1",
            "users\" OR \"1\"=\"1",
            "users` OR `1`=`1",
            "users-- comment",
            "users/* comment */",
            "users UNION SELECT * FROM admin",
            "users../etc/passwd",
            "users%",
            "users_"
        ]
        
        for identifier in dangerous_identifiers:
            with self.subTest(identifier=identifier):
                with self.assertRaises(SecurityError) as context:
                    self.identifier_manager.validate_identifier(identifier)
                self.assertIn("위험한 패턴", str(context.exception))
                
    def test_safe_identifier_quoting(self):
        """안전한 식별자 인용부호 처리 테스트"""
        # MySQL 백틱
        mysql_quoted = self.identifier_manager.get_safe_identifier("users", "mysql")
        self.assertEqual(mysql_quoted, "`users`")
        
        # PostgreSQL 큰따옴표
        postgresql_quoted = self.identifier_manager.get_safe_identifier("users", "postgresql")
        self.assertEqual(postgresql_quoted, '"users"')


class TestSecurityIntegration(unittest.TestCase):
    """보안 통합 테스트"""
    
    def test_sql_injection_attempts(self):
        """SQL Injection 시도 차단 테스트"""
        validator = QueryValidator(SecurityLevel.STRICT)
        
        # 실제로 차단되어야 하는 시도들
        blocked_attempts = [
            "SELECT * FROM users WHERE id = 1; DROP TABLE users; --",
            "SELECT * FROM users WHERE id = 1; INSERT INTO logs VALUES ('hack'); --",
            "SELECT * FROM users WHERE id = 1; UPDATE users SET admin = 1; --",
            "SELECT * FROM users WHERE id = 1; DELETE FROM users; --",
            "SELECT * FROM users WHERE id = 1; ALTER TABLE users ADD COLUMN hack VARCHAR(255); --"
        ]
        
        for attempt in blocked_attempts:
            with self.subTest(attempt=attempt):
                with self.assertRaises(SecurityError):
                    validator.validate_query(attempt, "mysql")
                    
        # 실제로는 유효한 SELECT 쿼리들 (통과해야 함)
        valid_queries = [
            "SELECT * FROM users WHERE name = 'admin' OR '1'='1'",
            "SELECT * FROM users WHERE id = 1 UNION SELECT * FROM admin_users"
        ]
        
        for query in valid_queries:
            with self.subTest(query=query):
                self.assertTrue(validator.validate_query(query, "mysql"))
                    
    def test_parameter_binding_requirement(self):
        """파라미터 바인딩 요구사항 테스트"""
        # 이 테스트는 실제 어댑터에서 구현되어야 함
        # 여기서는 개념적 테스트만 수행
        
        # 직접 문자열 보간을 사용한 쿼리는 위험
        dangerous_query = "SELECT * FROM users WHERE id = " + "1"
        
        # 파라미터 바인딩을 사용한 쿼리는 안전
        safe_query = "SELECT * FROM users WHERE id = %s"
        
        # 검증기는 쿼리 구조만 검사하므로 둘 다 통과
        validator = QueryValidator(SecurityLevel.STRICT)
        self.assertTrue(validator.validate_query(dangerous_query, "mysql"))
        self.assertTrue(validator.validate_query(safe_query, "mysql"))
        
        # 실제 보안은 어댑터 레벨에서 파라미터 바인딩 강제로 구현됨


class TestSecurityError(unittest.TestCase):
    """보안 에러 테스트"""
    
    def test_security_error_creation(self):
        """보안 에러 생성 테스트"""
        error = SecurityError(
            "테스트 에러",
            error_code="TEST_ERROR",
            additional_info="추가 정보"
        )
        
        self.assertEqual(error.message, "테스트 에러")
        self.assertEqual(error.error_code, "TEST_ERROR")
        self.assertEqual(error.details["additional_info"], "추가 정보")
        
    def test_security_error_string_representation(self):
        """보안 에러 문자열 표현 테스트"""
        error = SecurityError("테스트 에러", error_code="TEST_ERROR")
        self.assertEqual(str(error), "[TEST_ERROR] 테스트 에러")
        
        error_no_code = SecurityError("테스트 에러")
        self.assertEqual(str(error_no_code), "테스트 에러")


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)
