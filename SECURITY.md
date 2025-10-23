# 🔒 MCP Database Server 보안 가이드

## 개요

MCP Database Server는 엄격한 보안 정책을 통해 SQL Injection 공격과 읽기 전용 모드 우회를 방지합니다. 이 문서는 보안 기능과 설정 방법을 설명합니다.

## 🛡️ 보안 기능

### 1. 읽기 전용 모드 강제

- **기본값**: `READ_ONLY=true`
- **기능**: SELECT 쿼리만 허용
- **차단**: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE 등 모든 쓰기 작업

### 2. SQL Injection 방지

#### 다중 문장 실행 차단
```sql
-- ❌ 차단됨
SELECT * FROM users; DROP TABLE users;

-- ✅ 허용됨
SELECT * FROM users;
```

#### 금지된 SQL 동사 차단
다음 동사들이 문자열/주석 외부에서 발견되면 차단됩니다:

**DDL (Data Definition Language)**
- `CREATE`, `DROP`, `ALTER`, `TRUNCATE`, `RENAME`

**DML (Data Manipulation Language)**
- `INSERT`, `UPDATE`, `DELETE`, `REPLACE`, `MERGE`

**권한 관리**
- `GRANT`, `REVOKE`

**기타 위험 기능**
- `CALL`, `PREPARE`, `EXECUTE`, `DEALLOCATE`
- `SET`, `SHOW`, `USE`
- `VACUUM`, `ANALYZE`, `COMMENT`
- `COPY`, `LOAD`, `INTO`

### 3. 데이터베이스별 위험 기능 차단

#### MySQL 위험 키워드
- `INTO OUTFILE`, `INTO DUMPFILE`
- `LOAD_FILE()`, `LOAD DATA INFILE`
- `LOAD DATA LOCAL INFILE`
- `SELECT INTO @var`

#### PostgreSQL 위험 키워드
- `COPY FROM`, `COPY TO`
- `\COPY`, `\lo_import`, `\lo_export`

### 4. 식별자 화이트리스트 검증

- **테이블명**: 데이터베이스에서 실제 존재하는 테이블만 허용
- **컬럼명**: 해당 테이블에 실제 존재하는 컬럼만 허용
- **위험 패턴 차단**: 세미콜론, 따옴표, 주석, SQL 키워드 등

### 5. 파라미터 바인딩 강제

모든 사용자 입력은 파라미터 바인딩을 통해 전달되어야 합니다:

```python
# ❌ 위험한 방식
query = f"SELECT * FROM {table_name} WHERE id = {user_id}"

# ✅ 안전한 방식
query = "SELECT * FROM %s WHERE id = %s"
params = (table_name, user_id)
```

## ⚙️ 보안 설정

### 환경 변수

```bash
# 읽기 전용 모드 (기본값: true)
READ_ONLY=true

# 엄격한 읽기 전용 모드 (기본값: true)
STRICT_READONLY=true

# 데이터베이스 타입
DB_TYPE=mysql  # 또는 postgresql

# 데이터베이스 연결 정보
DB_HOST=localhost
DB_USER=readonly_user
DB_PASSWORD=secure_password
DB_NAME=your_database
DB_PORT=3306
```

### MySQL 보안 설정

```python
# 자동으로 적용되는 보안 설정
{
    'multi_statements': False,      # 다중 문장 비활성화
    'local_infile': False,          # 로컬 파일 로드 비활성화
    'ssl_disabled': False,          # SSL 강제
    'connect_timeout': 10,          # 연결 타임아웃
    'read_timeout': 30,             # 읽기 타임아웃
    'write_timeout': 30             # 쓰기 타임아웃
}
```

### PostgreSQL 보안 설정

```python
# 자동으로 적용되는 보안 설정
{
    'sslmode': 'prefer',            # SSL 우선 사용
    'connect_timeout': 10,          # 연결 타임아웃
    'application_name': 'mcp-db-server-secure'
}
```

## 🔐 데이터베이스 계정 권한

### 최소 권한 원칙

읽기 전용 계정은 다음 권한만 가져야 합니다:

