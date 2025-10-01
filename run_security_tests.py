#!/usr/bin/env python3
"""
보안 테스트 실행 스크립트
MCP Database Server의 보안 기능을 검증합니다.
"""

import sys
import os
import subprocess
import unittest

def run_security_tests():
    """보안 테스트 실행"""
    print("🔒 MCP Database Server 보안 테스트 시작")
    print("=" * 50)
    
    # 테스트 디렉토리를 Python 경로에 추가
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    
    try:
        # 보안 테스트 실행
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromName('tests.test_security')
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        print("\n" + "=" * 50)
        if result.wasSuccessful():
            print("✅ 모든 보안 테스트 통과!")
            print("🛡️  보안 기능이 정상적으로 작동합니다.")
            return 0
        else:
            print("❌ 일부 보안 테스트 실패!")
            print(f"실패한 테스트: {len(result.failures)}")
            print(f"에러 발생: {len(result.errors)}")
            return 1
            
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {e}")
        return 1

def check_security_config():
    """보안 설정 확인"""
    print("\n🔍 보안 설정 확인")
    print("-" * 30)
    
    # 환경 변수 확인
    read_only = os.getenv("READ_ONLY", "true")
    strict_readonly = os.getenv("STRICT_READONLY", "true")
    
    print(f"READ_ONLY: {read_only}")
    print(f"STRICT_READONLY: {strict_readonly}")
    
    if read_only.lower() == "true" and strict_readonly.lower() == "true":
        print("✅ 보안 설정이 올바르게 구성되었습니다.")
        return True
    else:
        print("⚠️  보안 설정을 확인하세요. READ_ONLY=true, STRICT_READONLY=true 권장")
        return False

def main():
    """메인 함수"""
    print("🛡️  MCP Database Server 보안 검증 도구")
    print("=" * 50)
    
    # 1. 보안 설정 확인
    config_ok = check_security_config()
    
    # 2. 보안 테스트 실행
    test_result = run_security_tests()
    
    # 3. 결과 요약
    print("\n" + "=" * 50)
    print("📋 보안 검증 결과 요약")
    print("=" * 50)
    
    if config_ok and test_result == 0:
        print("🎉 모든 보안 검증 통과!")
        print("✅ 서버가 안전하게 구성되었습니다.")
        return 0
    else:
        print("⚠️  보안 검증에서 문제가 발견되었습니다.")
        if not config_ok:
            print("- 보안 설정을 확인하세요")
        if test_result != 0:
            print("- 보안 테스트를 확인하세요")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

