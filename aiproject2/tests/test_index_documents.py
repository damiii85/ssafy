import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import chromadb

from src.collectors.document_collector import canonical_url, collect_document, extract_html
from src.rag.index_documents import (
    generate_queries, select_candidates, index_document, search_index, split_document,
)


class FakeEmbeddings:
    model = "offline-test-only"

    def __init__(self):
        self.calls = 0

    def embed_documents(self, texts):
        self.calls += len(texts)
        return [[1.0, 0.0, 0.0] for _ in texts]

    def embed_query(self, text):
        return [1.0, 0.0, 0.0]


def llm_reply(value):
    llm = Mock()
    llm.invoke.return_value = SimpleNamespace(content=json.dumps(value))
    return llm


class DocumentTests(unittest.TestCase):
    def test_prompt_responses_validated(self):
        self.assertEqual(generate_queries("창업", llm=llm_reply({"queries": ["의류 창업"]})), ["의류 창업"])
        with self.assertRaises(ValueError):
            generate_queries("창업", llm=llm_reply({"queries": []}))
        candidates = [{"id": 0, "url": "https://example.org/document", "title": "안내"}]
        with self.assertRaises(ValueError):
            select_candidates("창업", candidates, llm=llm_reply({
                "selected": [{"id": 99, "score": 0.9, "reason": "가짜 후보"}]}))
        self.assertEqual(select_candidates("창업", candidates, llm=llm_reply({
            "selected": [{"id": 0, "score": 0.2, "reason": "관련 낮음"}]})), [])

    def test_html_body_and_source_saved(self):
        html = ("<html><head><title>창업 안내</title></head><body><nav>메뉴</nav>"
                "<main>" + "검증된 창업 안내 본문입니다. " * 30 +
                "</main><script>잘못된 내용</script></body></html>").encode()
        title, text = extract_html(html)
        self.assertEqual(title, "창업 안내")
        self.assertNotIn("메뉴", text)
        self.assertNotIn("잘못된 내용", text)
        with tempfile.TemporaryDirectory() as directory, \
             patch("src.collectors.document_collector.check_robots", return_value="허용"), \
             patch("src.collectors.document_collector.request_document", return_value=(
                 "https://example.org/document", html, "text/html")):
            document = collect_document("https://example.org/document", directory)
            saved = json.loads(next(Path(directory).glob("*.json")).read_text(encoding="utf-8"))
            self.assertEqual(saved["text"], text)
            self.assertEqual(saved["url"], document["url"])
            self.assertTrue(saved["collected_at"])

    def test_chunk_validation_and_urls(self):
        with self.assertRaises(ValueError):
            split_document("본문", 100, 100)
        with self.assertRaises(ValueError):
            canonical_url("file:///private")
        self.assertEqual(canonical_url("https://example.org/doc?id=1#top"),
                         "https://example.org/doc?id=1")

    def test_real_chroma_duplicate_update_and_search(self):
        # 실제 영구 DB 대신 메모리 Chroma 컬렉션에 합성 벡터를 넣는다.
        client = chromadb.EphemeralClient()
        collection = client.create_collection("external_test_documents")
        untouched = client.create_collection("store_test_metadata")
        embeddings = FakeEmbeddings()
        document = {"text": "의류 창업 안내와 입지 분석. " * 70,
                    "url": "https://example.org/document", "title": "의류 창업 안내",
                    "source": "테스트 기관", "collected_at": "2026-10-21T00:00:00+00:00",
                    "content_type": "html", "robots_note": "허용", "usage_note": "테스트"}
        document["content_hash"] = hashlib.sha256(document["text"].encode()).hexdigest()
        try:
            first = index_document(document, collection, embeddings, 100, 20)
            self.assertGreater(first["embedded"], 0)
            calls = embeddings.calls
            repeated = index_document(document, collection, embeddings, 100, 20)
            self.assertEqual(repeated["embedded"], 0)
            self.assertEqual(calls, embeddings.calls)
            changed = index_document(document, collection, embeddings, 200, 20)
            self.assertGreater(changed["removed"], 0)
            self.assertEqual(collection.count(), changed["chunks"])
            results = search_index("의류", 2, collection=collection, embeddings=embeddings)
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["metadata"]["url"], document["url"])
            self.assertEqual(untouched.count(), 0)
            # 임베딩 실패 시 기존 버전 청크는 보존된다.
            embeddings.embed_documents = Mock(side_effect=RuntimeError("test"))
            with self.assertRaises(RuntimeError):
                index_document(document, collection, embeddings, 300, 20)
            self.assertEqual(collection.count(), changed["chunks"])
        finally:
            client.delete_collection(collection.name)
            client.delete_collection(untouched.name)


if __name__ == "__main__":
    unittest.main()
