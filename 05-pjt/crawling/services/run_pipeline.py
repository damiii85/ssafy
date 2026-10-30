"""Run collection, local cleaning, LLM filtering and augmentation once.

Django: result = run_pipeline(company_name)
CLI: python run_pipeline.py
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

if __package__:
    from .sentiment import analyze_comments_safely
    from .crawling import crawl_comments
    from .filter import process_comments
    from .augment import augment_comments, merge_with_source, show_pairs
else:
    from sentiment import analyze_comments_safely
    from crawling import crawl_comments
    from filter import process_comments
    from augment import augment_comments, merge_with_source, show_pairs

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'


def save_json(data, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    print(f'[Saved] {path}')


def run_pipeline(company_name, limit=20, *, save_files=False, reuse_raw=False):
    """Return all stages. File saving and saved-input reuse are CLI options."""
    if not isinstance(company_name, str) or not company_name.strip():
        raise ValueError('Please enter a company name.')
    if type(limit) is not int or limit <= 0:
        raise ValueError('limit must be a positive integer.')
    company_name = company_name.strip()
    total_started = perf_counter()
    started = perf_counter()
    if reuse_raw:
        with (DATA_DIR / 'comments_raw.json').open(encoding='utf-8') as file:
            raw = json.load(file)
        if raw['company'] != company_name:
            raise ValueError('Saved company does not match the requested company.')
        raw = {**raw, 'comments': raw['comments'][:limit]}
        raw['count'] = len(raw['comments'])
    else:
        print('[1/4] Collecting comments...')
        raw = crawl_comments(company_name, limit=limit)
    crawl_seconds = perf_counter() - started
    if save_files:
        save_json(raw, DATA_DIR / 'comments_raw.json')

    with ThreadPoolExecutor(max_workers=1) as pool:
        analysis_future = pool.submit(analyze_comments_safely, raw['comments'], raw['company'])
        print('[2/4 - 3/4] Local cleaning and LLM filtering...')
        filtered = process_comments(raw)
        if save_files:
            save_json(filtered, DATA_DIR / 'comments_filtered.json')
            save_json(filtered, DATA_DIR / 'comments_clean.json')
    
        print('[4/4] Augmenting comments...')
        started = perf_counter()
        cleaned = filtered['comments']
        augmented = augment_comments(cleaned)
        augment_seconds = perf_counter() - started
        records = merge_with_source(cleaned, augmented)
        analysis = analysis_future.result()
    result = {
        **filtered,
        'stock_snapshot': raw.get('stock_snapshot', {}),
        'sentiment_analysis': analysis,
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'cleaned_comments': cleaned,
        'augmented_comments': augmented,
        'records': records,
        'count': len(records),
        'counts': {
            'collected': len(raw['comments']),
            'prepared': len(filtered['prepared_comments']),
            'cleaned': len(cleaned),
            'augmented': len(augmented),
        },
        'message': ('No comments found.' if not raw['comments'] else
                    'No comments remained after preprocessing.' if not cleaned else ''),
        'timings_seconds': {
            **filtered['timings_seconds'],
            'crawl_or_load': round(crawl_seconds, 3),
            'llm_augment': round(augment_seconds, 3),
            'total': round(perf_counter() - total_started, 3),
        },
    }
    if save_files:
        save_json(result, DATA_DIR / 'comments_augmented.json')
        save_json(result, DATA_DIR / 'pipeline_result.json')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--company', help='Company search text')
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--reuse-raw', action='store_true', help='Development: use saved comments')
    args = parser.parse_args()
    company = args.company if args.company is not None else input('Company name: ')
    result = run_pipeline(company, limit=args.limit, save_files=True, reuse_raw=args.reuse_raw)
    print('[Stock snapshot]', result['stock_snapshot'])
    print('[Summary]', result['sentiment_analysis'].get('summary') or result['sentiment_analysis'].get('message'))
    print('[Sentiment]', result['sentiment_analysis'].get('counts', {}))
    print('[Counts]', result['counts'])
    print('[Seconds]', result['timings_seconds'])
    if result['message']:
        print(result['message'])
    show_pairs(result['cleaned_comments'], result['augmented_comments'])
