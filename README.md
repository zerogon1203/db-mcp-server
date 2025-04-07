

# MCP Stdio Server (MySQL/MariaDB)
 
 이 프로젝트는 Cursor IDE와 연동 가능한 Model Context Protocol (MCP) Stdio 서버입니다.
 MySQL 또는 MariaDB 데이터베이스의 테이블 구조와 관계를 반환합니다.
 
## ✅ 기능
 
- MCP 공식 Python SDK 기반
- `stdio` 모드로 Cursor IDE 연동
- `.env` 파일 기반 DB 설정
- 테이블 목록, 컬럼, 외래키 관계 반환
 
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
 
- `mysql.get_schema`: 모든 테이블 구조 + 외래키 반환
 
## 📝 예시 결과
 
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
 
## ✅ 요구사항
 
- Python 3.8+
- MySQL/MariaDB