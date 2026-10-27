
from pathlib import Path
import os
import argparse

import pandas as pd
import chromadb
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from src.rag.portable_db import chroma_path


# ==========================================
# 1. 프로젝트 경로 및 환경변수
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")

CSV_PATH = (
    BASE_DIR
    / "data"
    / "raw"
    / "dongseongro_stores.csv"
)

COLLECTION_NAME = "store_metadata"

GMS_BASE_URL = os.getenv(
    "GMS_BASE_URL",
    "https://gms.ssafy.io/gmsapi/api.openai.com/v1/"
)

EMBEDDING_MODEL = os.getenv(
    "GMS_EMBEDDING_MODEL",
    "text-embedding-3-small"
)

BATCH_SIZE = 100


# ==========================================
# 2. ChromaDB 및 GMS 연결
# ==========================================

def get_collection():

    api_key = os.getenv("GMS_API_KEY")

    if not api_key:
        raise ValueError(
            ".env 파일에 GMS_API_KEY를 설정해 주세요."
        )

    database_path = chroma_path()
    database_path.mkdir(
        parents=True,
        exist_ok=True
    )

    client = chromadb.PersistentClient(
        path=str(database_path)
    )

    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=api_key,
        base_url=GMS_BASE_URL,
        check_embedding_ctx_length=False,
        request_timeout=45,
        max_retries=1
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "description": "동성로 상가 메타데이터",
            "embedding_model": EMBEDDING_MODEL
        }
    )

    return collection, embeddings


# ==========================================
# 3. 결측값 처리
# ==========================================

def safe_text(value):

    if pd.isna(value):
        return ""

    return str(value).strip()


# ==========================================
# 4. 상가 1건을 검색용 문장으로 변환
# ==========================================

def make_document(row):

    return (
        f"상가명: {safe_text(row['bizesNm'])}\n"
        f"업종 대분류: {safe_text(row['indsLclsNm'])}\n"
        f"업종 중분류: {safe_text(row['indsMclsNm'])}\n"
        f"업종 소분류: {safe_text(row['indsSclsNm'])}\n"
        f"주소: {safe_text(row['rdnmAdr'])}\n"
        f"행정동: {safe_text(row['adongNm'])}\n"
        f"위도: {safe_text(row['lat'])}\n"
        f"경도: {safe_text(row['lon'])}"
    )


# ==========================================
# 5. ChromaDB 메타데이터 구성
# ==========================================

def make_metadata(row):

    metadata = {
        "store_id": safe_text(row["bizesId"]),
        "store_name": safe_text(row["bizesNm"]),
        "category_large": safe_text(row["indsLclsNm"]),
        "category_middle": safe_text(row["indsMclsNm"]),
        "category_small": safe_text(row["indsSclsNm"]),
        "address": safe_text(row["rdnmAdr"]),
        "district": safe_text(row["adongNm"]),
        "source": "소상공인시장진흥공단 상가정보 API"
    }

    if pd.notna(row["lat"]):
        metadata["lat"] = float(row["lat"])

    if pd.notna(row["lon"]):
        metadata["lon"] = float(row["lon"])

    return metadata


# ==========================================
# 6. 상가 데이터 색인
# ==========================================

