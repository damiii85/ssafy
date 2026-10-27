"""지정된 기존 PDF 후보 검색·선별 및 검색어/선별 결과 캐시."""
import hashlib
import json
import time

from src.rag.index_documents import generate_queries, select_candidates
from src.rag.knowledge import pdf_documents, corpus_signature
from src.rag.settings import BASE_DIR, load_settings
from src.services.spot_catalog import get_spot

CACHE_DIR=BASE_DIR/'data/raw/rag_collection_cache'


def _cached(path,ttl):
    try:
        value=json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value,dict) and time.time()-float(value['created_at'])<ttl else None
    except (OSError,ValueError,KeyError,TypeError):
        return None


def collect_candidates(question,region_id,llm=None,cache_dir=CACHE_DIR,settings=None,store_context=None):
    settings=settings or load_settings()
    signature=hashlib.sha256(json.dumps([question.strip(),region_id,corpus_signature(),bool(llm),
        settings['selection_min_score'],store_context or {},
        str(getattr(llm,'model_name','none')),'selection-v4'],ensure_ascii=True).encode()).hexdigest()
    path=cache_dir/(signature+'.json')
    cached=_cached(path,settings['cache_ttl_seconds'])
    if cached:
        return dict(cached,cache_hit=True)
    context={'region_id':region_id,'region_name':get_spot(region_id)['name'],'domain':'상권 분석',**(store_context or {})}
    errors=[]
    queries=[]
    prompt1=prompt2=False
    if llm:
        try:
            queries=generate_queries(question,context,llm)
            prompt1=True
        except Exception:
            errors.append('검색어 모델 호출 실패 · 기존 지역 자료를 사용합니다.')
    if not queries:
        queries=[question.strip()[:200] or region_id+' 상권']
    search_key=hashlib.sha256(json.dumps([sorted(queries),region_id,corpus_signature(),'candidate-v4'],ensure_ascii=True).encode()).hexdigest()
    search_path=cache_dir/('search_'+search_key+'.json')
    search_cache_hit=False
    cached_search=_cached(search_path,settings['cache_ttl_seconds'])
    if cached_search:
        candidates=cached_search['candidates']
        search_cache_hit=True
    if not search_cache_hit:
        documents=pdf_documents()
        candidates=[{'id':i,'title':d['title'],'url':d['url'],'region_id':d['region_id'],
            'snippet':d['text'][:700], 'source':d['source'],'page':d['page'],
            'source_type':d['source_type']} for i,d in enumerate(documents)]
        cache_dir.mkdir(parents=True,exist_ok=True)
        search_path.write_text(json.dumps({'created_at':time.time(),'candidates':candidates},ensure_ascii=False),encoding='utf-8')
    regional=[d for d in candidates if d['region_id']==region_id]
    if not regional:
        errors.append('선택 지역의 외부 문서 후보가 없습니다. PDF 파일과 지역 설정을 확인해 주세요.')
    selected=[]
    if llm and regional:
        try:
            selected=select_candidates(question,regional,settings['selection_min_score'],llm)
            prompt2=True
        except Exception:
            errors.append('후보 선별 모델 호출 실패 · 지정 지역 문서를 보존합니다.')
    # 지역 설명은 필수 보존하고 통계 후보에는 모델 선별 결과를 적용한다.
    chosen={d['id']:d for d in selected}
    for item in (regional if not prompt2 else [d for d in regional if d.get('source_type')=='pdf_chapter']):
        chosen.setdefault(item['id'],dict(item,reason='선택 지역 자체의 설명/통계 · 필수 포함'))
    selected=list(chosen.values())
    rejected=[dict(d,reason='다른 지역 문서' if d['region_id']!=region_id else '모델 선별 기준 미충족') for d in candidates if d['id'] not in chosen]
    result={'created_at':time.time(),'question':question,'region_id':region_id,'queries':queries,
        'candidates':candidates,'selected':selected,'rejected':rejected,'errors':errors,
        'prompt1_executed':prompt1,'prompt2_executed':prompt2,'cache_hit':False,'search_cache_hit':search_cache_hit}
    cache_dir.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


def index_selected(audit, settings, db_client=None, embeddings=None):
    """Index selected PDFs only; shared cached documents remain for other requests."""
    from src.rag.embeddings import get_embeddings
    from src.rag.index_documents import index_document, split_document
    from src.rag.retrieval import client
    embeddings = embeddings or get_embeddings(settings)
    collection = (db_client or client()).get_or_create_collection('external_documents')
    documents = {d['url']: d for d in pdf_documents()}
    selected_ids, reused, embedded = [], 0, 0
    for candidate in audit.get('selected', []):
        document = dict(documents[candidate['url']])
        identity = hashlib.sha256(document['url'].encode()).hexdigest()
        document['corpus_version'] = corpus_signature()+':'+embeddings.model
        where = {'$and': [{'document_id': identity}, {'embedding_model': embeddings.model},
                         {'corpus_version': document['corpus_version']},
                         {'chunk_size': settings['chunk_size']}, {'chunk_overlap': settings['chunk_overlap']}]}
        existing = collection.get(where=where, include=['documents'])
        expected = split_document(document['text'], settings['chunk_size'], settings['chunk_overlap'])
        if sorted(existing['documents']) == sorted(expected):
            reused += len(expected)
        else:
            outcome = index_document(document, collection, embeddings, settings['chunk_size'], settings['chunk_overlap'])
            embedded += outcome['embedded']
        selected_ids.append(identity)
    return {'selected_document_ids': selected_ids, 'reused_chunks': reused,
            'embedded_chunks': embedded, 'excluded_candidates': len(audit.get('rejected', []))}
