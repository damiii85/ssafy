"""Extract the submission and exercise it without original files or credentials."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil
import zipfile

BASE=Path(__file__).resolve().parents[1]
archive=BASE/'data/processed/submission/SPOT_CHECK_제출용.zip'
target=Path(tempfile.mkdtemp(prefix='submission_check_',dir=BASE/'data/processed'))
with zipfile.ZipFile(archive) as z:
    for name in z.namelist():
        assert (target/name).resolve().is_relative_to(target.resolve())
    z.extractall(target)
project=target/'aiproject2'
manifest=json.loads((project/'SUBMISSION_MANIFEST.json').read_text(encoding='utf-8'))
for entry in manifest:
    assert hashlib.sha256((project/entry['path']).read_bytes()).hexdigest()==entry['sha256']
assert not (project/'.env').exists()
environment=dict(os.environ,GMS_API_KEY='',PUBLIC_DATA_API_KEY='',NAVER_MAP_CLIENT_ID='',TAVILY_API_KEY='',
    SPOTCHECK_RAG_OFFLINE='1',SPOTCHECK_VECTOR_CACHE=str(target/'fresh_vector_cache'))
code='''
import json,runpy
from pathlib import Path
runpy.run_path('scripts/verify_package.py',run_name='__main__')
from src.services.pilot_report import load_spot_data
from src.services.spot_catalog import load_spots
from src.services.chat_controller import answer_question
from streamlit.testing.v1 import AppTest
counts={s['id']:len(load_spot_data(s['id'])[0]) for s in load_spots()}
data,meta=load_spot_data('suseongmot');session={}
text,report=answer_question('suseongmot','카페를 하고 싶어',session,data,meta,1000)
assert report['competitor_count']==95 and report['total_stores']==2106
assert session['rag_last']['trace']['rag1_count'] and session['rag_last']['trace']['rag2_count']
assert not session['rag_last']['statuses'],session['rag_last']['statuses']
text,_=answer_question('suseongmot','오늘 실시간 임대료는?',{},data,meta,1000)
assert '알 수 없습니다' in text
data,meta=load_spot_data('daegu_downtown')
text,report=answer_question('daegu_downtown','중앙대로 412-21 100m 카페',{},data,meta,1000)
assert report['competitor_count']==19
app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30).run()
app.button(key='start').click().run()
app.button(key='select_suseongmot').click().run()
app.chat_input[0].set_value('카페를 하고 싶어').run()
assert not app.exception
assert app.session_state['spot_sessions']['suseongmot']['reports'][-1]['competitor_count']==95
Path('extraction_check.json').write_text(json.dumps({'regions':counts,'cafe_count':95,'address_100m_cafes':19,'two_collections':True,'app_test':True,'keys_present':False,'network_model_calls':False}),encoding='utf-8')
print('Extracted application and both collections verified without API keys')
'''
result=subprocess.run([sys.executable,'-c',code],cwd=project,env=environment,capture_output=True,text=True,timeout=150)
if result.returncode:
    print(result.stdout)
    print(result.stderr[-5000:])
    raise SystemExit(result.returncode)
archived=BASE/'.archive/submission_checks'/target.name
assert target.resolve().is_relative_to(BASE/'data/processed')
assert archived.resolve().is_relative_to(BASE/'.archive')
archived.parent.mkdir(parents=True,exist_ok=True)
shutil.move(str(target),str(archived))
project=archived/'aiproject2'
record=json.loads((project/'extraction_check.json').read_text(encoding='utf-8'))
record.update(zip_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),zip_bytes=archive.stat().st_size,
    extracted_project=str(project),fresh_vector_cache=True,manifest_files=len(manifest),mode='local; no keys or original data paths',
    dependencies='Existing validated Python 3.11 environment used; data/code loaded only from extracted ZIP')
(BASE/'data/processed/submission_validation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False))
