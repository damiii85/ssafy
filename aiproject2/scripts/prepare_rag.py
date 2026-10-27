"""로컬의 활성 자료만 두 Chroma 컬렉션에 색인하고 재실행 결과를 기록한다."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import chromadb
from src.rag.index_documents import index_document, split_document
from src.rag.embeddings import get_embeddings
from src.rag.knowledge import pdf_documents, store_documents, corpus_signature, inventory, MANIFEST
from src.rag.settings import BASE_DIR, load_settings
from src.rag.portable_db import chroma_path


def prepare():
    settings=load_settings()
    client=chromadb.PersistentClient(path=str(chroma_path()))
    embeddings=get_embeddings()
    version=corpus_signature()+':'+embeddings.model
    result={'corpus_version':version,'settings':settings,'collections':{},'started_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    corpora=[('store_metadata',store_documents()),('external_documents',pdf_documents())]
    # 기존 색인 함수는 재사용하되 API 요청은 문서마다 보내지 않고 50청크씩 묶는다.
    pending={}
    vector_cache={}
    for name,documents in corpora:
        collection=client.get_or_create_collection(name)
        existing=collection.get(where={'corpus_version':version},include=['documents','embeddings'])
        known=set(existing['documents'])
        if existing['embeddings'] is not None:
            vector_cache.update(zip(existing['documents'],existing['embeddings']))
        for document in documents:
            for text in split_document(document['text'],settings['chunk_size'],settings['chunk_overlap']):
                if text not in known:
                    pending[text]=None
    texts=list(pending)
    for start in range(0,len(texts),50):
        batch=texts[start:start+50]
        pending.update(zip(batch,embeddings.embed_documents(batch)))
        print(f'embedding: {min(start+50,len(texts))}/{len(texts)}',flush=True)
    class PreparedEmbeddings:
        model=embeddings.model
        def embed_documents(self,texts):
            return [pending[t] if t in pending else vector_cache[t] for t in texts]
    prepared=PreparedEmbeddings()
    for name,documents in corpora:
        collection=client.get_or_create_collection(name)
        totals={'documents':len(documents),'chunks':0,'embedded':0,'removed':0}
        for number,document in enumerate(documents,1):
            document['corpus_version']=version
            stats=index_document(document,collection,prepared,settings['chunk_size'],settings['chunk_overlap'])
            for field in ('chunks','embedded','removed'):
                totals[field]+=stats[field]
            if number%50==0:
                print(f'{name}: {number}/{len(documents)}',flush=True)
        totals['collection_total']=collection.count()
        result['collections'][name]=totals
    result['elapsed_seconds']=round(time.perf_counter()-prepare.started,3)
    MANIFEST.parent.mkdir(parents=True,exist_ok=True)
    MANIFEST.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--inventory',action='store_true')
    args=parser.parse_args()
    if args.inventory:
        print(json.dumps(inventory(),ensure_ascii=False))
    else:
        prepare.started=time.perf_counter()
        try:
            prepare()
        except Exception as error:
            print('색인 실패: '+type(error).__name__+' · 연결/키/색인 설정을 확인해 주세요.',file=sys.stderr)
            raise SystemExit(1)
