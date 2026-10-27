"""RAG 2: 검색어 생성 → 후보 선별 → 본문 수집 → 별도 컬렉션 색인."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import chromadb
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.collectors.document_collector import collect_document, search_documents
from src.rag.document_prompts import QUERY_PROMPT, SELECTION_PROMPT
from src.rag.settings import load_settings

load_dotenv(BASE_DIR / ".env")
RAW_PATH = BASE_DIR / "data/raw/external_documents"
COLLECTION_NAME = "external_documents"


def gms_options():
    key = os.getenv("GMS_API_KEY")
    if not key:
        raise ValueError(".env에 GMS_API_KEY를 설정해 주세요.")
    return {"api_key": key, "base_url": os.getenv(
        "GMS_BASE_URL", "https://gms.ssafy.io/gmsapi/api.openai.com/v1/")}


def get_llm(timeout=45):
    model = os.getenv("GMS_LLM_MODEL", "gpt-6-luna")
    options = {"use_responses_api": True, "output_version": "responses/v1"} if model.startswith("gpt-6") else {"temperature": 0}
    return ChatOpenAI(model=model, timeout=timeout, max_retries=1,
                      **options, **gms_options())


def get_embeddings():
    return OpenAIEmbeddings(model=os.getenv("GMS_EMBEDDING_MODEL", "text-embedding-3-small"),
                            check_embedding_ctx_length=False, request_timeout=45,
                            max_retries=1, **gms_options())


def ask_json(llm, system, payload):
    reply = llm.invoke([("system", system),
                        ("human", json.dumps(payload, ensure_ascii=False))])
    # Responses API returns text alongside optional reasoning blocks.
    content = reply.content
    if isinstance(content, list):
        content = "".join(block.get("text", "") for block in content
                          if isinstance(block, dict) and block.get("type") in ("text", "output_text"))
    if not isinstance(content, str) or not content.strip():
        raise ValueError("LLM 응답에 확인 가능한 텍스트가 없습니다.")
    content = content.strip()
    if content.startswith("```"):
        content = "\n".join(content.splitlines()[1:-1])
    try:
        result = json.loads(content)
    except (ValueError, TypeError):
        raise ValueError("LLM 응답이 올바른 JSON이 아닙니다. 문서를 임의로 선택하지 않았습니다.") from None
    if not isinstance(result, dict):
        raise ValueError("LLM 응답은 JSON 객체여야 합니다.")
    return result


def generate_queries(question, store_context=None, llm=None):
    result = ask_json(llm or get_llm(), QUERY_PROMPT,
                      {"question": question, "store_context": store_context or {}})
    queries = result.get("queries")
    if not isinstance(queries, list) or not 1 <= len(queries) <= 3:
        raise ValueError("검색어는 1~3개 목록이어야 합니다.")
    if any(not isinstance(q, str) or not 2 <= len(q.strip()) <= 200 for q in queries):
        raise ValueError("유효하지 않은 검색어 응답입니다.")
    return list(dict.fromkeys(q.strip() for q in queries))


def select_candidates(question, candidates, min_score=0.6, llm=None):
    if not 0 <= min_score <= 1:
        raise ValueError("최소 관련성 점수는 0~1이어야 합니다.")
    if not candidates:
        return []
    result = ask_json(llm or get_llm(), SELECTION_PROMPT,
                      {"question": question, "candidates": candidates})
    selections = result.get("selected")
    if not isinstance(selections, list):
        raise ValueError("문서 선별 응답에 selected 목록이 없습니다.")
    by_id = {item["id"]: item for item in candidates}
    selected = {}
    for selection in selections:
        if not isinstance(selection, dict):
            raise ValueError("유효하지 않은 문서 선별 응답입니다.")
        item_id, score = selection.get("id"), selection.get("score")
        if (type(item_id) is not int or item_id not in by_id or
                type(score) not in (int, float) or not 0 <= score <= 1):
            raise ValueError("선별 결과의 후보 ID 또는 관련성 점수가 유효하지 않습니다.")
        reason = selection.get("reason")
        if not isinstance(reason, str):
            raise ValueError("선정 이유가 없습니다.")
        if score >= min_score:
            selected[item_id] = dict(by_id[item_id], relevance=score, reason=reason[:1000])
    return sorted(selected.values(), key=lambda item: item["relevance"], reverse=True)


def split_document(text, chunk_size=None, chunk_overlap=None):
    settings=load_settings() if chunk_size is None or chunk_overlap is None else {}
    chunk_size=settings.get('chunk_size') if chunk_size is None else chunk_size
    chunk_overlap=settings.get('chunk_overlap') if chunk_overlap is None else chunk_overlap
    if chunk_size < 50 or not 0 <= chunk_overlap < chunk_size:
        raise ValueError("chunk-size는 50 이상, overlap은 0 이상 chunk-size 미만이어야 합니다.")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


def get_collection(create=False, db_path=None):
    from src.rag.portable_db import chroma_path
    client = chromadb.PersistentClient(path=str(db_path or chroma_path()))
    if create:
        return client.get_or_create_collection(name=COLLECTION_NAME,
                                               metadata={"description": "외부 창업·상권 문서 본문"})
    try:
        return client.get_collection(name=COLLECTION_NAME)
    except chromadb.errors.NotFoundError:
        raise ValueError("외부 문서가 아직 색인되지 않았습니다. 먼저 --url 또는 --question으로 색인해 주세요.") from None


def index_document(document, collection, embeddings, chunk_size=None, chunk_overlap=None):
    settings=load_settings() if chunk_size is None or chunk_overlap is None else {}
    chunk_size=settings.get('chunk_size') if chunk_size is None else chunk_size
    chunk_overlap=settings.get('chunk_overlap') if chunk_overlap is None else chunk_overlap
    chunks = split_document(document["text"], chunk_size, chunk_overlap)
    if not chunks:
        raise ValueError("색인할 본문이 없습니다.")
    doc_id = hashlib.sha256(document["url"].encode()).hexdigest()
    model = str(getattr(embeddings, "model", "unknown"))
    content_hash = hashlib.sha256(document["text"].encode("utf-8")).hexdigest()
    revision = hashlib.sha256(json.dumps([
        content_hash, chunk_size, chunk_overlap, model, "splitter-v1",
        {field: document[field] for field in ('region_id','source_type','page','reference','corpus_version') if field in document}
    ]).encode()).hexdigest()
    ids = [f"{doc_id}:{revision}:{i}" for i in range(len(chunks))]
    existing = collection.get(where={'$and': [{"document_id": doc_id}, {"embedding_model": model}]}, include=["metadatas"])
    existing_ids = set(existing["ids"])
    pending = [(i, text) for i, text in enumerate(chunks) if ids[i] not in existing_ids]
    for start in range(0, len(pending), 50):
        batch = pending[start:start + 50]
        metadatas = [{
            "document_id": doc_id, "revision": revision, "chunk_index": i,
            "title": document["title"], "url": document["url"],
            "source": document["source"], "collected_at": document["collected_at"],
            "content_hash": content_hash, "usage_note": document["usage_note"],
            "robots_note": document["robots_note"], "content_type": document["content_type"],
            "chunk_size": chunk_size, "chunk_overlap": chunk_overlap, "embedding_model": model,
        } for i, _ in batch]
        for (i, _), metadata in zip(batch, metadatas):
            metadata['chunk_id'] = ids[i]
            for field in ('source_type','region_id','region_name','page','reference','category_level','category_name','corpus_hash','corpus_version'):
                if field in document:
                    metadata[field] = document[field]
        vectors = embeddings.embed_documents([text for _, text in batch])
        collection.upsert(ids=[ids[i] for i, _ in batch],
                          documents=[text for _, text in batch],
                          metadatas=metadatas, embeddings=vectors)
    # 새 청크를 모두 저장한 뒤 이전 버전 청크만 제거한다.
    stale = sorted(existing_ids - set(ids))
    for start in range(0, len(stale), 500):
        collection.delete(ids=stale[start:start + 500])
    return {"chunks": len(chunks), "embedded": len(pending), "removed": len(stale)}


def search_index(query, top_k=5, max_distance=None, collection=None, embeddings=None):
    if not query.strip() or top_k < 1:
        raise ValueError("검색 질문과 1 이상의 top-k가 필요합니다.")
    collection = collection if collection is not None else get_collection()
    count = collection.count()
    if not count:
        return []
    embeddings = embeddings or get_embeddings()
    result = collection.query(query_embeddings=[embeddings.embed_query(query)],
                              n_results=min(top_k, count),
                              include=["documents", "metadatas", "distances"])
    return [{"text": text, "metadata": metadata, "distance": distance}
            for text, metadata, distance in zip(result["documents"][0], result["metadatas"][0],
                                                result["distances"][0])
            if max_distance is None or distance <= max_distance]


def run(args):
    split_document("설정 검증", args.chunk_size, args.chunk_overlap)
    if args.search:
        results = search_index(args.search, args.top_k, args.max_distance)
        if not results:
            print("관련 문서가 없습니다. 자료를 추가하거나 검색 조건을 확인해 주세요.")
        for i, result in enumerate(results, 1):
            meta = result["metadata"]
            print(f"[{i}] {meta['title']} | {meta['source']} | 거리 {result['distance']:.4f}")
            print(f"출처: {meta.get('source',meta['url'])}\n수집일: {meta['collected_at']}")
            print(result["text"] + "\n")
        return
    if args.url:
        candidates = [{"url": url, "title": ""} for url in dict.fromkeys(args.url)]
        print("직접 지정한 문서를 수집합니다. 검색어 생성·후보 선별 단계는 생략합니다.")
    else:
        if not os.getenv("TAVILY_API_KEY"):
            raise ValueError("자동 웹 검색에는 TAVILY_API_KEY가 필요합니다. --url 직접 수집도 가능합니다.")
        context = json.loads(Path(args.store_context).read_text(encoding="utf-8-sig")) if args.store_context else {}
        print("[1/4] 검색어 생성")
        queries = generate_queries(args.question, context)
        print(json.dumps(queries, ensure_ascii=False))
        print("[2/4] 외부 문서 검색 및 관련성 선별")
        all_candidates = search_documents(queries, args.candidates)
        candidates = select_candidates(args.question, all_candidates, args.min_score)
        selected_ids={item['id'] for item in candidates}
        audit = {"question": args.question, "queries": queries, "candidates":all_candidates,
                 "selected": candidates,"rejected":[item for item in all_candidates if item['id'] not in selected_ids]}
        RAW_PATH.mkdir(parents=True, exist_ok=True)
        (RAW_PATH / "last_selection.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
        candidates = candidates[:args.max_documents]
    if not candidates:
        print("관련성 기준을 충족한 문서가 없습니다. 자료가 부족합니다.")
        return
    collection = embeddings = None
    successful = 0
    for item in candidates:
        print(f"[3/4] 본문 수집: {item['url']}")
        try:
            document = collect_document(item["url"], RAW_PATH, title=item["title"],
                                        source=args.source or "", usage_note=args.usage_note)
            if args.collect_only:
                print(f"수집 완료: {len(document['text'])}자 (API 임베딩 생략)")
            else:
                if embeddings is None:
                    embeddings = get_embeddings()
                    collection = get_collection(create=True)
                print("[4/4] 청킹·임베딩·external_documents 저장")
                print(index_document(document, collection, embeddings, args.chunk_size, args.chunk_overlap))
            successful += 1
        except Exception as error:
            # HTTP/SDK 예외의 원문에는 요청 정보가 포함될 수 있어 출력하지 않는다.
            message = str(error) if isinstance(error, ValueError) else type(error).__name__
            print(f"문서 처리 실패: {message}")
    print(f"처리 완료: {successful}/{len(candidates)}개 문서")
    if successful == 0:
        raise ValueError("처리된 문서가 없습니다. URL 접근성과 설정을 확인해 주세요.")


def main():
    settings=load_settings()
    parser = argparse.ArgumentParser(description="SPOT CHECK RAG 2 외부 문서 수집·색인·검색")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--question", help="자동 웹 검색에 사용할 창업 질문")
    mode.add_argument("--url", action="append", help="실제 HTML/PDF 문서 URL. 여러 번 지정 가능")
    mode.add_argument("--search", help="저장된 외부 문서 벡터 검색")
    parser.add_argument("--store-context", help="검색어 생성에 사용할 상가·분석 정보 JSON 파일")
    parser.add_argument("--collect-only", action="store_true", help="본문 수집까지만 실행")
    parser.add_argument("--chunk-size", type=int, default=settings['chunk_size'])
    parser.add_argument("--chunk-overlap", type=int, default=settings['chunk_overlap'])
    parser.add_argument("--top-k", type=int, default=settings['top_k_documents'])
    parser.add_argument("--max-distance", type=float, help="벡터 거리 상한. 데이터별 검증 후 설정")
    parser.add_argument("--candidates", type=int, default=5)
    parser.add_argument("--max-documents", type=int, default=3)
    parser.add_argument("--min-score", type=float, default=0.6)
    parser.add_argument("--source", help="직접 지정 문서의 발행기관. 미지정 시 원문 호스트 기록")
    parser.add_argument("--usage-note", default="미확인: 원문 이용조건 확인 필요")
    args = parser.parse_args()
    if args.max_documents < 1:
        parser.error("--max-documents는 1 이상이어야 합니다.")
    try:
        run(args)
    except Exception as error:
        print("오류: " + (str(error) if isinstance(error, ValueError) else type(error).__name__), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
