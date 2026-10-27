"""F2015: 동일 모델의 무검색 답변과 실제 서비스 답변 5쌍을 기록한다."""
import json
import argparse
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.rag.index_documents import get_llm
from src.rag.settings import BASE_DIR, load_settings
from src.services.chat_controller import answer_question
from src.services.pilot_report import load_spot_data
from src.services.spot_catalog import get_spot

CASES = [
    ('suseongmot', '수성못에서 카페를 하고 싶어. 등록된 전체 상가와 카페 수는?', 'counts'),
    ('daegu_downtown', '중앙대로 412-21 100m 이내 카페는 몇 곳이야?', 'radius'),
    ('dongdaegu', '동대구역 상권의 일평균 유동인구는 몇 명이야?', 'pdf'),
    ('chilgok3', '칠곡3지구 상권의 교통 특징은?', 'transport'),
    ('samdeok', '삼덕동 상권의 오늘 실시간 점포 임대료는 얼마야?', 'unknown'),
]


def main(output_path=None):
    settings = load_settings()
    if not settings.get('external_processing_approved') or settings['generation_mode'] != 'llm':
        raise ValueError('승인된 GMS llm 설정에서만 실제 비교를 실행합니다.')
    llm = get_llm(timeout=45)
    results = {'executed_at':datetime.now(timezone.utc).isoformat(), 'model':llm.model_name,
               'method':'무검색 LLM 대 실제 CSV/PDF 검증·RAG 검색·발췌 결합 서비스 비교. 순수 프롬프트 단독 효과 실험이 아님.',
               'cases':[]}
    output = Path(output_path) if output_path else BASE_DIR/'data/processed/rag_quality_comparison.json'
    for region, question, kind in CASES:
        start = time.perf_counter()
        # 질문·지역명 외에 CSV/PDF·검색 결과·정답·이전 대화는 보내지 않는다.
        baseline = llm.invoke([
            ('system', '너는 대구 상권 분석 도우미다. 질문에 사실에 근거해 답하고, 모르는 수치는 알 수 없다고 밝혀라. 출처를 만들어내지 마라.'),
            ('human', f'선택 지역: {get_spot(region)["name"]}\n질문: {question}')]).text
        before_seconds = round(time.perf_counter()-start,3)
        stores, metadata = load_spot_data(region)
        session = {}
        start = time.perf_counter()
        answer, visual = answer_question(region, question, session, stores, metadata, 1000)
        rag = session['rag_last']
        assert rag['trace']['nodes'] == ['retrieve', 'generate']
        assert {int(n) for n in re.findall(r'\[근거 (\d+)\]', answer)} == {c['number'] for c in rag['citations']}
        results['cases'].append({'region':region,'question':question,'kind':kind,
            'before':baseline,'before_seconds':before_seconds,'after':answer,
            'after_seconds':round(time.perf_counter()-start,3),'visual':visual,
            'citations':rag['citations'],'trace':rag['trace'],'statuses':rag['statuses'],
            'collection_audit':rag.get('collection_audit',{})})
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'{len(results["cases"])}/5 {kind}: 실제 응답 저장',flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output')
    args = parser.parse_args()
    try:
        main(args.output)
    except Exception as error:
        print('비교 중단: '+type(error).__name__+' (완료로 처리하지 않음)',file=sys.stderr)
        raise SystemExit(1)
