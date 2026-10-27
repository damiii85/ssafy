import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from src.rag import knowledge


class PortableCorpusTests(unittest.TestCase):
    def test_signature_survives_timestamp_change_but_detects_content(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'config').mkdir()
            pdf=root/'report.pdf';pdf.write_bytes(b'PDF fixture')
            source=root/'active_report.source.json';source.write_text('{}')
            (root/'config/daegu_spots.json').write_text('[]')
            with patch.object(knowledge,'BASE_DIR',root),patch.object(knowledge,'PDF_PATH',pdf),patch.object(knowledge,'load_spots',return_value=[]):
                before=knowledge.corpus_signature()
                os.utime(pdf,(100,100))
                self.assertEqual(before,knowledge.corpus_signature())
                pdf.write_bytes(b'Updated PDF fixture')
                self.assertNotEqual(before,knowledge.corpus_signature())
