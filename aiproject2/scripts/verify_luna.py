"""One live Luna RAG question; fails if any model stage silently falls back."""
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.rag.index_documents import get_llm
from src.services.chat_controller import answer_question
from src.services.pilot_report import load_spot_data


def main():
    model = get_llm().model_name
    assert model == 'gpt-6-luna', 'Expected Luna configuration'
    data, metadata = load_spot_data('suseongmot')
    session = {}
    start = time.perf_counter()
    answer, _ = answer_question('suseongmot',
        '수성못 카페 상권의 특징을 검색 근거로 설명해줘', session, data, metadata, 1000)
    rag = session['rag_last']
    assert rag['collection_audit']['prompt1_executed'], 'Prompt 1 did not execute'
    assert rag['collection_audit']['prompt2_executed'], 'Prompt 2 did not execute'
    assert rag['trace']['prompt3_executed'] or rag['trace']['generation_cache_hit'], 'Prompt 3 failed'
    assert not rag['statuses'], 'Service reported fallback or missing evidence'
    assert rag['trace']['rag1_count'] and rag['trace']['rag2_count']
    assert {int(n) for n in re.findall(r'\[근거 (\d+)\]', answer)} == {c['number'] for c in rag['citations']}
    assert '>' in answer, 'Missing validated source quotation'
    result = {'executed_at': datetime.now(timezone.utc).isoformat(), 'model': model,
              'api': 'responses', 'elapsed_seconds': round(time.perf_counter()-start, 3),
              'rag': rag, 'answer': answer}
    output = Path('data/processed/luna_verification.json')
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('model', 'api', 'elapsed_seconds')}))
    print(json.dumps(rag['trace']))
    print('Verified:', output)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Luna verification failed:', type(error).__name__)
        if isinstance(error, AssertionError):
            print(str(error))
        sys.exit(1)
