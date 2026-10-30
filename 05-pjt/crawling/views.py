import json
from concurrent.futures import ThreadPoolExecutor

from django.shortcuts import render
from django.http import StreamingHttpResponse

from .models import CommentTaskResult
from .services.crawling import crawl_comments
from .services.filter import process_comments
from .services.augment import augment_comments, merge_with_source
from .services.sentiment import analyze_comments_safely


def stream_event(status, message, **extra):
    return 'data: ' + json.dumps({'status': status, 'message': message, **extra}, ensure_ascii=False) + '\n\n'


def crawl_stream(request):
    company_name = request.GET.get('company_name', '').strip()

    def event_stream():
        if not company_name:
            yield stream_event('error', '회사명이 입력되지 않았습니다.')
            return
        try:
            yield stream_event('info', f'[{company_name}] 토스증권 접속 및 댓글 수집 중...')
            raw = crawl_comments(company_name, limit=20)
            company = raw['company']
            originals = raw.get('comments', [])
            snapshot = raw.get('stock_snapshot', {})
            yield stream_event('snapshot', '수집 시점의 주가를 확인했습니다. 댓글을 분석합니다.',
                               company=company, stock_snapshot=snapshot)
            if not originals:
                yield stream_event('error', '수집된 댓글이 없습니다. 다른 회사로 검색하거나 잠시 후 다시 시도해 주세요.')
                return

            # Analyze unchanged comments concurrently with the existing data pipeline.
            with ThreadPoolExecutor(max_workers=1) as pool:
                analysis_future = pool.submit(analyze_comments_safely, originals, company)
                yield stream_event('progress', '데이터 정제 및 부적절한 표현 제거 중... 원본 댓글 요약·감성분석도 함께 진행합니다.')
                filtered = process_comments(raw, criteria_name='strict')
                cleaned = filtered.get('comments', [])
                yield stream_event('progress', 'LLM을 활용한 의미 기반 데이터 증강 중...')
                augmented = augment_comments(cleaned)
                integrated = merge_with_source(cleaned, augmented)
                yield stream_event('progress', '댓글 요약·감성분석 결과를 확인 중...')
                analysis = analysis_future.result()

            yield stream_event('progress', '완료된 데이터를 DB에 저장 중...')
            CommentTaskResult.objects.create(
                actual_company_name=company,
                original_comments=originals,
                cleaned_comments=cleaned,
                augmented_comments=augmented,
                iqr_thresholds=filtered.get('iqr_thresholds') or {},
                stock_snapshot=snapshot,
                sentiment_analysis=analysis,
            )
            message = f'수집({len(originals)}) ➔ 정제({len(cleaned)}) ➔ 증강({len(augmented)}) DB 저장 완료!'
            if not cleaned:
                message += ' 정제 후 남은 댓글은 없으며, 원본 댓글 분석을 표시합니다.'
            if analysis['status'] != 'complete':
                message += ' 댓글 요약·감성분석은 완료하지 못했습니다.'
            yield stream_event('complete', message, company=company,
                stock_snapshot=snapshot, sentiment_analysis=analysis,
                data={'original': originals, 'cleaned': cleaned,
                      'augmented': augmented, 'integrated': integrated})
        except Exception as error:
            print(f'[Pipeline Error] {type(error).__name__}: {error}')
            yield stream_event('error', '처리 중 오류가 발생했습니다. 회사명을 확인하거나 잠시 후 다시 시도해 주세요.')

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def index(request):
    return render(request, 'crawling/index.html')
