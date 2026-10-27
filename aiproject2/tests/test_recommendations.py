"""구체적인 입지 추천이 다시 노출되지 않는지 검증한다."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from src.services.chat_controller import answer_question
from src.services.pilot_report import load_spot_data, parse_request
from src.services.naver_map import map_html
from src.services.region_analytics import public_report, distribution_rows, pdf_visuals
from src.services.pdf_evidence import pdf_answer

class RegionalInformationPolicyTests(unittest.TestCase):
    def test_recommendation_is_always_aggregate_even_with_old_state(self):
        stores, meta = load_spot_data('dongseongro')
        state = {'request': {'intent':'spot_recommendation', 'address':'중앙대로 412-21', 'categories':[{'level':'small','name':'카페'}]}}
        for question in ('카페 어디가 좋을까?', '중앙대로 412-21에 카페 추천해줘', '후보 top3 알려줘'):
            answer, report = answer_question('dongseongro', question, state, stores, meta, 200)
            self.assertEqual(report['type'], 'overview')
            for key in ('address','latitude','longitude','candidates','competitors'):
                self.assertNotIn(key, report)
            # 직접 입력한 주소는 집계 기준으로만 사용하며 점포 추천은 만들지 않는다.
            if '412-21' in question or state.get('address_location'):
                self.assertIn('직선 반경', report['scope_description'])
            else:
                self.assertNotIn('412-21', answer)
            self.assertNotIn('입지 탐색 후보', answer)

    def test_model_cannot_restore_address_recommendation(self):
        stores, _ = load_spot_data('dongseongro')
        model = Mock()
        model.invoke.return_value = SimpleNamespace(content=json.dumps({'address':'생성한 주소', 'intent':'spot_recommendation', 'categories':[{'level':'small','name':'카페'}]}))
        result = parse_request('위치 추천', stores, llm=model)
        self.assertEqual(result['address'], '')
        self.assertEqual(result['intent'], 'spot_overview')

    def test_map_escapes_untrusted_labels(self):
        html = map_html('test-client-id', 35.87, 128.595, [{'lat':35.87,'lon':128.595,'label':'</script><script>alert(1)</script>'}])
        self.assertNotIn('</script><script>alert', html)
        self.assertIn('ncpKeyId=test-client-id', html)
        self.assertIn('textContent', html)
        regional = map_html('test',35.87,128.595,show_markers=False)
        self.assertIn('"show_markers": false', regional)

    def test_distribution_keeps_total_and_old_reports_are_filtered(self):
        rows = distribution_rows({str(i):i+1 for i in range(10)})
        self.assertEqual(sum(r['점포 수'] for r in rows),55)
        self.assertEqual(rows[-1]['업종'],'그 외 업종')
        self.assertIsNone(public_report({'type':'recommendation','candidates':[{'address':'secret'}]}))
        self.assertNotIn('competitors',public_report({'type':'overview','competitors':[{'주소':'secret'}]}))

    def test_pdf_graphs_only_use_the_answered_values(self):
        answer = pdf_answer('banwoldang','반월당 유동인구')
        visual = pdf_visuals('banwoldang','반월당 유동인구',answer)
        self.assertEqual(visual['rows'],[{'지역':'반월당','지표':'유동인구','값':18012,'단위':'명/일'}])
        self.assertIsNone(pdf_visuals('banwoldang','임대료',pdf_answer('banwoldang','임대료')))
