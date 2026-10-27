"""Restore bundled vectors locally, avoiding Windows Unicode native-index paths."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile
from functools import lru_cache

from src.rag.settings import BASE_DIR


@lru_cache(maxsize=1)
def chroma_path():
    snapshot=BASE_DIR/'db/portable_vectors.json.gz'
    if not snapshot.exists():
        return BASE_DIR/'db/chroma_db'
    digest=hashlib.sha256(snapshot.read_bytes()).hexdigest()
    root=Path(os.getenv('SPOTCHECK_VECTOR_CACHE',str(BASE_DIR/'db/runtime')))/digest[:20]
    if os.name=='nt' and not str(root).isascii():
        root=Path(tempfile.gettempdir())/'spotcheck_vectors'/digest[:20]
        if not str(root).isascii():
            root=Path(os.environ.get('PUBLIC','C:/Users/Public'))/'spotcheck_vectors'/digest[:20]
    root.mkdir(parents=True,exist_ok=True)
    marker=root/'ready.json'
    database=root/'chroma_db'
    if not marker.exists():
        import chromadb
        with gzip.open(snapshot,'rt',encoding='utf-8') as f:
            bundled=json.load(f)
        client=chromadb.PersistentClient(path=str(database))
        for name,records in bundled['collections'].items():
            collection=client.get_or_create_collection(name)
            for start in range(0,len(records['ids']),200):
                collection.upsert(**{key:values[start:start+200] for key,values in records.items()})
            assert collection.count()==len(records['ids'])
            # Force a query before completing the restoration.
            collection.query(query_embeddings=[records['embeddings'][0]],n_results=1)
        marker.write_text(json.dumps({'snapshot_sha256':digest}),encoding='utf-8')
    return database
