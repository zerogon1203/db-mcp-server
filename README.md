# MCP Stdio Server (MySQL/MariaDB)
 
 이 프로젝트는 Cursor IDE와 연동 가능한 Model Context Protocol (MCP) Stdio 서버입니다.
 MySQL 또는 MariaDB 데이터베이스의 테이블 구조와 관계를 반환합니다.
 
## ✅ 기능
 
- MCP 공식 Python SDK 기반
- `stdio` 모드로 Cursor IDE 연동
- `.env` 파일 기반 DB 설정
- 테이블 목록, 컬럼, 외래키 관계 반환
- 데이터 조회 및 분석 기능
- 쿼리 실행 및 최적화 기능
- 데이터베이스 모니터링 기능
- 성능 분석 및 최적화 제안
 
## 📦 설치
 
```bash
git clone <this-repo-url>
cd db-mcp-server
python -m venv venv
source venv/bin/activate  # 또는 venv\Scripts\activate (Windows)
pip install -r requirements.txt
```
 
## ⚙️ .env 설정
 
루트에 `.env` 파일을 아래와 같이 작성하세요:
 
```env
# Database connection settings for MCP Python server
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=your_db
DB_CHARSET=utf8mb4
```
 
## 🚀 실행
 
Cursor IDE에서 `MCP Server` 추가 > `Transport: stdio` > `Command: python main.py`
 
## 📡 지원 메서드
 
### 스키마 조회
- `mysql.get_schema`: 모든 테이블 구조 + 외래키 반환

### 데이터 조회 및 분석
- `mysql.get_table_stats`: 테이블별 통계 정보 (행 수, NULL 값 비율, 고유값 수)
- `mysql.get_sample_data`: 테이블의 샘플 데이터 조회
- `mysql.get_column_stats`: 특정 컬럼의 상세 통계 정보

### 쿼리 실행 및 최적화
- `mysql.execute_query`: 안전한 읽기 전용 쿼리 실행
- `mysql.explain_query`: 쿼리 실행 계획 분석
- `mysql.optimize_query`: 쿼리 최적화 제안

### 데이터베이스 모니터링
- `mysql.get_db_status`: 데이터베이스 상태 정보 (연결 수, 쿼리 통계 등)
- `mysql.get_table_size`: 테이블별 크기 정보
- `mysql.get_index_usage`: 인덱스 사용 통계

### 성능 분석
- `mysql.analyze_performance`: 성능 병목 지점 분석
- `mysql.suggest_indexes`: 인덱스 생성 제안
- `mysql.optimize_tables`: 테이블 최적화 제안
 
## 📝 예시 결과
 
### 스키마 조회
```json
{
  "schema": {
    "users": {
      "columns": [...],
      "foreign_keys": [...]
    }
  }
}
```

### 테이블 통계
```json
{
  "table_name": "users",
  "total_rows": 1000,
  "column_stats": {
    "id": {
      "total_rows": 1000,
      "null_count": 0,
      "null_ratio": 0.0,
      "unique_values": 1000
    }
  }
}
```

### 쿼리 실행 계획
```json
{
  "explain_plan": [...],
  "handler_stats": {...},
  "suggestions": [
    {
      "type": "index",
      "message": "정렬 작업이 발생하고 있습니다. ORDER BY 절에 사용된 컬럼에 대한 인덱스 추가를 고려하세요."
    }
  ]
}
```

### 성능 분석
```json
{
  "slow_queries": 5,
  "bottlenecks": [
    {
      "type": "large_table",
      "table": "orders",
      "rows": 1500000,
      "message": "테이블 'orders'이(가) 1,500,000개의 행을 가지고 있습니다. 파티셔닝을 고려하세요."
    }
  ],
  "recommendations": [...]
}
```
 
## ✅ 요구사항
 
- Python 3.8+
- MySQL/MariaDB