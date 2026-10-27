"""명시적 외부 처리 승인 전에는 로컬 문자 n-gram 벡터화만 사용한다."""
import hashlib
import math
import re
import os
from functools import lru_cache

from src.rag.settings import load_settings


class LocalEmbeddings:
    """학습형 의미 임베딩이 아닌 재현 가능한 한국어 문자 2/3-gram 검색 벡터."""
    model='local-char-ngram-v1'
    dimensions=1536

    def embed_query(self,text):
        compact=re.sub(r'\s+',' ',str(text).lower())
        vector=[0.0]*self.dimensions
        for n in (2,3):
            for start in range(max(0,len(compact)-n+1)):
                digest=hashlib.blake2b(compact[start:start+n].encode(),digest_size=8).digest()
                number=int.from_bytes(digest,'big')
                vector[number%self.dimensions]+=1 if number&(1<<63) else -1
        norm=math.sqrt(sum(v*v for v in vector))
        return [v/norm for v in vector] if norm else vector

    def embed_documents(self,texts):
        return [self.embed_query(text) for text in texts]


def get_embeddings(settings=None):
    settings=settings or load_settings()
    if settings['embedding_backend']=='local' or os.getenv('SPOTCHECK_RAG_OFFLINE')=='1':
        return LocalEmbeddings()
    if settings['embedding_backend']!='gms' or not settings.get('external_processing_approved'):
        raise ValueError('GMS 문서 전송이 승인되지 않았습니다. 로컬 임베딩을 사용해 주세요.')
    return _gms_embeddings()


@lru_cache(maxsize=1)
def _gms_embeddings():
    from src.rag.index_documents import get_embeddings as gms_embeddings
    return gms_embeddings()
