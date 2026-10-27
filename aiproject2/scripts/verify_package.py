"""Check packaged data and indexes without collecting data or calling an API."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import chromadb
from src.rag.settings import BASE_DIR, load_settings
from src.rag.knowledge import corpus_signature, pdf_documents
from src.rag.embeddings import LocalEmbeddings
from src.rag.portable_db import chroma_path
from src.services.spot_catalog import load_spots
from src.services.pilot_report import load_spot_data

settings=load_settings()
for spot in load_spots():
    frame,meta=load_spot_data(spot['id'])
    assert len(frame)==meta['count'], spot['id']
assert len(pdf_documents())==14
model='text-embedding-3-small' if settings['embedding_backend']=='gms' else LocalEmbeddings.model
version=corpus_signature()+':'+model
client=chromadb.PersistentClient(path=str(chroma_path()))
counts={}
for name,expected in [('store_metadata',1452),('external_documents',14)]:
    collection=client.get_collection(name)
    counts[name]=len(collection.get(where={'corpus_version':version},include=[])['ids'])
    assert counts[name]==expected,(name,counts[name],expected)
print('Packaged data/index verified:',counts)
print('Runtime:', 'GPT-6 Luna / GMS' if settings['embedding_backend']=='gms' else 'local search and CSV/PDF answers (no API key required)')
