# 🗄️ MCP Database Server

> **보안 강화된 다중 데이터베이스 지원 MCP 서버** - Cursor IDE 및 Claude와 연동 가능한 Model Context Protocol 서버

MySQL, PostgreSQL을 지원하는 **엄격한 보안 정책**을 적용한 데이터베이스 분석 및 시각화 도구입니다.

## ✨ 주요 기능

### 🔒 **보안 기능 (NEW!)**
- **읽기 전용 모드 강제** - SELECT 쿼리만 허용
- **SQL Injection 방지** - 다중 문장 실행 및 금지 동사 차단
- **식별자 화이트리스트** - 테이블/컬럼명 검증
- **파라미터 바인딩 강제** - 안전한 쿼리 실행
- **MySQL/PostgreSQL 위험 기능 차단** - INTO OUTFILE, COPY 등

### 🎯 **다중 데이터베이스 지원**
- **MySQL/MariaDB** - 완전 지원 (보안 강화)
- **PostgreSQL** - 완전 지원 (보안 강화)
- **SQLite** - 기본 지원 (준비 중)

### 📊 **시각화 도구**
- **Mermaid ERD 생성** - 데이터베이스 스키마를 Mermaid 다이어그램으로
- **마크다운 테이블 요약** - 테이블 정보를 깔끔한 표로 정리
- **ASCII 성능 차트** - 테이블 크기와 인덱스 효율성을 시각적으로

### 🔍 **분석 기능**
- 스키마 분석 및 조회
- 테이블별 통계 정보
- 성능 병목 지점 탐지
- 인덱스 최적화 제안
- 쿼리 실행 계획 분석

## 📦 설치

```bash
git clone <this-repo-url>
cd db-mcp-server
python -m venv venv
source venv/bin/activate  # 또는 venv\Scripts\activate (Windows)
pip install -r requirements.txt
```

## ⚙️ 설정

### 🔒 보안 설정 (중요!)

**프로덕션 환경에서는 반드시 다음 설정을 적용하세요:**

```env
# 읽기 전용 모드 강제
READ_ONLY=true
STRICT_READONLY=true

# 보안 강화된 데이터베이스 계정 사용
DB_USER=readonly_user
DB_PASSWORD=secure_password
```

### 환경변수 설정

`.env` 파일을 생성하고 데이터베이스 정보를 설정하세요:

```bash
cp .env.example .env
```

### MySQL/MariaDB 설정 (보안 강화)
```env
DB_TYPE=mysql
DB_HOST=localhost
DB_USER=readonly_user  # 읽기 전용 계정 사용
DB_PASSWORD=your_password
DB_NAME=your_database
DB_CHARSET=utf8mb4
DB_PORT=3306
```

### PostgreSQL 설정
```env
DB_TYPE=postgresql
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=your_database
DB_PORT=5432
DB_SCHEMA=public
```

### SQLite 설정
```env
DB_TYPE=sqlite
DB_PATH=./database.sqlite
```

## 🚀 사용법

### Cursor IDE 연동

`MCP Server` 추가 → `Transport: stdio` → `Command: python main.py`

**환경변수 개별 설정:**
```json
{
  "mcpServers": {
    "db-mcp-server": {
      "transport": "stdio",
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/db-mcp-server/main.py"],
      "env": {
        "DB_TYPE": "postgresql",
        "DB_NAME": "your_db_name",
        "DB_HOST": "localhost"
      }
    }
  }
}
```

## 🔒 보안

### 보안 정책

이 서버는 엄격한 보안 정책을 적용합니다:

- **읽기 전용 모드**: SELECT 쿼리만 허용
- **SQL Injection 방지**: 다중 문장 실행 및 금지 동사 차단
- **식별자 검증**: 테이블/컬럼명 화이트리스트 검증
- **파라미터 바인딩**: 모든 사용자 입력은 안전한 방식으로 처리

### 보안 설정

