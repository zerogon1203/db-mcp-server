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

if __name__ == "__main__":
    try:
        logger.info("MCP 서버 실행")
        mcp.run()
    except Exception as e:
        logger.error(f"MCP 서버 실행 중 오류 발생: {str(e)}")
        raise