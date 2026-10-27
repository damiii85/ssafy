import unittest
from unittest.mock import patch

from src.services.pdf_evidence import evidence_pages, pdf_answer, UNKNOWN
from src.services.chat_controller import answer_question


class PdfEvidenceTests(unittest.TestCase):
    def test_only_five_regions_and_retired_source_rejected(self):
        from src.services.spot_catalog import load_spots
        from src.collectors.document_collector import canonical_url
        self.assertEqual([s["name"] for s in load_spots()],
                         ['대구 도심 통합상권', '수성못', '삼덕동', '동대구역', '칠곡3지구'])
        for host in ("www.easylaw.go.kr", "law.go.kr"):
            with self.assertRaises(ValueError):
                canonical_url(f"https://{host}/document")

    def test_real_pdf_region_and_page_provenance(self):
        sources = evidence_pages("dongseongro", "동성로 교통")
        self.assertEqual([s["page"] for s in sources], [3, 1, 2, 10])
        self.assertIn("중앙로역", sources[0]["text"])
        for spot, page in (("banwoldang", 5), ("daegu_station", 4), ("samdeok", 7), ("suseongmot", 6), ('dongdaegu', 8), ('chilgok3', 9)):
            self.assertEqual(evidence_pages(spot, "주변 교통")[0]["page"], page)

    def test_verified_excerpt_cites_page(self):
        quote = "중앙로역"
        with patch("src.rag.index_documents.ask_json", return_value={
            "excerpts": [{"source_id": "PDF-3", "quote": quote}], "unknown": False
        }):
            answer = pdf_answer("dongseongro", "교통", llm=object())
        self.assertIn(quote, answer)
        self.assertIn("3쪽", answer)
        self.assertIn("상권보고서.pdf", answer)

    def test_hallucinated_quote_or_source_fails_closed(self):
        for excerpt in ({"source_id": "PDF-3", "quote": "창업 성공률 99.99%"},
                        {"source_id": "LAW", "quote": "중앙로역"}):
            with self.subTest(excerpt=excerpt), patch("src.rag.index_documents.ask_json", return_value={
                "excerpts": [excerpt], "unknown": False
            }):
                answer = pdf_answer("dongseongro", "성공률", llm=object())
                self.assertIn(UNKNOWN, answer)
                self.assertNotIn("99.99", answer)

    def test_partial_and_connection_failure_abstain(self):
        with patch("src.rag.index_documents.ask_json", return_value={"excerpts": [], "unknown": True}):
            self.assertIn(UNKNOWN, pdf_answer("dongseongro", "임대료", llm=object()))
        with patch("src.rag.index_documents.ask_json", side_effect=RuntimeError("offline")):
            self.assertIn(UNKNOWN, pdf_answer("dongseongro", "교통", llm=object()))

    def test_document_question_does_not_require_industry_or_address(self):
        with patch("src.services.chat_controller.local_request", return_value=None), patch("src.services.pdf_evidence.pdf_answer", return_value="중앙로역 / PDF 3쪽") as read:
            answer, report = answer_question("dongseongro", "주변 지하철 알려줘", {}, None, {}, 200)
        self.assertIsNone(report)
        self.assertIn("3쪽", answer)
        read.assert_called_once()
