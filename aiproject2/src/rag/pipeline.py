"""실제 채팅의 START → retrieve → generate → END 파이프라인."""
import os
import time
from contextvars import ContextVar
from functools import lru_cache
from typing import Any, TypedDict

from langgraph.graph import StateGraph, START, END

from src.rag.collection_flow import collect_candidates, index_selected
from src.rag.generation import generate_quotes, cite_answer
from src.rag.index_documents import get_llm
from src.rag.retrieval import retrieve
from src.rag.settings import load_settings
from src.services.pdf_evidence import PDF_PATH

ACTIVE=ContextVar('spotcheck_graph_active',default=False)


class GraphState(TypedDict,total=False):
    spot_id:str
    question:str
    context_region:str
    session:dict
    stores:Any
    metadata:dict
    radius:float
    location:Any
    legacy:Any
    progress:Any
    core_text:str
    report:Any
    retrieved:dict
    citations:list
    statuses:list
    collection_audit:dict
    trace:dict
    llm:Any
    answer:str


def _progress(state,label):
    if state.get('progress'):
        state['progress'](label)


def _llm(state,settings):
    if os.getenv('SPOTCHECK_RAG_OFFLINE')=='1' or not settings.get('external_processing_approved'):
        return None
    mode=settings['generation_mode']
    explanatory=any(word in state['question'] for word in ('근거로 설명','종합 분석','심층 분석','검색 근거','왜 그런','상권 전략'))
    if mode=='llm' or (mode=='on_demand' and explanatory):
        try:
            return get_llm(timeout=settings['request_timeout_seconds'])
        except Exception:
            return None
    return None


def retrieve_node(state):
    start=time.perf_counter()
    _progress(state,'데이터 검색 중')
    # 기존의 검증된 주소·반경·전체 CSV 계산 및 PDF 해석을 그대로 재사용한다.
    core,report=state['legacy'](state['spot_id'],state['question'],state['session'],state['stores'],state['metadata'],state['radius'],state.get('location'))
    region_id=report.get('region_id',state['spot_id']) if report else state['session'].get('last_region',state['spot_id'])
    categories=(report or {}).get('categories',state['session'].get('request',{}).get('categories',[]))
    settings=load_settings()
    valid_core=report is not None or PDF_PATH.name in core
    llm=_llm(state,settings) if valid_core else None
    _progress(state,'외부 문서 검색 중')
    statuses=[]
    if not PDF_PATH.is_file():
        statuses.append('지정 PDF 파일이 없습니다. 보고서 파일을 확인해 주세요.')
    if valid_core and llm is None and (settings['generation_mode']=='llm' or any(word in state['question'] for word in ('근거로 설명','종합 분석','심층 분석','검색 근거','왜 그런','상권 전략'))):
        statuses.append('AI 모델 연결을 확인할 수 없습니다. API 키/연결 설정을 확인하고 재시도해 주세요. 검증된 원문 자료만 사용합니다.')
    audit={}
    if not valid_core:
        retrieved={'rag1':[],'rag2':[],'evidence':[]}
        statuses.append('질문의 범위에서 확인 가능한 근거가 없습니다. 지역·업종 또는 필요한 자료를 구체적으로 알려주세요.')
    else:
        try:
            audit=collect_candidates(state['question'],region_id,llm=llm,settings=settings,
                store_context={'categories':categories,'scope':(report or {}).get('scope_description','')})
            statuses.extend(audit.get('errors',[]))
        except Exception:
            statuses.append('문서 후보를 확인할 수 없습니다. 검증된 수집본만 사용합니다.')
        try:
            selection=index_selected(audit,settings)
            audit.update(selection)
            retrieved=retrieve(state['question'],region_id,categories,settings=settings,
                               selected_document_ids=selection['selected_document_ids'])
            statuses.extend(retrieved['statuses'])
        except Exception:
            retrieved={'rag1':[],'rag2':[],'evidence':[]}
            statuses.append('벡터 검색 연결을 확인할 수 없습니다. 검증된 API/PDF 자료를 사용합니다.')
    return {'core_text':core,'report':report,'context_region':region_id,'retrieved':retrieved,'statuses':statuses,'collection_audit':audit,'llm':llm,
            'trace':{'nodes':['retrieve'],'retrieve_seconds':round(time.perf_counter()-start,6),
                     'rag1_count':len(retrieved['rag1']),'rag2_count':len(retrieved['rag2']),
                     'merged_count':len(retrieved['evidence']),'generation_mode':settings['generation_mode']}}


def generate_node(state):
    start=time.perf_counter()
    _progress(state,'근거 분석 중')
    quotes=[]
    statuses=list(state['statuses'])
    prompt3=False
    generation_cache_hit=False
    _progress(state,'AI 답변 생성 중')
    if state.get('llm'):
        try:
            quotes,prompt3,generation_cache_hit=generate_quotes(state['question'],state['retrieved']['evidence'],state['llm'],with_trace=True)
        except Exception:
            statuses.append('생성 근거를 검증하지 못해 원문 발췌를 추가하지 않았습니다.')
    text,citations=cite_answer(state['core_text'],state['report'],state['context_region'],state['question'],quotes)
    trace=dict(state['trace'],nodes=state['trace']['nodes']+['generate'],generate_seconds=round(time.perf_counter()-start,6),
               prompt3_executed=prompt3,generation_cache_hit=generation_cache_hit,used_citations=len(citations))
    return {'answer':text,'citations':citations,'statuses':statuses,'trace':trace}


@lru_cache(maxsize=1)
def graph():
    builder=StateGraph(GraphState)
    builder.add_node('retrieve',retrieve_node)
    builder.add_node('generate',generate_node)
    builder.add_edge(START,'retrieve')
    builder.add_edge('retrieve','generate')
    builder.add_edge('generate',END)
    return builder.compile()


def run(spot_id,question,session,stores,metadata,radius,location,legacy,progress=None):
    started=time.perf_counter()
    token=ACTIVE.set(True)
    try:
        result=graph().invoke({'spot_id':spot_id,'question':question,'session':session,'stores':stores,
            'metadata':metadata,'radius':radius,'location':location,'legacy':legacy,'progress':progress})
        session['rag_last']={'trace':dict(result['trace'],total_seconds=round(time.perf_counter()-started,6)),
            'citations':result['citations'],'statuses':result['statuses'],
            'collection_audit':{k:result['collection_audit'].get(k) for k in ('queries','prompt1_executed','prompt2_executed','cache_hit','selected_document_ids','reused_chunks','embedded_chunks','excluded_candidates')}}
        return result['answer'],result['report']
    finally:
        ACTIVE.reset(token)
