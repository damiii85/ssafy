"""실제 로컬 PDF/CSV와 사용자 질문의 대응을 검증한다. 외부 모델 호출 금지."""
import unittest
from unittest.mock import patch

from src.services.pdf_evidence import pdf_answer, report_data
from src.services.chat_controller import answer_question, local_request
from src.services.pilot_report import load_spot_data


class AnswerQualityTests(unittest.TestCase):
    def test_all_pdf_metrics_are_read_without_external_model(self):
        expected = {"동성로": 110640, "반월당": 18012, "대구역": 55851,
                    "삼덕동": 13144, "수성못": 121031}
        with patch('src.rag.index_documents.get_llm', side_effect=AssertionError('No external PDF transfer')) as external:
            for region, number in expected.items():
                with self.subTest(region=region):
                    self.assertEqual(report_data(region)['metrics']['유동인구'], number)
                    text = pdf_answer('banwoldang', f'{region}의 유동인구는 몇 명이야?')
                    self.assertIn(f'{number:,}명/일', text)
                    self.assertIn('2쪽', text)
                    self.assertIn('2026.07', text)
                    self.assertNotIn('비활성화', text)
            external.assert_not_called()

    def test_split_page_table_does_not_confuse_residents_and_footfall(self):
        text = pdf_answer('dongseongro', '동성로 주거인구와 유동인구 알려줘')
        self.assertIn('721명', text)
        self.assertIn('110,640명/일', text)

    def test_pdf_transport_and_unknown_partial_or_current(self):
        self.assertIn('반월당역', pdf_answer('banwoldang', '지하철 알려줘'))
        self.assertIn('2호선', pdf_answer('samdeok', '주변 지하철'))
        text = pdf_answer('banwoldang', '유동인구와 임대료')
        self.assertIn('18,012', text)
        self.assertIn('알 수 없습니다', text)
        self.assertIn('알 수 없습니다', pdf_answer('banwoldang', '카페 예상 매출'))
        self.assertIn('현재 실측값은 알 수 없습니다', pdf_answer('banwoldang', '오늘 유동인구'))

    def test_industry_first_turn_uses_full_csv_and_pdf_without_address(self):
        for spot in ('daegu_downtown', 'dongdaegu', 'chilgok3', 'samdeok', 'suseongmot'):
            stores, meta = load_spot_data(spot)
            state = {}
            with self.subTest(spot=spot), patch('src.services.pilot_report.parse_request', side_effect=AssertionError('Basic category must work offline')):
                text, report = answer_question(spot, '카페를 하고 싶어요', state, stores, meta, 200)
                self.assertEqual(report['type'], 'overview')
                self.assertEqual(report['competitor_count'], int((stores.indsSclsNm == '카페').sum()))
                self.assertEqual(report['total_stores'], len(stores))
                self.assertIn('커피·차', text)
                self.assertIn('PDF', text)
                self.assertIn(meta['source'], text)
                self.assertNotIn('정해 둔 주소를', text)
                self.assertNotIn('비활성화', text)

    def test_followup_metric_does_not_repeat_industry_or_request_address(self):
        stores, meta = load_spot_data('banwoldang')
        state = {}
        answer_question('banwoldang', '카페 창업', state, stores, meta, 200)
        text, report = answer_question('banwoldang', '유동인구는 몇명이야?', state, stores, meta, 200)
        self.assertIsNone(report)
        self.assertIn('18,012', text)
        self.assertNotIn('카페 창업을 생각', text)
        text, report = answer_question('banwoldang', '어디가 좋을까?', state, stores, meta, 200)
        self.assertEqual(report['type'], 'overview')
        self.assertNotIn('candidates', report)

    def test_explicit_other_region_does_not_use_selected_region_csv(self):
        stores, meta = load_spot_data('dongseongro')
        other, _ = load_spot_data('banwoldang')
        text, report = answer_question('dongseongro', '반월당 카페 현황', {}, stores, meta, 200)
        self.assertEqual(report['spot'], '반월당')
        self.assertEqual(report['total_stores'], len(other))
        self.assertIn('18,012', text)

    def test_clothing_retail_does_not_include_rental_or_repair(self):
        stores, _ = load_spot_data('dongseongro')
        request = local_request('옷가게 하고 싶어', stores, {})
        self.assertTrue(request['categories'])
        self.assertTrue(all(c['name'].endswith('소매업') for c in request['categories']))

    def test_mixed_startup_question_keeps_industry_and_document_evidence(self):
        stores, meta = load_spot_data('banwoldang')
        text, report = answer_question('banwoldang', '카페 창업하고 싶은데 반월당 유동인구와 지하철도 알려줘', {}, stores, meta, 200)
        self.assertEqual(report['type'], 'overview')
        self.assertIn('545', text)
        self.assertIn('18,012', text)
        self.assertIn('1·2호선', text)
        self.assertIn(meta['source'], text)
        self.assertIn('상권보고서.pdf', text)

    def test_industry_comparison_uses_each_regions_csv(self):
        stores, meta = load_spot_data('dongseongro')
        text, report = answer_question('dongseongro', '동성로와 반월당 카페 현황 비교', {}, stores, meta, 200)
        self.assertIsNone(report)
        for spot in ('dongseongro', 'banwoldang'):
            frame, _ = load_spot_data(spot)
            self.assertIn(f"{int((frame.indsSclsNm == '카페').sum()):,}곳", text)
        self.assertIn('합산', text)
