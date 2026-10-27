import math
import unittest
from pathlib import Path

import pandas as pd

from src.services.distance_scope import requested_radius
from src.services.chat_controller import answer_question
from src.services.pdf_evidence import PDF_PATH, report_data, pdf_answer
from src.services.pilot_report import load_spot_data
from src.services.spot_catalog import get_spot, load_spots


class DistanceAndRevisionTests(unittest.TestCase):
    def setUp(self):
        self.meta = {'center_lat': 35.828, 'center_lon': 128.617, 'radius_m': 1000,
                     'source': 'https://example.org/source', 'collected_at_utc': '2026-10-22',
                     'anchor': '검증 기준점', 'spot_name': '수성못'}
        self.frame = pd.DataFrame([
            {'bizesId': str(i), 'bizesNm': '비공개점포', 'rdnmAdr': '비공개주소',
             'lat': self.meta['center_lat'] + math.degrees(distance / 6371000),
             'lon': self.meta['center_lon'], 'indsLclsNm': '음식', 'indsMclsNm': '음료',
             'indsSclsNm': '편의점' if i == 1 else '카페'}
            for i, distance in enumerate([50, 99.5, 100, 100.5, 150, 250])])

    def ask(self, question, state=None):
        return answer_question('suseongmot', question, {} if state is None else state,
                               self.frame, self.meta, 200)

    def test_radius_units_and_invalid_values(self):
        for text in ('100m', '100 미터', '0.1km', '100미터 이내', '100M 안'):
            self.assertEqual(requested_radius(text), 100)
        self.assertEqual(requested_radius('1,000미터'), 1000)
        for text in ('0m', '-100m', '100m와 200m'):
            with self.assertRaises(ValueError):
                requested_radius(text)

    def test_100m_is_not_200m_and_boundary_is_inclusive(self):
        _, small = self.ask('100미터 이내 카페')
        _, large = self.ask('200m 이내 카페')
        self.assertEqual((small['radius_m'], small['total_stores'], small['competitor_count']), (100, 3, 2))
        self.assertEqual((large['radius_m'], large['total_stores'], large['competitor_count']), (200, 5, 4))
        self.assertIn('100m', small['scope_description'])
        self.assertNotIn('competitors', small)

    def test_followup_keeps_category_and_requested_radius_until_reset(self):
        state = {}
        self.ask('카페를 하고 싶어', state)
        _, report = self.ask('100미터 이내 유사 업계는?', state)
        self.assertEqual(report['competitor_count'], 2)
        _, next_report = self.ask('동종 업계 현황', state)
        self.assertEqual(next_report['radius_m'], 100)
        _, full = self.ask('전체 범위 현황', state)
        self.assertEqual(full['total_stores'], 6)

    def test_no_fabricated_coverage_location_or_radius_pdf_metrics(self):
        answer, report = self.ask('카페 2km 이내')
        self.assertIsNone(report)
        self.assertIn('알 수 없습니다', answer)
        answer, report = self.ask('내 위치 100m 카페')
        self.assertIsNone(report)
        self.assertIn('현재 위치', answer)
        answer, report = self.ask('100m 내 유동인구')
        self.assertIsNone(report)
        self.assertIn('알 수 없습니다', answer)

    def test_new_report_values_and_downtown_stats_are_not_summed(self):
        self.assertEqual(len(load_spots()), 5)
        self.assertEqual(PDF_PATH.name, '상권보고서.pdf')
        self.assertFalse((PDF_PATH.parent / '대구_5개상권_교통_랜드마크_확장보고서.pdf').exists())
        self.assertEqual(report_data('동대구역')['metrics']['유동인구'], 43284)
        self.assertEqual(report_data('칠곡3지구')['metrics']['유동인구'], 50357)
        self.assertEqual(report_data('대구 도심 통합상권')['metrics'], {})
        text = pdf_answer('daegu_downtown', '유동인구')
        for value in ('110,640', '55,851', '18,012', '합산하지'):
            self.assertIn(value, text)
        self.assertNotIn('184,503', text)

    def test_union_deduplicates_ids_and_new_regions_are_real(self):
        combined, meta = load_spot_data('daegu_downtown')
        source_ids = set()
        for component in get_spot('daegu_downtown')['components']:
            frame, _ = load_spot_data(component['id'])
            source_ids.update(frame.bizesId)
        self.assertEqual(set(combined.bizesId), source_ids)
        self.assertEqual(combined.bizesId.nunique(), len(combined))
        self.assertGreater(meta['duplicates_removed'], 0)
        for spot_id in ('dongdaegu', 'chilgok3'):
            frame, metadata = load_spot_data(spot_id)
            self.assertEqual(len(frame), metadata['api_total'])

    def test_subregion_100m_then_followup_50m_uses_same_reference(self):
        frame, meta = load_spot_data('daegu_downtown')
        state = {}
        _, first = answer_question('daegu_downtown', '반월당 100m 카페', state, frame, meta, 200)
        _, second = answer_question('daegu_downtown', '50m 유사 업계', state, frame, meta, 200)
        self.assertEqual(first['region_id'], 'banwoldang')
        self.assertEqual(second['region_id'], 'banwoldang')
        self.assertEqual((first['radius_m'], second['radius_m']), (100, 50))
        self.assertLessEqual(second['competitor_count'], first['competitor_count'])

    def test_ui_cards_use_requested_radius_not_full_collection(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
        app.button(key='start').click().run()
        app.button(key='select_daegu_downtown').click().run()
        app.button(key='quick_카페').click().run()
        app.chat_input[0].set_value('100미터 이내 유사 업계').run()
        self.assertFalse(app.exception)
        report = app.session_state['spot_sessions']['daegu_downtown']['reports'][-1]
        self.assertEqual(report['radius_m'], 100)
        self.assertEqual(report['total_stores'], 271)
        self.assertEqual(report['competitor_count'], 19)
        metric = next(m for m in app.metric if m.label == 'API 집계 범위 상가')
        self.assertEqual(metric.value, '271곳')