자세한 보안 설정은 [SECURITY.md](SECURITY.md)를 참조하세요.

### 데이터베이스 계정 권한

**중요**: 프로덕션 환경에서는 반드시 읽기 전용 계정을 사용하세요:

```sql
-- MySQL 예시
CREATE USER 'mcp_readonly'@'%' IDENTIFIED BY 'secure_password';
GRANT SELECT ON your_database.* TO 'mcp_readonly'@'%';

-- PostgreSQL 예시
CREATE USER mcp_readonly WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE your_database TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_readonly;
```

## 🛠️ 사용 가능한 도구들

### 📋 **스키마 도구** 
- `get_schema` - 전체 데이터베이스 스키마 조회
- `get_table_stats` - 테이블별 통계 정보
- `get_sample_data` - 샘플 데이터 조회
- `get_column_stats` - 컬럼별 상세 통계

### 🔍 **분석 도구**
- `execute_query` - 안전한 읽기 전용 쿼리 실행
- `explain_query` - 쿼리 실행 계획 분석
- `optimize_query` - 쿼리 최적화 제안
- `get_db_status` - 데이터베이스 상태 정보
- `get_table_size` - 테이블별 크기 정보
- `get_index_usage` - 인덱스 사용 통계
- `analyze_performance` - 성능 병목 지점 분석
- `suggest_indexes` - 인덱스 생성 제안
- `optimize_tables` - 테이블 최적화 제안

### 🎨 **시각화 도구**
- `generate_schema_mermaid` - Mermaid ERD 다이어그램 생성
- `generate_tables_summary` - 마크다운 테이블 요약
- `generate_performance_report` - 성능 분석 리포트 (ASCII 차트 포함)

## 📊 사용 예시

### 스키마 시각화
```
😊 사용자: "데이터베이스 스키마를 ERD로 보여줘"
🤖 AI: generate_schema_mermaid() 실행 → Mermaid 다이어그램 제공
```

### 성능 분석
```
😊 사용자: "성능 문제가 있는지 분석해줘"  
🤖 AI: analyze_performance() → generate_performance_report() 실행
     → ASCII 차트와 함께 상세한 성능 리포트 제공
```

### 테이블 현황 요약
```
😊 사용자: "테이블들 현황을 요약해줘"
🤖 AI: generate_tables_summary() 실행 → 마크다운 테이블 요약 제공
```

## 🏗️ 프로젝트 구조

```
db-mcp-server/
├── main.py                 # MCP 서버 메인 파일
├── .env.example            # 환경변수 예시 파일
├── requirements.txt        # Python 의존성
├── adapters/               # 데이터베이스 어댑터
│   ├── __init__.py        
│   ├── base.py            # 베이스 어댑터 클래스
│   ├── mysql.py           # MySQL/MariaDB 어댑터
│   └── postgresql.py      # PostgreSQL 어댑터
└── tools/                 # MCP 도구 모듈
    ├── __init__.py
    ├── schema_tools.py     # 스키마 관련 도구
    ├── analysis_tools.py   # 분석 관련 도구
    └── visualization_tools.py # 시각화 관련 도구
```

## 🚀 확장성

### 새로운 데이터베이스 추가

1. `adapters/` 폴더에 새 어댑터 클래스 생성
2. `DatabaseAdapter` 베이스 클래스 상속
3. 필요한 메서드들 구현
4. `adapters/__init__.py`의 팩토리 함수에 추가

### 새로운 도구 추가

1. 해당 카테고리의 `tools/` 모듈에 함수 추가
2. `@mcp.tool()` 데코레이터로 등록
3. 어댑터의 메서드를 활용하여 구현

## 📋 요구사항

- **Python 3.8+**
- **데이터베이스**:
  - MySQL/MariaDB 5.7+
  - PostgreSQL 12+
  - SQLite 3.x

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이센스

이 프로젝트는 MIT 라이센스 하에 있습니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.