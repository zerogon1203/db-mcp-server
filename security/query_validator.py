"""
SQL 쿼리 보안 검증기
- 읽기 전용 모드 강제
- SQL Injection 방지
- 다중 문장 실행 차단
- 금지 동사 탐지
"""

import re
import logging
from typing import List, Set, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class SecurityLevel(Enum):
    """보안 수준"""
    STRICT = "strict"      # 모든 검증 강제
    NORMAL = "normal"      # 기본 검증
    PERMISSIVE = "permissive"  # 최소 검증

class QueryValidator:
    """SQL 쿼리 보안 검증기"""
    
    # 금지된 SQL 동사들 (대소문자 구분 없음)
    FORBIDDEN_VERBS = {
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE',
        'GRANT', 'REVOKE', 'COPY', 'LOAD', 'CALL', 'MERGE', 'VACUUM', 
        'ANALYZE', 'COMMENT', 'SET', 'SHOW', 'USE', 'PREPARE', 'EXECUTE',
        'DEALLOCATE', 'LOCK', 'UNLOCK', 'REPLACE', 'RENAME', 'FLUSH',
        'RESET', 'KILL', 'SHUTDOWN', 'RESTART', 'RELOAD', 'REPAIR',
        'OPTIMIZE', 'CHECK', 'CHECKSUM', 'BACKUP', 'RESTORE', 'IMPORT',
        'EXPORT', 'DUMP', 'LOAD_FILE', 'INTO', 'OUTFILE', 'INFILE'
    }
    
    # MySQL 특화 위험 키워드
    MYSQL_DANGEROUS_KEYWORDS = {
        'INTO OUTFILE', 'INTO DUMPFILE', 'LOAD_FILE', 'LOAD DATA',
        'LOCAL INFILE', 'SELECT INTO', 'INTO VAR', 'INTO @'
    }
    
    # PostgreSQL 특화 위험 키워드
    POSTGRESQL_DANGEROUS_KEYWORDS = {
        'COPY FROM', 'COPY TO', '\\COPY', '\\lo_import', '\\lo_export'
    }
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.STRICT):
        self.security_level = security_level
        self.read_only_mode = True  # 기본적으로 읽기 전용
        
    def validate_query(self, query: str, db_type: str = "mysql") -> bool:
        """
        SQL 쿼리 보안 검증
        
        Args:
            query: 검증할 SQL 쿼리
            db_type: 데이터베이스 타입 ("mysql", "postgresql")
            
        Returns:
            bool: 검증 통과 여부
            
        Raises:
            SecurityError: 보안 위반 감지 시
        """
        if not query or not query.strip():
            raise SecurityError("빈 쿼리는 허용되지 않습니다.")
            
        # 1. 세미콜론을 통한 다중 문장 실행 차단
        self._validate_single_statement(query)
        
        # 2. 금지 동사 검증 (읽기 전용 검증보다 먼저)
        self._validate_forbidden_verbs(query)
        
        # 3. 기본 읽기 전용 검증
        if self.read_only_mode:
            self._validate_read_only(query)
        
        # 4. DB별 위험 키워드 검증
        if db_type.lower() == "mysql":
            self._validate_mysql_dangerous_keywords(query)
        elif db_type.lower() == "postgresql":
            self._validate_postgresql_dangerous_keywords(query)
            
        # 5. 주석을 통한 우회 시도 차단
        self._validate_comment_bypass(query)
        
        # 6. 문자열 리터럴 내 위험 패턴 검증
        self._validate_string_literals(query)
        
        logger.info(f"쿼리 보안 검증 통과: {query[:50]}...")
        return True
        
    def _validate_read_only(self, query: str) -> None:
        """읽기 전용 모드 검증"""
        # 문자열 리터럴과 주석을 제거한 후 검증
        clean_query = self._strip_strings_and_comments(query)
        
        # SELECT로 시작하는지 확인 (대소문자 구분 없음)
        if not clean_query.strip().upper().startswith('SELECT'):
            raise SecurityError(
                "읽기 전용 모드에서는 SELECT 쿼리만 허용됩니다.",
                error_code="READ_ONLY_VIOLATION"
            )
            
    def _validate_single_statement(self, query: str) -> None:
        """단일 문장 실행 검증"""
        # 문자열 리터럴과 주석을 제거
        clean_query = self._strip_strings_and_comments(query)
        
        # 세미콜론 개수 확인
        semicolon_count = clean_query.count(';')
        if semicolon_count > 1:
            raise SecurityError(
                "다중 문장 실행은 허용되지 않습니다.",
                error_code="MULTIPLE_STATEMENTS"
            )
            
        # 마지막에 세미콜론이 있어야 함 (선택사항)
        if semicolon_count == 1 and not clean_query.strip().endswith(';'):
            raise SecurityError(
                "세미콜론은 문장 끝에만 허용됩니다.",
                error_code="INVALID_SEMICOLON_POSITION"
            )
            
    def _validate_forbidden_verbs(self, query: str) -> None:
        """금지된 SQL 동사 검증"""
        # 문자열 리터럴과 주석을 제거
        clean_query = self._strip_strings_and_comments(query)
        
        # 단어 경계를 고려한 패턴 매칭
        for verb in self.FORBIDDEN_VERBS:
            # 단어 경계를 고려한 정규식
            pattern = r'\b' + re.escape(verb) + r'\b'
            if re.search(pattern, clean_query, re.IGNORECASE):
                raise SecurityError(
                    f"금지된 SQL 동사 '{verb}'가 감지되었습니다.",
                    error_code="FORBIDDEN_VERB",
                    detected_verb=verb
                )
                
    def _validate_mysql_dangerous_keywords(self, query: str) -> None:
        """MySQL 위험 키워드 검증"""
        clean_query = self._strip_strings_and_comments(query)
        
        for keyword in self.MYSQL_DANGEROUS_KEYWORDS:
            if keyword.upper() in clean_query.upper():
                raise SecurityError(
                    f"MySQL 위험 키워드 '{keyword}'가 감지되었습니다.",
                    error_code="MYSQL_DANGEROUS_KEYWORD",
                    detected_keyword=keyword
                )
                
    def _validate_postgresql_dangerous_keywords(self, query: str) -> None:
        """PostgreSQL 위험 키워드 검증"""
        clean_query = self._strip_strings_and_comments(query)
        
        for keyword in self.POSTGRESQL_DANGEROUS_KEYWORDS:
            if keyword.upper() in clean_query.upper():
                raise SecurityError(
                    f"PostgreSQL 위험 키워드 '{keyword}'가 감지되었습니다.",
                    error_code="POSTGRESQL_DANGEROUS_KEYWORD",
                    detected_keyword=keyword
                )
                
    def _validate_comment_bypass(self, query: str) -> None:
        """주석을 통한 우회 시도 검증"""
        # 주석을 제거한 후 다시 검증
        clean_query = self._strip_comments(query)
        
        # 주석 제거 후에도 금지 동사가 있는지 확인 (SELECT가 아닌 경우만)
        if not clean_query.strip().upper().startswith('SELECT'):
            for verb in self.FORBIDDEN_VERBS:
                pattern = r'\b' + re.escape(verb) + r'\b'
                if re.search(pattern, clean_query, re.IGNORECASE):
                    raise SecurityError(
                        f"주석을 통한 우회 시도가 감지되었습니다. 금지된 동사: '{verb}'",
                        error_code="COMMENT_BYPASS_ATTEMPT",
                        detected_verb=verb
                    )
                
    def _validate_string_literals(self, query: str) -> None:
        """문자열 리터럴 내 위험 패턴 검증"""
        # 문자열 리터럴 추출
        string_literals = self._extract_string_literals(query)
        
        for literal in string_literals:
            # 문자열 내에서도 위험한 패턴 검사
            if any(verb.lower() in literal.lower() for verb in self.FORBIDDEN_VERBS):
                # 단, 이는 false positive일 수 있으므로 경고만
                logger.warning(f"문자열 리터럴 내에서 의심스러운 패턴 감지: {literal[:50]}...")
                
    def _strip_strings_and_comments(self, query: str) -> str:
        """문자열 리터럴과 주석을 제거"""
        # 1. 주석 제거
        clean_query = self._strip_comments(query)
        
        # 2. 문자열 리터럴 제거
        clean_query = self._strip_string_literals(clean_query)
        
        return clean_query
        
    def _strip_comments(self, query: str) -> str:
        """SQL 주석 제거"""
        # -- 주석 제거
        lines = query.split('\n')
        clean_lines = []
        
        for line in lines:
            # -- 주석 제거
            if '--' in line:
                line = line[:line.index('--')]
            clean_lines.append(line)
            
        clean_query = '\n'.join(clean_lines)
        
        # /* */ 주석 제거
        clean_query = re.sub(r'/\*.*?\*/', '', clean_query, flags=re.DOTALL)
        
        return clean_query
        
    def _strip_string_literals(self, query: str) -> str:
        """문자열 리터럴 제거"""
        # 작은따옴표 문자열 제거
        clean_query = re.sub(r"'([^'\\]|\\.)*'", "''", query)
        
        # 큰따옴표 문자열 제거 (MySQL/PostgreSQL)
        clean_query = re.sub(r'"([^"\\]|\\.)*"', '""', clean_query)
        
        # 백틱 문자열 제거 (MySQL)
        clean_query = re.sub(r'`([^`\\]|\\.)*`', '``', clean_query)
        
        return clean_query
        
    def _extract_string_literals(self, query: str) -> List[str]:
        """문자열 리터럴 추출"""
        literals = []
        
        # 작은따옴표 문자열
        literals.extend(re.findall(r"'([^'\\]|\\.)*'", query))
        
        # 큰따옴표 문자열
        literals.extend(re.findall(r'"([^"\\]|\\.)*"', query))
        
        # 백틱 문자열
        literals.extend(re.findall(r'`([^`\\]|\\.)*`', query))
        
        return literals
        
    def validate_identifier(self, identifier: str, allowed_identifiers: Optional[Set[str]] = None) -> bool:
        """
        식별자(테이블명, 컬럼명) 검증
        
        Args:
            identifier: 검증할 식별자
            allowed_identifiers: 허용된 식별자 목록 (화이트리스트)
            
        Returns:
            bool: 검증 통과 여부
            
        Raises:
            SecurityError: 보안 위반 감지 시
        """
        if not identifier or not identifier.strip():
            raise SecurityError("빈 식별자는 허용되지 않습니다.")
            
        identifier = identifier.strip()
        
        # 1. 화이트리스트 검증 (우선순위)
        if allowed_identifiers and identifier not in allowed_identifiers:
            raise SecurityError(
                f"허용되지 않은 식별자입니다: {identifier}",
                error_code="IDENTIFIER_NOT_WHITELISTED"
            )
            
        # 2. 기본 식별자 검증
        self._validate_identifier_format(identifier)
        
        # 3. 위험한 패턴 검증
        self._validate_identifier_patterns(identifier)
        
        return True
        
    def _validate_identifier_format(self, identifier: str) -> None:
        """식별자 형식 검증"""
        # SQL 주입 시도 패턴 검증
        dangerous_patterns = [
            r'[;\'"`]',  # 구분자 및 따옴표
            r'--',       # 주석
            r'/\*',      # 블록 주석 시작
            r'\*/',      # 블록 주석 끝
            r'\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b',  # SQL 키워드
            r'\.\.',     # 디렉토리 탐색
            r'%',        # 와일드카드
            r'_',        # 단일 문자 와일드카드
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, identifier, re.IGNORECASE):
                raise SecurityError(
                    f"식별자에 위험한 패턴이 감지되었습니다: {identifier}",
                    error_code="DANGEROUS_IDENTIFIER_PATTERN",
                    detected_pattern=pattern
                )
                
    def _validate_identifier_patterns(self, identifier: str) -> None:
        """식별자 패턴 검증"""
        # 너무 긴 식별자
        if len(identifier) > 128:
            raise SecurityError(
                "식별자가 너무 깁니다 (최대 128자).",
                error_code="IDENTIFIER_TOO_LONG"
            )
            
        # 숫자로 시작하는 식별자 (일부 DB에서 문제)
        if identifier[0].isdigit():
            raise SecurityError(
                "식별자는 숫자로 시작할 수 없습니다.",
                error_code="IDENTIFIER_STARTS_WITH_DIGIT"
            )
            
        # 특수문자만으로 구성된 식별자
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            raise SecurityError(
                "식별자는 영문자, 숫자, 언더스코어만 허용됩니다.",
                error_code="INVALID_IDENTIFIER_CHARACTERS"
            )


class SecurityError(Exception):
    """보안 위반 예외"""
    
    def __init__(self, message: str, error_code: str = None, **kwargs):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = kwargs
        
    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


# 전역 검증기 인스턴스
default_validator = QueryValidator(SecurityLevel.STRICT)
