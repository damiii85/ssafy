"""두 컬렉션을 지역·업종으로 제한해 검색하고 근거를 중복 제거한다."""
import hashlib
import json
from functools import lru_cache

import chromadb

from src.rag.embeddings import get_embeddings
from src.rag.knowledge import corpus_signature
from src.rag.settings import BASE_DIR, load_settings
from src.services.spot_catalog import get_spot
from src.rag.portable_db import chroma_path


@lru_cache(maxsize=1)
def client():
    return chromadb.PersistentClient(path=str(chroma_path()))


def canonical_region(region_id):
    spot=get_spot(region_id)
    return spot.get('parent_id',region_id)


@lru_cache(maxsize=512)
def cached_query_vector(question,backend,model):
    return get_embeddings(dict(load_settings(),embedding_backend=backend)).embed_query(question)


def merge_evidence(*groups):
    result=[]
    seen=set()
    for group in groups:
        for evidence in group:
            meta=evidence['metadata']
            # 같은 출처/페이지의 중복 문단만 제거. 서로 다른 출처는 보존.
            identity=(meta.get('source'),meta.get('region_name'),meta.get('page'),hashlib.sha256(evidence['text'].strip().encode()).hexdigest())
            if identity not in seen:
                seen.add(identity)
                result.append(dict(evidence,evidence_id=f'R{len(result)+1}'))
    return result


def retrieve(question,region_id,categories=None,settings=None,db_client=None,embeddings=None,selected_document_ids=None):
    settings=settings or load_settings()
    provided_embeddings=embeddings is not None
    embeddings=embeddings or get_embeddings(settings)
    db_client=db_client or client()
    parent=canonical_region(region_id)
    version=corpus_signature()+':'+embeddings.model
    base=[{'region_id':parent},{'embedding_model':embeddings.model},{'corpus_version':version},
          {'chunk_size':settings['chunk_size']},{'chunk_overlap':settings['chunk_overlap']}]
    query_vector=(embeddings.embed_query(question) if provided_embeddings else
                  cached_query_vector(question,settings['embedding_backend'],embeddings.model))
    groups={}
    statuses=[]
    for name,top_k in [('store_metadata',settings['top_k_stores']),('external_documents',settings['top_k_documents'])]:
        try:
            collection=db_client.get_collection(name)
            filters=list(base)
            if name=='external_documents' and selected_document_ids is not None:
                if not selected_document_ids:
                    groups[name]=[]
                    continue
                filters.append({'document_id': {'$in': selected_document_ids}})
            if name=='store_metadata' and categories:
                conditions=[{'$and':[{'category_level':c['level']},{'category_name':c['name']}]} for c in categories]
                filters.append(conditions[0] if len(conditions)==1 else {'$or':conditions})
            spot=get_spot(region_id)
            if name=='external_documents' and region_id!=parent:
                filters.append({'region_name':spot['name']})
            where={'$and':filters}
            count=len(collection.get(where=where,include=[])['ids'])
            if not count:
                statuses.append(name+'에 해당 지역/업종의 최신 색인이 없습니다.')
                groups[name]=[]
                if name=='store_metadata':
                    mandatory=collection.get(where={'$and':base+[{'category_level':'region'}]},include=['documents','metadatas'])
                    groups[name]=[{'chunk_id':i,'text':t,'metadata':m,'distance':0,'collection':name}
                                  for i,t,m in zip(mandatory['ids'],mandatory['documents'],mandatory['metadatas'])]
                continue
            result=collection.query(query_embeddings=[query_vector],n_results=min(top_k,count),where=where,
                                     include=['documents','metadatas','distances'])
            groups[name]=[{'chunk_id':identity,'text':text,'metadata':meta,'distance':distance,'collection':name}
                for identity,text,meta,distance in zip(result['ids'][0],result['documents'][0],result['metadatas'][0],result['distances'][0])]
            if name=='store_metadata':
                # 선택 지역 자체의 메타데이터는 top-k와 별도로 항상 포함한다.
                mandatory=collection.get(where={'$and':base+[{'category_level':'region'}]},include=['documents','metadatas'])
                for identity,text,meta in zip(mandatory['ids'],mandatory['documents'],mandatory['metadatas']):
                    groups[name].append({'chunk_id':identity,'text':text,'metadata':meta,'distance':0,'collection':name})
        except Exception:
            groups[name]=[]
            statuses.append(name+' 검색이 불가능합니다. 색인과 연결 설정을 확인해 주세요.')
    return {'rag1':groups.get('store_metadata',[]),'rag2':groups.get('external_documents',[]),
            'evidence':merge_evidence(*groups.values()),'statuses':statuses,'region_id':parent}
