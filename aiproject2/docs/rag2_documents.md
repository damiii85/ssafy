# PDF 근거 답변

활성 자료는 `data/reports/상권보고서.pdf`(10쪽)다. 2쪽의 7개 지역 통계표는 각 지역의 4개 지표 행 두 개를 검증해 읽으며, 지역명 수성못(두산동)·동대구역(신천4동)의 표기를 처리한다. 본문 페이지와 기준·정의 1·10쪽을 함께 출처로 표시한다.

`src/services/pdf_evidence.py`의 검증된 원문 해석을 재사용한다. 사용자의 명시적 GMS 전송 승인 후 활성 PDF 지역 설명·지역별 통계 14청크를 `external_documents`에 실제 색인했다. 기본 LLM 모드는 검색된 원문 발췌만 생성하고 연속 문자열 일치를 검사한다. 도심 통합상권의 PDF 통계는 동성로·대구역·반월당별로 표시하며 합산하지 않는다. API 상가 ID 중복 제거 합집합과 구별한다.

거리 요청은 `src/services/distance_scope.py`에서 API 상가 좌표에만 적용한다. PDF 유동인구·매출을 반경 비율로 환산하지 않으며 요청 범위의 미확인 값은 알 수 없다고 안내한다.

외부 문서 CLI `src/rag/index_documents.py`는 별도 수집 도구로 보존한다. 현재 채팅은 LangGraph에서 API 메타데이터 컬렉션과 활성 PDF 컬렉션을 통합 검색한다. 지역·모델·자료 버전·청크 설정 필터가 없는 구형 자료와 다른 보관 보고서를 무조건 섞지 않는다. 검색된 모든 문서가 아닌 실제 사용한 근거만 번호로 표시한다.

지역별 자료·거리 처리: `docs/daegu_pilot.md`.
검증: `python scripts/run_tests.py`, 실서비스: `python scripts/verify_rag.py --live-llm`.
설계/요구사항/결과는 `docs/rag_pipeline.md`, `docs/requirements_audit.md`, `docs/rag_test_results.md` 참조.
