# 요구서와 검증 환경의 버전 대조

실제 실행: Windows, Python 3.11.9.

기존 `venv`는 보존하고 별도 `.venv`에 요구서 버전을 설치해 검증했다. `requirements.txt` 하나에 요구서 필수 버전과 검증 환경의 전체 의존성을 고정했다. 지정 버전 72개 회귀·pip check·GMS 검색/모델 연동 기록은 `evidence/spec_environment.json`에 보존한다. 브라우저 도구는 기존 개발용 venv에서 실행하며 서비스 서버는 지정 버전 .venv를 사용했다.

| 패키지 | 요구서 | 검증 환경 | 일치 |
|---|---|---|---|
| langchain | 1.3.14 | 1.3.14 | 예 |
| langgraph | 1.2.10 | 1.2.10 | 예 |
| langsmith | 0.10.17 | 0.10.17 | 예 |
| langchain-core | 1.6.0 | 1.6.0 | 예 |
| langchain-openai | 1.4.3 | 1.4.3 | 예 |
| langchain-community | 0.4.2 | 0.4.2 | 예 |
| langchain-chroma | 1.1.0 | 1.1.0 | 예 |
| langchain-text-splitters | 1.1.2 | 1.1.2 | 예 |
| chromadb | 1.5.9 | 1.5.9 | 예 |
| openai | 2.54.0 | 2.54.0 | 예 |
| streamlit | 1.62.0 | 1.62.0 | 예 |
| requests | 2.34.2 | 2.34.2 | 예 |
| python-dotenv | 1.2.3 | 1.2.3 | 예 |
| typing-extensions | 4.16.0 | 4.16.0 | 예 |
