"""
Visualization-related MCP tools.
"""

def register_visualization_tools(mcp, adapter):
    """시각화 관련 도구들을 MCP 서버에 등록"""
    
    @mcp.tool()
    def generate_schema_mermaid() -> dict:
        """데이터베이스 스키마를 Mermaid ERD 다이어그램으로 생성합니다."""
        try:
            with adapter:
                tables = adapter.get_tables()
                
                # Mermaid ERD 문법 시작
                mermaid_lines = ["erDiagram"]
                
                # 각 테이블의 컬럼 정보 수집
                for table in tables:
                    columns = adapter.get_table_schema(table)
                    
                    # 테이블 정의 추가
                    mermaid_lines.append(f"    {table} {{")
                    
                    for col in columns:
                        field_name = col["name"]
                        field_type = col["type"]
                        is_nullable = col["nullable"]
                        key_type = col["key"]
                        
                        # 키 타입에 따른 표시
                        key_indicator = ""
                        if key_type == "PRI":
                            key_indicator = " PK"
                        elif key_type == "UNI":
                            key_indicator = " UK"
                        elif key_type == "MUL":
                            key_indicator = " FK"
                        
                        # NULL 여부
                        null_indicator = "" if is_nullable else " NOT NULL"
                        
                        mermaid_lines.append(f"        {field_type} {field_name}{key_indicator}{null_indicator}")
                    
                    mermaid_lines.append("    }")
                
                # 외래키 관계 추가
                for table in tables:
                    foreign_keys = adapter.get_foreign_keys(table)
                    for fk in foreign_keys:
                        ref_table = fk["referenced_table"]
                        # Mermaid 관계 문법: 테이블1 ||--o{ 테이블2 : 관계명
                        mermaid_lines.append(f"    {ref_table} ||--o{{ {table} : has")
                
                mermaid_diagram = "\n".join(mermaid_lines)
                
                return {
                    "mermaid_code": mermaid_diagram,
                    "tables_count": len(tables),
                    "description": f"{len(tables)}개 테이블의 ERD 다이어그램이 생성되었습니다."
                }
        except Exception as e:
            raise
    
    @mcp.tool()
    def generate_tables_summary() -> dict:
        """테이블 정보를 깔끔한 마크다운 테이블로 요약합니다."""
        try:
            with adapter:
                tables = adapter.get_tables()
                
                # 마크다운 테이블 헤더
                markdown_lines = [
                    "# 📊 데이터베이스 테이블 요약",
                    "",
                    "| 테이블명 | 행 수 | 컬럼 수 | 데이터 크기 | 인덱스 크기 | 총 크기 | 설명 |",
                    "|---------|-------|---------|-------------|-------------|---------|------|"
                ]
                
                total_rows = 0
                total_data_size = 0
                total_index_size = 0
                tables_data = []
                
                for table in tables:
                    # 테이블 크기 정보
                    size_info = adapter.get_table_size(table)
                    rows = size_info.get("rows", 0)
                    data_size_mb = size_info.get("data_size_mb", 0)
                    index_size_mb = size_info.get("index_size_mb", 0)
                    total_size_mb = size_info.get("total_size_mb", 0)
                    
                    # 컬럼 수
                    schema = adapter.get_table_schema(table)
                    col_count = len(schema)
                    
                    # 행 수 포맷팅
                    rows_formatted = f"{rows:,}" if rows > 0 else "0"
                    
                    # 마크다운 행 추가
                    markdown_lines.append(
                        f"| `{table}` | {rows_formatted} | {col_count} | {data_size_mb}MB | {index_size_mb}MB | {total_size_mb}MB |  |"
                    )
                    
                    # 총계 계산 (MB를 바이트로 변환)
                    total_rows += rows
                    total_data_size += data_size_mb * 1024 * 1024
                    total_index_size += index_size_mb * 1024 * 1024
                    
                    tables_data.append((table, rows, data_size_mb, index_size_mb, total_size_mb))
                
                # 정렬 (행 수 기준 내림차순)
                tables_data.sort(key=lambda x: x[1], reverse=True)
                
                # 요약 통계 추가
                markdown_lines.extend([
                    "",
                    "## 📈 전체 통계",
                    "",
                    f"- **총 테이블 수**: {len(tables)}개",
                    f"- **총 행 수**: {total_rows:,}개",
                    f"- **총 데이터 크기**: {round(total_data_size / (1024 * 1024), 2)}MB",
                    f"- **총 인덱스 크기**: {round(total_index_size / (1024 * 1024), 2)}MB",
                    f"- **총 데이터베이스 크기**: {round((total_data_size + total_index_size) / (1024 * 1024), 2)}MB"
                ])
                
                # 상위 5개 테이블 (행 수 기준)
                if tables_data:
                    markdown_lines.extend([
                        "",
                        "## 🔝 상위 테이블 (행 수 기준)",
                        ""
                    ])
                    
                    for i, table_data in enumerate(tables_data[:5]):
                        table_name, rows, _, _, _ = table_data
                        markdown_lines.append(f"{i+1}. **{table_name}**: {rows:,}개 행")
                
                markdown_summary = "\n".join(markdown_lines)
                
                return {
                    "markdown_summary": markdown_summary,
                    "tables_count": len(tables),
                    "total_rows": total_rows,
                    "total_size_mb": round((total_data_size + total_index_size) / (1024 * 1024), 2)
                }
        except Exception as e:
            raise
    
    @mcp.tool()
    def generate_performance_report() -> dict:
        """성능 분석을 시각적 차트와 함께 리포트로 생성합니다."""
        try:
            with adapter:
                tables = adapter.get_tables()
                
                # 테이블 크기 정보 수집
                size_data = []
                for table in tables:
                    size_info = adapter.get_table_size(table)
                    if size_info:
                        rows = size_info.get("rows", 0)
                        data_size = size_info.get("data_size_mb", 0)
                        index_size = size_info.get("index_size_mb", 0)
                        total_size = data_size + index_size
                        size_data.append((table, rows, data_size, index_size, total_size))
                
                # 크기순 정렬
                size_data.sort(key=lambda x: x[4], reverse=True)
                top_10_tables = size_data[:10]
                
                # 인덱스 효율성 분석
                index_data = []
                all_indexes = adapter.get_indexes()
                for table_name, indexes in all_indexes.items():
                    index_count = len(indexes)
                    cardinalities = []
                    for index_info in indexes.values():
                        cardinality = index_info.get("cardinality", 0)
                        if cardinality > 0:
                            cardinalities.append(cardinality)
                    
                    avg_cardinality = sum(cardinalities) / len(cardinalities) if cardinalities else 0
                    index_data.append((table_name, index_count, avg_cardinality))
                
                # 평균 카디널리티순 정렬
                index_data.sort(key=lambda x: x[2], reverse=True)
                
                # 마크다운 리포트 생성
                report_lines = [
                    "# 📊 데이터베이스 성능 분석 리포트",
                    "",
                    "## 💾 테이블 크기 분석",
                    "",
                    "```",
                    "테이블 크기 (MB) - Top 10",
                    "=" * 50
                ]
                
                # ASCII 차트 생성
                if top_10_tables:
                    max_size = max(row[4] for row in top_10_tables) if top_10_tables else 1
                    for table_name, rows, data_size, index_size, total_size in top_10_tables:
                        bar_length = int((total_size / max_size) * 30) if max_size > 0 else 0
                        bar = "█" * bar_length + "░" * (30 - bar_length)
                        report_lines.append(f"{table_name:<20} |{bar}| {total_size:.2f}MB")
                
                report_lines.extend([
                    "```",
                    "",
                    "## 🔍 인덱스 효율성 분석",
                    "",
                    "| 테이블명 | 인덱스 수 | 평균 카디널리티 | 효율성 |",
                    "|---------|-----------|-----------------|--------|"
                ])
                
                # 인덱스 효율성 테이블
                for table_name, index_count, avg_cardinality in index_data:
                    efficiency = "🟢 좋음" if avg_cardinality > 100 else "🟡 보통" if avg_cardinality > 10 else "🔴 나쁨"
                    report_lines.append(f"| `{table_name}` | {index_count} | {avg_cardinality:.1f} | {efficiency} |")
                
                # Mermaid 차트도 추가
                report_lines.extend([
                    "",
                    "## 📈 성능 트렌드 (Mermaid)",
                    "",
                    "```mermaid",
                    "pie title 테이블별 데이터 분포"
                ])
                
                # 파이 차트 데이터 (상위 5개 테이블만)
                if top_10_tables[:5]:
                    for table_name, _, _, _, total_size in top_10_tables[:5]:
                        report_lines.append(f'    "{table_name}" : {total_size:.1f}')
                
                report_lines.extend([
                    "```",
                    "",
                    "## 💡 권장사항",
                    "",
                    "### 즉시 개선 가능",
                    "- 🔴 효율성이 나쁜 인덱스 검토",
                    "- 📊 큰 테이블의 파티셔닝 고려",
                    "- 🧹 불필요한 인덱스 제거",
                    "",
                    "### 모니터링 필요",
                    "- 📈 데이터 증가 추이 관찰",
                    "- ⚡ 쿼리 성능 지속 확인",
                    "- 💾 디스크 사용량 모니터링"
                ])
                
                performance_report = "\n".join(report_lines)
                
                return {
                    "performance_report": performance_report,
                    "analyzed_tables": len(top_10_tables),
                    "top_table_size_mb": round(top_10_tables[0][4], 2) if top_10_tables else 0
                }
        except Exception as e:
            raise 