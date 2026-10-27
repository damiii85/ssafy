"""Build a runnable whole-project ZIP, excluding credentials and local environments."""
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile
from dotenv import load_dotenv

BASE=Path(__file__).resolve().parents[1]

def main():
    load_dotenv(BASE/'.env')
    secrets=[os.getenv(k,'').encode() for k in ('GMS_API_KEY','PUBLIC_DATA_API_KEY','TAVILY_API_KEY','NAVER_MAP_CLIENT_ID') if len(os.getenv(k,''))>8]
    paths=[]
    for folder in ('src','scripts','tests','assets','config','.streamlit','docs','output'):
        paths.extend(p for p in (BASE/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.startswith('~$') and p.suffix not in ('.pyc','.log'))
    paths.extend(BASE/name for name in ('app.py','README.md','requirements.txt','.env.example','.gitignore','실행.bat'))
    raw=BASE/'data/raw'
    paths.extend(p for p in (raw/'spots').rglob('*') if p.is_file() and p.name in ('stores.csv','metadata.json'))
    paths.extend(raw/name for name in ('dongseongro_stores.csv','collection_metadata.json','daegu_bus_stops.json','daegu_subway_ridership.csv'))
    paths.extend(p for p in (BASE/'data/processed').glob('*.csv'))
    paths.extend(BASE/'data/processed'/name for name in ('unit_test_results.json','luna_verification.json','live_acceptance.json','rag_security.json'))
    paths.extend(BASE/'data/reports'/name for name in ('상권보고서.pdf','active_report.source.json'))
    paths.extend(BASE/'db'/name for name in ('portable_vectors.json.gz','inventory.json','README.md'))
    paths=sorted(set(p for p in paths if p.is_file()))
    required=[BASE/'db/portable_vectors.json.gz',BASE/'실행.bat',BASE/'output/검증결과.md',BASE/'data/reports/상권보고서.pdf']
    assert all(p in paths for p in required),'Missing essential submission files'
    manifest=[]
    for p in paths:
        body=p.read_bytes()
        assert not any(key in body for key in secrets),'Actual credential found; contents withheld'
        manifest.append({'path':p.relative_to(BASE).as_posix(),'sha256':hashlib.sha256(body).hexdigest()})
    destination=BASE/'data/processed/submission/SPOT_CHECK_제출용.zip'
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,'aiproject2/'+p.relative_to(BASE).as_posix())
        z.writestr('aiproject2/SUBMISSION_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(destination) as z:
        assert z.testzip() is None
        assert not any('/.env' in name and not name.endswith('/.env.example') for name in z.namelist())
        assert not any('/.venv/' in n or '/venv/' in n or '/.git/' in n or '/.archive/' in n for n in z.namelist())
    print('Created:',destination)
    print('Files:',len(paths),'bytes:',destination.stat().st_size,'actual secrets: 0')

if __name__=='__main__':main()
