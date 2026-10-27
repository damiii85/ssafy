"""실제 색인/검색/그래프/근거 및 모델 프롬프트 실행을 재현하고 결과를 JSON으로 저장."""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.rag.knowledge import inventory, MANIFEST
from src.rag.retrieval import retrieve
from src.rag.settings import BASE_DIR, load_settings
from src.services.chat_controller import answer_question
from src.services.pilot_report import load_spot_data


def main(live_llm=False):
    settings=load_settings()
    result={'collections':inventory(),'index_repeat':json.loads(MANIFEST.read_text(encoding='utf-8')),
            'mode':'GMS actual service','cases':[]}
    questions=[('suseongmot','카페를 하고 싶어'),('daegu_downtown','중앙대로 412-21 100m 카페'),
               ('dongdaegu','유동인구는 몇 명이야?'),('chilgok3','교통 특징은?'),('samdeok','오늘 실시간 임대료는?')]
    if live_llm:
        questions.append(('suseongmot','수성못 카페 상권을 검색 근거로 설명해줘'))
    for region,question in questions:
        data,meta=load_spot_data(region)
        session={}
        started=time.perf_counter()
        text,report=answer_question(region,question,session,data,meta,1000)
        elapsed=time.perf_counter()-started
        rag=session['rag_last']
        numbers={int(n) for n in re.findall(r'\[근거 (\d+)\]',text)}
        listed={c['number'] for c in rag['citations']}
        assert numbers==listed,(numbers,listed)
        assert rag['trace']['nodes']==['retrieve','generate']
        result['cases'].append({'region_id':region,'question':question,'elapsed_seconds':round(elapsed,3),
            'answer':text,'report':report,'rag':rag,'citation_match':True})
        print(region,round(elapsed,3),'seconds',rag['trace'],flush=True)
    small=retrieve('상권 업종 현황','suseongmot',settings=dict(settings,top_k_stores=1,top_k_documents=1))
    large=retrieve('상권 업종 현황','suseongmot',settings=dict(settings,top_k_stores=3,top_k_documents=4))
    assert len(large['rag1'])>len(small['rag1'])
    assert len(large['rag2'])>len(small['rag2'])
    assert all(e['metadata']['region_id']=='suseongmot' for e in large['evidence'])
    result['top_k']={'small':[len(small['rag1']),len(small['rag2'])],
                     'large':[len(large['rag1']),len(large['rag2'])],'region_filter':True}
    if live_llm:
        last=result['cases'][-1]['rag']
        assert last['collection_audit']['prompt1_executed']
        assert last['collection_audit']['prompt2_executed']
        assert last['trace']['prompt3_executed'] or last['trace']['generation_cache_hit']
        assert '>' in result['cases'][-1]['answer'],'검색 원문 발췌가 답변에 없습니다.'
    path=BASE_DIR/'data/processed/rag_verification.json'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Verified:',path.name)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--live-llm',action='store_true')
    args=parser.parse_args()
    try:
        main(args.live_llm)
    except Exception as error:
        print('검증 실패: '+type(error).__name__+' · 실제 성공으로 기록하지 않았습니다.',file=sys.stderr)
        raise SystemExit(1)
