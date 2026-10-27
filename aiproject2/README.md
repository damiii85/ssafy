# SPOT CHECK

대구 다섯 권역의 상가정보와 PDF를 이용하는 상권 분석 RAG 서비스입니다.

- 실행: Python 3.11을 준비하고 루트의 `실행.bat`을 더블클릭합니다.
- 실제 CSV·PDF·검색 벡터가 포함됩니다. 최초 사용 시 재수집이나 임베딩 API 호출은 필요하지 않습니다.
- 키가 없으면 로컬 검색·CSV/PDF 답변, 본인 `.env`에 GMS_API_KEY가 있으면 GPT-6 Luna를 사용합니다.
- 상세 실행·기능·출처 안내: [output/README.md](output/README.md)
- 산출물: [output](output)

제출 ZIP 생성:

```powershell
.venv\Scripts\python.exe scripts/build_submission.py
```

생성 위치는 `data/processed/submission/SPOT_CHECK_제출용.zip`입니다. 코드·데이터·산출물을 포함하고 실제 키, 가상환경, Git 이력, 캐시, `.archive`는 제외합니다. 로컬 `.env`는 작업용이므로 파일 탐색기로 모든 파일을 그대로 압축하지 말고 위 생성 도구를 사용하세요.
