"""
MCP Database Server - 다중 데이터베이스 지원
"""

from mcp.server.fastmcp import FastMCP
import os
import logging
import sys
from dotenv import load_dotenv

# 모듈 임포트
from adapters import get_adapter
from tools.schema_tools import register_schema_tools
from tools.analysis_tools import register_analysis_tools
from tools.visualization_tools import register_visualization_tools

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# .env 로드
load_dotenv()

def get_db_config():
    """환경변수에서 데이터베이스 설정을 가져옵니다."""
    db_type = os.getenv("DB_TYPE", "mysql").lower()
    
    if db_type == "mysql":
        return {
            "host": os.getenv("DB_HOST"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "db": os.getenv("DB_NAME"),
            "charset": os.getenv("DB_CHARSET", "utf8mb4"),
            "port": int(os.getenv("DB_PORT", "3306"))
        }
    elif db_type == "postgresql":
        return {
            "host": os.getenv("DB_HOST"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "db": os.getenv("DB_NAME"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "schema": os.getenv("DB_SCHEMA", "public")
        }
    elif db_type == "sqlite":
        return {
            "database": os.getenv("DB_PATH", "./database.sqlite")
        }
    else:
        raise ValueError(f"지원하지 않는 데이터베이스 타입: {db_type}")

def create_mcp_server():
    """MCP 서버를 생성하고 설정합니다."""
    # 데이터베이스 설정
    db_type = os.getenv("DB_TYPE", "mysql").lower()
    db_config = get_db_config()
    
    logger.info(f"MCP 서버 시작 - DB 타입: {db_type}")
    logger.info(f"데이터베이스 설정: {db_config}")
    
    # MCP 서버 생성 (stdio 모드)
    mcp = FastMCP(
        name="DatabaseMCPServer",
        mode="stdio", 
        version="2.0.0",
        description=f"{db_type.upper()} 데이터베이스 분석 및 시각화 도구"
    )
    
    # 어댑터 생성
    try:
        adapter = get_adapter(db_type, db_config)
        logger.info(f"{db_type.upper()} 어댑터 생성 완료")
    except Exception as e:
        logger.error(f"어댑터 생성 실패: {str(e)}")
        raise
    
    # MCP 도구들 등록
    register_schema_tools(mcp, adapter)
    register_analysis_tools(mcp, adapter)
    register_visualization_tools(mcp, adapter)
    
    logger.info("모든 MCP 도구가 등록되었습니다")
    
    return mcp

if __name__ == "__main__":
    try:
        logger.info("MCP 서버 실행")
        mcp = create_mcp_server()
        mcp.run()
    except Exception as e:
        logger.error(f"MCP 서버 실행 중 오류 발생: {str(e)}")
        raise