import json
import os
import unittest
from unittest.mock import patch

import httpx

from src.rag.index_documents import get_llm, ask_json


class LunaResponsesTests(unittest.TestCase):
    def test_authenticated_429_retry_is_bounded(self):
        calls = []
        def respond(request):
            calls.append(request)
            self.assertEqual(request.headers['authorization'], 'Bearer fixture')
            return httpx.Response(429, headers={'retry-after':'0'}, json={
                'error':{'message':'rate limited','type':'rate_limit_error','code':'rate_limit_exceeded'}})
        with patch.dict(os.environ, {'GMS_API_KEY':'fixture','GMS_LLM_MODEL':'gpt-6-luna'}):
            llm=get_llm(timeout=15)
            llm.root_client=llm.root_client.with_options(
                http_client=httpx.Client(transport=httpx.MockTransport(respond)))
            with self.assertRaises(Exception):
                ask_json(llm,'Return JSON',{'test':True})
        self.assertEqual(len(calls),2)

    def test_responses_transport_and_text_blocks(self):
        def respond(request):
            self.assertTrue(request.url.path.endswith('/v1/responses'))
            body = json.loads(request.content)
            self.assertEqual(body['model'], 'gpt-6-luna')
            self.assertNotIn('temperature', body)
            self.assertIn('input', body)
            return httpx.Response(200, json={
                'id': 'resp_fixture', 'created_at': 1, 'object': 'response',
                'model': 'gpt-6-luna', 'status': 'completed',
                'output': [{'id': 'msg_fixture', 'type': 'message', 'role': 'assistant',
                            'status': 'completed', 'content': [
                                {'type': 'output_text', 'text': '{"status":"ok"}', 'annotations': []}]}]})
        with patch.dict(os.environ, {'GMS_API_KEY': 'fixture', 'GMS_LLM_MODEL': 'gpt-6-luna'}):
            llm = get_llm()
            llm.root_client = llm.root_client.with_options(
                http_client=httpx.Client(transport=httpx.MockTransport(respond)))
            self.assertEqual(ask_json(llm, 'Return JSON', {'check': True}), {'status': 'ok'})

    def test_legacy_model_override(self):
        with patch.dict(os.environ, {'GMS_API_KEY': 'fixture', 'GMS_LLM_MODEL': 'gpt-4o-mini'}):
            llm = get_llm()
            self.assertFalse(llm.use_responses_api)
            self.assertEqual(llm.temperature, 0)
