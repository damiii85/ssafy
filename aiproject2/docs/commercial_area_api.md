# 전국 상권 현황 API

활용명세: https://infuser.odcloud.kr/oas/docs?namespace=15143727/v1

`.env`의 `COMMERCIAL_AREA_API_KEY`를 사용한다. 인증키는 Authorization 헤더에 전달하며 URL·출력·저장 파일에 포함하지 않는다. 기존 상가 CSV와 ChromaDB는 변경하지 않는다.

```bash
source venv/Scripts/activate
python src/collectors/collect_commercial_areas.py
python -m unittest discover -s tests -v
```

추가 라이브러리는 필요 없다. 결과는 `data/raw/commercial_areas/national_commercial_areas.json`과 `.csv`에 저장한다. JSON에는 원문 응답 행과 출처·수집시각·기준연도를 함께 기록한다.

2026-10-21 실제 API 인증과 조회 성공. 시도별 17개 행, `구분`과 `2023년` 두 컬럼을 확인했다. 대구 행은 247이다. 이 값은 해당 자료의 상권 현황 수치이며, 점포 수·매출·유동인구가 아니다. 데이터 설명의 기준일은 2024-11-20으로, 실시간 동성로 현황을 나타내지 않는다.

이 API에는 개별 상권명·위치·업종별 매출·유동인구가 없어 동성로 입지분석의 핵심 자료로 사용하기 어렵다. 시도별 배경 통계로 보관하며 RAG 2에 자동 색인하지 않는다. 동성로 분석에는 별도로 지역을 식별할 수 있는 상세 통계나 상권분석 보고서가 필요하다.
