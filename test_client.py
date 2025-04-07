import json
import sys

def main():
    try:
        # 요청 메시지 작성
        request = {
            "type": "tool_call",
            "tool": "get_schema",
            "args": {}
        }
        
        # 요청 전송
        print(json.dumps(request), flush=True)
        
        # 응답 대기
        response = json.loads(sys.stdin.readline())
        result = response["result"]
        
        # 결과 출력
        print("\n데이터베이스 스키마 정보:")
        for table_name, table_info in result["schema"].items():
            print(f"\n테이블: {table_name}")
            print("컬럼:")
            for column in table_info["columns"]:
                print(f"  - {column['Field']} ({column['Type']})")
            
            if "foreign_keys" in table_info:
                print("외래키:")
                for fk in table_info["foreign_keys"]:
                    print(f"  - {fk['column']} -> {fk['references']['table']}.{fk['references']['column']}")
    
    except Exception as e:
        print(f"오류 발생: {e}", file=sys.stderr)

if __name__ == "__main__":
    main() 