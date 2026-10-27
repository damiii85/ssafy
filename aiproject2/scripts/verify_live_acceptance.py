"""Measure uncached and repeated GMS runs, keeping caches isolated."""
import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from src.rag.collection_flow import collect_candidates
from src.services.chat_controller import answer_question
from src.services.pilot_report import load_spot_data


def main():
    question = '수성못 카페 상권의 특징을 검색 근거로 설명해줘'
    data, metadata = load_spot_data('suseongmot')
    runs = []
    with tempfile.TemporaryDirectory() as directory:
        cache = Path(directory)
        def isolated(*args, **kwargs):
            return collect_candidates(*args, cache_dir=cache/'selection', **kwargs)
        with patch('src.rag.pipeline.collect_candidates', side_effect=isolated), \
             patch('src.rag.generation.BASE_DIR', cache):
            for kind in ('uncached', 'repeat'):
                session = {}
                started = time.perf_counter()
                answer, _ = answer_question('suseongmot', question, session, data, metadata, 1000)
                rag = session['rag_last']
                runs.append({'kind':kind, 'elapsed_seconds':round(time.perf_counter()-started,3),
                             'rag':rag, 'answer':answer})
    first, repeat = runs
    checks = {
        'fresh_prompt1':first['rag']['collection_audit']['prompt1_executed'],
        'fresh_prompt2':first['rag']['collection_audit']['prompt2_executed'],
        'fresh_prompt3':first['rag']['trace']['prompt3_executed'],
        'selection_restricts_search':bool(first['rag']['collection_audit']['selected_document_ids']),
        'both_collections':all(r['rag']['trace']['rag1_count'] and r['rag']['trace']['rag2_count'] for r in runs),
        'no_fallback':all(not r['rag']['statuses'] for r in runs),
        'repeat_selection_cache':repeat['rag']['collection_audit']['cache_hit'],
        'repeat_generation_cache':repeat['rag']['trace']['generation_cache_hit'],
        'citations_present':all(r['rag']['citations'] for r in runs),
    }
    result={'question':question,'model':'gpt-6-luna','runs':runs,'checks':checks,
            'scope':'One user, one representative PDF question; no load/SLA claim.'}
    (BASE/'data/processed/live_acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'checks':checks,'seconds':[r['elapsed_seconds'] for r in runs]}))
    assert all(checks.values()), 'Live verification failed; inspect saved statuses.'


if __name__=='__main__': main()
