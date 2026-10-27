"""외부 호출 없이 단위·회귀 테스트. 실서비스 검증은 verify_rag.py로 별도 실행."""
import os
from pathlib import Path
import sys
import unittest
import json
import time

base=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(base))
os.environ['SPOTCHECK_RAG_OFFLINE']='1'
suite=unittest.defaultTestLoader.discover(str(base/'tests'))
started=time.perf_counter()
result=unittest.TextTestRunner(verbosity=2).run(suite)
report={'tests':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
        'failures':[test.id() for test,_ in result.failures],'errors':[test.id() for test,_ in result.errors],
        'skipped':[test.id() for test,_ in result.skipped],'elapsed_seconds':round(time.perf_counter()-started,3),
        'external_api_calls':'disabled; model fixtures and local real Chroma/LangGraph tests'}
output=base/'data/processed/unit_test_results.json'
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
raise SystemExit(0 if result.wasSuccessful() else 1)