#### MySQL
```sql
-- 읽기 전용 계정 생성
CREATE USER 'mcp_readonly'@'%' IDENTIFIED BY 'secure_password';

-- 최소 권한 부여
GRANT SELECT ON your_database.* TO 'mcp_readonly'@'%';

-- 위험한 권한 제거
REVOKE INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, INDEX, 
       TRIGGER, REFERENCES, RELOAD, SHUTDOWN, PROCESS, 
       FILE, GRANT OPTION ON *.* FROM 'mcp_readonly'@'%';

FLUSH PRIVILEGES;
```

#### PostgreSQL
```sql
-- 읽기 전용 계정 생성
CREATE USER mcp_readonly WITH PASSWORD 'secure_password';

-- 최소 권한 부여
GRANT CONNECT ON DATABASE your_database TO mcp_readonly;
GRANT USAGE ON SCHEMA public TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_readonly;

-- 기본 권한 설정
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT SELECT ON TABLES TO mcp_readonly;
```

## 🚨 보안 에러 코드

| 에러 코드                      | 설명                        | 해결 방법                 |
| ------------------------------ | --------------------------- | ------------------------- |
| `READ_ONLY_VIOLATION`          | 읽기 전용 모드 위반         | SELECT 쿼리만 사용        |
| `MULTIPLE_STATEMENTS`          | 다중 문장 실행 시도         | 단일 문장으로 분리        |
| `FORBIDDEN_VERB`               | 금지된 SQL 동사 사용        | 허용된 쿼리만 사용        |
| `MYSQL_DANGEROUS_KEYWORD`      | MySQL 위험 키워드 사용      | 안전한 쿼리로 변경        |
| `POSTGRESQL_DANGEROUS_KEYWORD` | PostgreSQL 위험 키워드 사용 | 안전한 쿼리로 변경        |
| `COMMENT_BYPASS_ATTEMPT`       | 주석을 통한 우회 시도       | 주석 제거 후 재시도       |
| `IDENTIFIER_NOT_WHITELISTED`   | 허용되지 않은 식별자        | 유효한 테이블/컬럼명 사용 |
| `DANGEROUS_IDENTIFIER_PATTERN` | 위험한 식별자 패턴          | 안전한 식별자 사용        |

## 📋 보안 체크리스트

### 배포 전 확인사항

- [ ] `READ_ONLY=true` 설정 확인
- [ ] `STRICT_READONLY=true` 설정 확인
- [ ] 데이터베이스 계정이 읽기 전용 권한만 가지는지 확인
- [ ] MySQL의 경우 `multi_statements=False` 설정 확인
- [ ] MySQL의 경우 `local_infile=False` 설정 확인
- [ ] SSL 연결 사용 확인
- [ ] 방화벽에서 필요한 포트만 개방 확인

### 정기 보안 점검

- [ ] 데이터베이스 계정 권한 재검토
- [ ] 보안 로그 모니터링
- [ ] 의심스러운 쿼리 패턴 분석
- [ ] 데이터베이스 서버 보안 패치 적용
- [ ] 백업 및 복구 절차 테스트

## 🔍 보안 모니터링

### 로그 확인

보안 위반 시도는 다음과 같이 로깅됩니다:

```
2024-01-15 10:30:45 - security.query_validator - WARNING - 
쿼리 보안 검증 실패: [FORBIDDEN_VERB] 금지된 SQL 동사 'DROP'가 감지되었습니다.
```

### 모니터링 지표

- 보안 위반 시도 횟수
- 차단된 쿼리 유형별 통계
- 의심스러운 IP 주소
- 비정상적인 쿼리 패턴

## 🆘 보안 사고 대응

### 1. 즉시 조치

1. **연결 차단**: 의심스러운 IP 주소 차단
2. **로그 분석**: 공격 패턴 및 영향 범위 파악
3. **데이터베이스 점검**: 데이터 무결성 확인

### 2. 장기 조치

1. **보안 강화**: 추가 보안 정책 적용
2. **모니터링 개선**: 실시간 알림 시스템 구축
3. **교육**: 팀원 보안 인식 교육

## 📞 지원

보안 관련 문의사항이나 취약점 발견 시:

1. **긴급 상황**: 즉시 시스템 관리자에게 연락
2. **일반 문의**: 프로젝트 이슈 트래커 활용
3. **보안 취약점**: 비공개 채널을 통한 신고

---

**⚠️ 주의사항**: 이 문서의 보안 설정은 기본적인 보호 수준을 제공합니다. 프로덕션 환경에서는 추가적인 보안 조치가 필요할 수 있습니다.

