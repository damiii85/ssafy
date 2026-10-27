import unittest
from streamlit.testing.v1 import AppTest


class AnswerCardsUITests(unittest.TestCase):
    def test_used_sources_are_deduplicated_but_all_numbered_evidence_survives(self):
        message = {'content':'확인된 설명 [근거 1] [근거 2]', 'citations':[
            {'number':1,'title':'통계','source_type':'pdf_statistics',
             'source':'data/reports/상권보고서.pdf','page':2,
             'reference':'{"stores_footfall_sales_residents":"2026-07"}','scope':'수성못 PDF 경계'},
            {'number':2,'title':'지역 설명','source_type':'pdf_chapter',
             'source':'상권보고서.pdf','page':6,'reference':'2026-06','scope':'수성못 PDF 경계'}]}
        app=AppTest.from_string('from src.ui.assistant_message import assistant_message\n'
                                f'assistant_message({message!r}, "evidence")').run()
        self.assertFalse(app.exception)
        captions=[c.value for c in app.caption]
        self.assertEqual(sum('상권보고서 · PDF' in c for c in captions),1)
        self.assertTrue(any('[근거 1] [근거 2]' in c for c in captions))
        self.assertTrue(any('PDF 페이지: 2쪽' in c for c in captions))
        self.assertTrue(any('PDF 페이지: 6쪽' in c for c in captions))
        self.assertTrue(any('2026-07' in c for c in captions))
        self.assertFalse(any('pdf_statistics' in c or 'stores_footfall_sales_residents' in c for c in captions))
        self.assertEqual(app.expander[0].label,'상세 근거 및 분석 기준')
        self.assertFalse(app.expander[0].proto.expanded)

    def test_unknown_source_is_not_attributed_to_a_public_agency(self):
        from src.ui.assistant_message import _source_label
        self.assertEqual(_source_label({'source':'https://example.org/report','title':'자료'}),
                         'example.org · 자료')

    def test_pdf_metric_uses_verified_value_and_keeps_original_answer(self):
        app=self.render({'type':'pdf_metrics','rows':[
            {'지역':'동성로','지표':'유동인구','값':110640,'단위':'명/일'}]})
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value,'110,640명/일')
        self.assertIn('일평균 유동인구',app.metric[0].label)
        self.assertTrue(any('원본 답변과 한계 설명' in m.value for m in app.markdown))

    def render(self, visual):
        script = '''
import streamlit as st
from src.ui.assistant_message import assistant_message
assistant_message({'role':'assistant', 'content':'원본 답변과 한계 설명', 'visual':%r}, 'test')
''' % visual
        return AppTest.from_string(script,default_timeout=20).run()

    def test_empty_scope_has_zero_counts_without_fabricated_share(self):
        app = self.render({'type':'overview','total_stores':0,'competitor_count':0})
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric], ['0곳','0곳','데이터 없음'])
        self.assertFalse(app.get('vega_lite_chart'))
        self.assertTrue(any('원본 답변과 한계 설명' in m.value for m in app.markdown))

    def test_zero_selected_still_renders_chart(self):
        app = self.render({'type':'overview','total_stores':12,'competitor_count':0})
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric], ['12곳','0곳','0.0%'])
        self.assertEqual(len(app.get('vega_lite_chart')),1)

    def test_missing_and_inconsistent_counts_are_not_invented(self):
        for visual in ({'type':'overview'}, {'type':'overview','total_stores':3,'competitor_count':4}):
            app = self.render(visual)
            self.assertFalse(app.exception)
            self.assertEqual([m.value for m in app.metric], ['데이터 없음']*3)
            self.assertFalse(app.get('vega_lite_chart'))

    def test_missing_pdf_fields_and_no_document_link(self):
        for visual in ({'type':'pdf_metrics'}, {'type':'pdf_metrics','rows':[{'지표':'유동인구','값':None}]}):
            app=self.render(visual)
            self.assertFalse(app.exception)
            self.assertFalse(app.get('download_button'))
            self.assertTrue(any('데이터 없음' in c.value for c in app.caption))
