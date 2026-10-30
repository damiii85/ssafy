import json
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .models import CommentTaskResult
from .services.crawling import parse_stock_snapshot
from .services.sentiment import analyze_comments, analyze_comments_safely, parse_analysis, unavailable_analysis


class AnalysisValidationTests(SimpleTestCase):
    def response(self, labels):
        return json.dumps({'summary': '주가에 대한 기대와 우려가 함께 나타납니다.',
            'comments': [{'index': i, 'label': label, 'reason': '댓글의 태도를 분류했습니다.'}
                         for i, label in enumerate(labels)]})

    def test_actual_text_mapping_and_ratio_rounding(self):
        comments = ['좋아요 ❤️', '불안하네요', '발표 언제인가요']
        data = json.loads(self.response(['positive','negative','neutral']))
        data['comments'].reverse()
        result = parse_analysis(json.dumps(data), comments)
        self.assertEqual([x['text'] for x in result['comments']], comments)
        self.assertEqual(result['counts'], {'positive':1,'negative':1,'neutral':1})
        self.assertAlmostEqual(sum(result['ratios'].values()), 100)
        self.assertEqual(result['basis'], 'raw_comments')

    def test_reject_incomplete_duplicate_and_invalid_records(self):
        for change in ['count','duplicate','bool','label','reason']:
            with self.subTest(change=change):
                data = json.loads(self.response(['positive','negative']))
                if change == 'count': data['comments'].pop()
                if change == 'duplicate': data['comments'][1]['index'] = 0
                if change == 'bool': data['comments'][0]['index'] = True
                if change == 'label': data['comments'][0]['label'] = 'bullish'
                if change == 'reason': data['comments'][0]['reason'] = ''
                with self.assertRaises(ValueError):
                    parse_analysis(json.dumps(data), ['a','b'])

    def test_empty_comments_do_not_call_api(self):
        with patch('crawling.services.sentiment.run_llm') as llm:
            self.assertEqual(analyze_comments([], '삼성전자')['status'], 'unavailable')
            llm.assert_not_called()

    def test_failure_is_not_fake_neutral_sentiment(self):
        with patch('crawling.services.sentiment.run_llm', return_value='invalid'):
            result = analyze_comments_safely(['좋아요'], '삼성전자')
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['counts'], {})

    def test_original_emoji_reaches_api_once(self):
        with patch('crawling.services.sentiment.run_llm', return_value=self.response(['positive'])) as llm:
            result = analyze_comments(['좋아요 ❤️'], '삼성전자')
        llm.assert_called_once()
        self.assertIn('❤️', llm.call_args.args[0])
        self.assertEqual(result['counts']['positive'], 1)

    def test_signed_daily_price_direction(self):
        for rate, expected in [('+2.40','up'),('-3.01','down'),('−1.00','down'),('0.00','flat'),('2.40','unknown')]:
            with self.subTest(rate=rate):
                result = parse_stock_snapshot(f'225,000원 {rate}% | 삼성전자')
                self.assertEqual(result['direction'], expected)
                self.assertEqual(result['price'], 225000)
        self.assertEqual(parse_stock_snapshot('삼성전자')['direction'], 'unknown')


class StreamAnalysisTests(TestCase):
    def test_empty_company_does_not_crawl(self):
        with patch('crawling.views.crawl_comments') as crawl:
            response = self.client.get(reverse('crawling:crawl_stream'))
            body = b''.join(response.streaming_content).decode()
        self.assertIn('error', body)
        crawl.assert_not_called()

    def test_analysis_failure_preserves_existing_output_and_is_saved(self):
        raw = {'company':'삼성전자','comments':['좋아요 주식'], 'stock_code':'A005930',
               'stock_snapshot':{'direction':'down','change_percent':-3.01}}
        filtered = {'comments':['좋아요 주식'],'iqr_thresholds':None}
        with patch('crawling.views.crawl_comments',return_value=raw), \
             patch('crawling.views.process_comments',return_value=filtered), \
             patch('crawling.views.augment_comments',return_value=['이 종목이 좋습니다']), \
             patch('crawling.views.analyze_comments_safely',return_value=unavailable_analysis()):
            response = self.client.get(reverse('crawling:crawl_stream'), {'company_name':'삼성'})
            events = [json.loads(chunk.decode().split('data: ',1)[1]) for chunk in response.streaming_content]
        self.assertEqual(events[-1]['status'], 'complete')
        self.assertEqual(events[-1]['sentiment_analysis']['status'], 'unavailable')
        saved = CommentTaskResult.objects.get()
        self.assertEqual(saved.original_comments, raw['comments'])
        self.assertEqual(saved.stock_snapshot['direction'], 'down')
        self.assertEqual(saved.augmented_comments, ['이 종목이 좋습니다'])

    def test_all_filtered_comments_still_allow_raw_sentiment(self):
        raw = {'company':'삼성전자','comments':['❤️'], 'stock_snapshot':{}}
        analysis = {'status':'complete','summary':'긍정적 반응입니다.'}
        with patch('crawling.views.crawl_comments',return_value=raw), \
             patch('crawling.views.process_comments',return_value={'comments':[]}), \
             patch('crawling.views.augment_comments',return_value=[]), \
             patch('crawling.views.analyze_comments_safely',return_value=analysis):
            response = self.client.get(reverse('crawling:crawl_stream'), {'company_name':'삼성'})
            events = [json.loads(chunk.decode().split('data: ',1)[1]) for chunk in response.streaming_content]
        self.assertEqual(events[-1]['status'], 'complete')
        self.assertEqual(CommentTaskResult.objects.get().sentiment_analysis, analysis)


class PipelineAnalysisTests(SimpleTestCase):
    def test_cli_pipeline_returns_quote_and_original_comment_analysis(self):
        from .services.run_pipeline import run_pipeline
        raw = {'company':'삼성전자', 'comments':['원본 댓글 ❤️'],
               'collected_at':'2026-10-30', 'stock_snapshot':{'direction':'down'}}
        filtered = {'comments':['정제 댓글'], 'prepared_comments':['정제 댓글'],
                    'timings_seconds':{}, 'raw_comments':raw['comments']}
        analysis = {'status':'complete','summary':'요약','counts':{'positive':1}}
        with patch('crawling.services.run_pipeline.crawl_comments',return_value=raw), \
             patch('crawling.services.run_pipeline.process_comments',return_value=filtered), \
             patch('crawling.services.run_pipeline.augment_comments',return_value=['증강 댓글']), \
             patch('crawling.services.run_pipeline.analyze_comments_safely',return_value=analysis) as analyze:
            result = run_pipeline('삼성')
        analyze.assert_called_once_with(raw['comments'], '삼성전자')
        self.assertEqual(result['stock_snapshot'], raw['stock_snapshot'])
        self.assertEqual(result['sentiment_analysis'], analysis)
