"""요구서 지정 버전의 별도 환경에서 충돌·72개 회귀·선택 실모델 연동 검사."""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))


def main(live=False):
    pins={}
    for line in (BASE/'requirements.txt').read_text(encoding='utf-8').splitlines():
        if '==' in line and not line.startswith('#'):
            name,expected=line.split('==')
            pins[name]={'required':expected,'actual':version(name)}
    assert all(p['required']==p['actual'] for p in pins.values()),'지정 버전 불일치'
    subprocess.run([sys.executable,'-m','pip','check'],check=True,cwd=BASE)
    subprocess.run([sys.executable,'scripts/run_tests.py'],check=True,cwd=BASE)
    result={'executed_at':datetime.now(timezone.utc).isoformat(),'python':sys.version.split()[0],
            'versions':pins,'pip_check':'passed',
            'tests':json.loads((BASE/'data/processed/unit_test_results.json').read_text(encoding='utf-8'))}
    if live:
        from src.rag.index_documents import get_llm
        from src.services.chat_controller import answer_question
        from src.services.pilot_report import load_spot_data
        stores,metadata=load_spot_data('suseongmot')
        state={}
        answer,visual=answer_question('suseongmot','카페를 하고 싶어',state,stores,metadata,1000)
        rag=state['rag_last']
        assert rag['trace']['nodes']==['retrieve','generate']
        assert rag['trace']['rag1_count'] and rag['trace']['rag2_count']
        assert rag['trace']['prompt3_executed'] or rag['trace']['generation_cache_hit']
        assert visual['competitor_count']==95 and visual['total_stores']==2106
        assert {int(n) for n in re.findall(r'\[근거 (\d+)\]',answer)}=={c['number'] for c in rag['citations']}
        assert not rag['statuses'], '실모델 대체/실패 안내 발생'
        # 서비스 생성 캐시가 적중해도 지정 버전의 모델 클라이언트 실호출을 별도 확인한다.
        probe=get_llm(timeout=30).invoke([
            ('system','대구 상권 질문에 답하라. 제공 자료에 없는 정확한 수치는 모른다고 밝혀라.'),
            ('human','수성못의 현재 카페 수를 알고 있나요?')])
        result['gms_direct_model']={'question':'수성못의 현재 카페 수를 알고 있나요?',
                                    'answer':probe.content,'actual_request':True}
        result['gms_smoke']={'question':'카페를 하고 싶어','answer':answer,'trace':rag['trace'],
                             'citations':rag['citations'],'source_counts_verified':True}
    (BASE/'data/processed/spec_environment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('지정 버전 환경 검증 기록 저장 완료')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--live-llm',action='store_true')
    args=parser.parse_args()
    try:
        main(args.live_llm)
    except Exception as error:
        print('지정 환경 검증 실패: '+type(error).__name__,file=sys.stderr)
        raise SystemExit(1)