def index_stores(limit=200):

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"상가 CSV 파일을 찾을 수 없습니다: {CSV_PATH}"
        )

    df = pd.read_csv(
        CSV_PATH,
        encoding="utf-8-sig",
        dtype={"bizesId": "string"}
    )

    required_columns = [
        "bizesId",
        "bizesNm",
        "indsLclsNm",
        "indsMclsNm",
        "indsSclsNm",
        "rdnmAdr",
        "adongNm",
        "lat",
        "lon"
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"CSV에 필요한 컬럼이 없습니다: {missing_columns}"
        )

    # 고유 ID가 없는 데이터 제외
    df = df.dropna(
        subset=["bizesId"]
    )

    df = df[
        df["bizesId"].str.strip() != ""
    ]

    # 상가 ID 기준 중복 제거
    df = df.drop_duplicates(
        subset=["bizesId"]
    )

    # 위도, 경도 숫자 변환
    df["lat"] = pd.to_numeric(
        df["lat"],
        errors="coerce"
    )

    df["lon"] = pd.to_numeric(
        df["lon"],
        errors="coerce"
    )

    # 테스트용 건수 제한
    if limit is not None:
        df = df.head(limit)

    if df.empty:
        print("색인할 상가 데이터가 없습니다.")
        return

    collection, embeddings = get_collection()

    print("\n===== SPOT CHECK RAG 1 =====")
    print(f"색인 대상: {len(df)}건")
    print(f"기존 컬렉션: {collection.count()}건")
    print(f"임베딩 모델: {EMBEDDING_MODEL}")

    for start in range(
        0,
        len(df),
        BATCH_SIZE
    ):

        batch = df.iloc[
            start:start + BATCH_SIZE
        ]

        ids = []
        documents = []
        metadatas = []

        for _, row in batch.iterrows():

            store_id = safe_text(
                row["bizesId"]
            )

            ids.append(store_id)

            documents.append(
                make_document(row)
            )

            metadatas.append(
                make_metadata(row)
            )

        # 기존에 저장된 동일 ID와 동일 내용은
        # 다시 임베딩하지 않음
        existing = collection.get(
            ids=ids,
            include=["documents"]
        )

        existing_documents = dict(
            zip(
                existing["ids"],
                existing["documents"]
            )
        )

        new_ids = []
        new_documents = []
        new_metadatas = []

        for store_id, document, metadata in zip(
            ids,
            documents,
            metadatas
        ):

            if (
                store_id in existing_documents
                and existing_documents[store_id] == document
            ):
                continue

            new_ids.append(store_id)
            new_documents.append(document)
            new_metadatas.append(metadata)

        if not new_ids:
            print(
                f"{min(start + BATCH_SIZE, len(df))}"
                f"/{len(df)}건 확인 완료 "
                "(변경 없음)"
            )
            continue

        print(
            f"임베딩 요청: {len(new_ids)}건"
        )

        vectors = embeddings.embed_documents(
            new_documents
        )

        collection.upsert(
            ids=new_ids,
            documents=new_documents,
            metadatas=new_metadatas,
            embeddings=vectors
        )

        print(
            f"{min(start + BATCH_SIZE, len(df))}"
            f"/{len(df)}건 처리 완료"
        )

    print("\n===== RAG 1 색인 완료 =====")
    print(f"컬렉션: {COLLECTION_NAME}")
    print(f"총 저장 건수: {collection.count()}")
    print(f"저장 경로: {chroma_path()}")


# ==========================================
# 7. 자연어 검색
# ==========================================


def search_stores(query, top_k=5, category=None):
    """상가 벡터 검색. category는 업종 중분류 또는 소분류의 정확한 이름."""
    if top_k < 1:
        raise ValueError("--top-k는 1 이상이어야 합니다.")

    collection, embeddings = get_collection()
    total_count = collection.count()
    if total_count == 0:
        print("색인된 상가가 없습니다.")
        return

    search_options = {
        "query_embeddings": [embeddings.embed_query(query)],
        "n_results": min(top_k, total_count),
        "include": ["documents", "metadatas", "distances"],
    }

    # 지정된 업종이 중분류 또는 소분류에 정확히 일치하는 경우만 검색
    if category:
        category = category.strip()
        search_options["where"] = {
            "$or": [
                {"category_middle": category},
                {"category_small": category},
            ]
        }

    results = collection.query(**search_options)
    print("\n===== RAG 1 검색 결과 =====")
    print(f"질문: {query}")
    print(f"업종 필터: {category or '전체 업종'}\n")

    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    if not metadatas:
        print("검색 결과가 없습니다. CSV의 업종 중분류/소분류 명칭을 확인해 주세요.")
        return

    for i, (metadata, distance) in enumerate(zip(metadatas, distances), start=1):
        print(f"[{i}] {metadata['store_name']}")
        print(f"업종 중분류: {metadata['category_middle']}")
        print(f"업종 소분류: {metadata['category_small']}")
        print(f"주소: {metadata['address']}")
        print(f"벡터 거리: {distance:.4f}")
        print("-" * 40)


# ==========================================
# 8. 실행 옵션
# ==========================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="SPOT CHECK RAG 1 상가 색인 및 검색"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="색인할 상가 수 (0이면 전체)"
    )

    parser.add_argument(
        "--search",
        type=str,
        default=None,
        help="자연어 검색 질문"
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="검색 결과 개수"
    )

    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="업종 중분류 또는 소분류의 정확한 명칭 (미지정 시 전체 업종)",
    )

    args = parser.parse_args()

    if args.search:

        search_stores(
            query=args.search,
            top_k=args.top_k,
            category=args.category
        )

    else:

        limit = (
            None
            if args.limit == 0
            else args.limit
        )

        index_stores(
            limit=limit
        )
