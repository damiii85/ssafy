import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import json
import chromadb
from src.rag.collection_flow import collect_candidates, index_selected
from src.rag.embeddings import LocalEmbeddings
from src.rag.retrieval import retrieve
from src.rag.settings import load_settings
from src.collectors.collect_spot_stores import unpack


class SelectedIndexTests(unittest.TestCase):
    def test_selection_controls_actual_index_and_retrieval(self):
        settings = dict(load_settings(), embedding_backend='local', external_processing_approved=False)
        model = Mock(model_name='selection-proof')
        model.invoke.side_effect = [SimpleNamespace(content=json.dumps(x)) for x in
                                   ({'queries':['suseongmot report']}, {'selected':[]})]
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            audit = collect_candidates('report', 'suseongmot', model, Path(directory), settings)
            client = chromadb.PersistentClient(path=str(Path(directory)/'db'))
            embeddings = LocalEmbeddings()
            result = index_selected(audit, settings, client, embeddings)
            self.assertEqual(len(result['selected_document_ids']), 1)
            self.assertGreater(result['embedded_chunks'], 0)
            self.assertGreater(result['excluded_candidates'], 0)
            records = client.get_collection('external_documents').get(include=['metadatas'])
            self.assertTrue(all(m['document_id'] in result['selected_document_ids'] for m in records['metadatas']))
            repeat = index_selected(audit, settings, client, embeddings)
            self.assertEqual(repeat['embedded_chunks'], 0)
            self.assertGreater(repeat['reused_chunks'], 0)
            found = retrieve('report', 'suseongmot', settings=settings, db_client=client,
                             embeddings=embeddings, selected_document_ids=result['selected_document_ids'])
            self.assertTrue(found['rag2'])
            self.assertTrue(all(e['metadata']['document_id'] in result['selected_document_ids'] for e in found['rag2']))
            empty = retrieve('report', 'suseongmot', settings=settings, db_client=client,
                             embeddings=embeddings, selected_document_ids=[])
            self.assertEqual(empty['rag2'], [])

    def test_active_collector_can_parse_response(self):
        self.assertEqual(unpack({'response':{'body':{'items':{'item':{'bizesId':'1'}},'totalCount':1}}}),
                         ([{'bizesId':'1'}],1))
