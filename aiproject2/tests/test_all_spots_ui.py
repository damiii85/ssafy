"""다섯 지역의 즉시 채팅·시각화·지역 전환을 검증한다."""
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from src.services.spot_catalog import load_spots
from src.services.pilot_report import load_spot_data

class AllSpotsUI(unittest.TestCase):
    def test_each_spot_region_overview_and_visuals(self):
        for spot in load_spots():
            with self.subTest(spot=spot['name']):
                app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
                app.button(key='start').click().run()
                app.button(key='select_' + spot['id']).click().run()
                self.assertEqual(len(app.chat_input), 1)
                self.assertFalse(app.text_input)
                self.assertFalse(any(b.label == '위치 수정' for b in app.button))
                with patch('src.services.pilot_report.parse_request', side_effect=AssertionError('offline')):
                    app.button(key='quick_카페').click().run()
                self.assertFalse(app.exception)
                state = app.session_state['spot_sessions'][spot['id']]
                report = state['reports'][-1]
                stores, _ = load_spot_data(spot['id'])
                self.assertEqual(report['type'], 'overview')
                self.assertEqual(report['total_stores'], len(stores))
                self.assertEqual(report['competitor_count'], int((stores.indsSclsNm == '카페').sum()))
                self.assertNotIn('candidates', report)
                self.assertNotIn('competitors', report)
                self.assertTrue(any(m.label.endswith('전체 대비 비중') for m in app.metric))
                self.assertTrue(app.get('vega_lite_chart'))
                app.chat_input[0].set_value('어디에 열면 좋아? 후보 top3 추천해줘').run()
                self.assertFalse(app.exception)
                state = app.session_state['spot_sessions'][spot['id']]
                self.assertEqual(state['reports'][-1]['type'], 'overview')
                self.assertNotIn('입지 탐색 후보', state['messages'][-1]['content'])
                other = next(s for s in load_spots() if s['id'] != spot['id'])
                app.selectbox(key='chat_spot_selector').set_value(other['id']).run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state['active_spot'], other['id'])
                self.assertEqual(app.session_state['ui_stage'], 'chat')
