# SPOT CHECK 벡터 DB

- `portable_vectors.json.gz`: 로컬·GMS 검색에 사용하는 사전 계산 벡터와 문서·메타데이터.
- `inventory.json`: 컬렉션별·모델별 구성 정보.
- `runtime/<벡터파일 해시>/chroma_db/`: 앱이 자동 복원한 실제 ChromaDB 파일. 이 폴더는 프로그램 실행 중 생성되며 직접 수정하지 않는다.

컬렉션은 `store_metadata`와 `external_documents`다. 각 백엔드는 메타데이터 1,452개와 PDF 14청크를 검색한다. API 상가 원본 CSV는 DB가 아니라 `data/raw`에 별도로 보관한다.

제출 ZIP에는 복원용 벡터와 구성 정보만 포함하며 실행용 native DB는 자동 복원한다. Windows에서 프로젝트 경로에 한글이 포함되면 Chroma의 경로 호환성 때문에 실행용 native DB만 임시 폴더의 `spotcheck_vectors`에 생성한다. 복원용 파일은 항상 이 `db` 폴더에 있다.
