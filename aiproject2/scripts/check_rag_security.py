"""키 값을 출력하지 않는 환경·Git·소스 보안 점검."""
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from src.rag.settings import BASE_DIR

load_dotenv(BASE_DIR/'.env')
tracked=subprocess.run(['git','ls-files'],cwd=BASE_DIR,capture_output=True,text=True,check=True).stdout.splitlines()
secret_names=('GMS_API_KEY','PUBLIC_DATA_API_KEY','TAVILY_API_KEY')
values=[os.getenv(k,'') for k in secret_names if len(os.getenv(k,''))>8]
leaks=[]
source_paths=set(tracked)
for folder in ('src','scripts','tests','config','docs'):
    source_paths.update(str(path.relative_to(BASE_DIR)) for path in (BASE_DIR/folder).rglob('*') if path.is_file() and path.suffix in ('.py','.json','.md','.toml','.txt'))
for relative in source_paths:
    path=BASE_DIR/relative
    if path.is_file() and path.suffix in ('.py','.json','.md','.toml','.txt'):
        content=path.read_text(encoding='utf-8',errors='replace')
        if any(secret in content for secret in values):
            leaks.append(relative)
example=(BASE_DIR/'.env.example').read_text(encoding='utf-8')
filled=[line.split('=',1)[0] for line in example.splitlines() if '=' in line and not line.lstrip().startswith('#') and line.split('=',1)[1].strip()]
result={'key_configured':{name:bool(os.getenv(name)) for name in secret_names},
        'tracked_secret_files':[name for name in tracked if Path(name).name.startswith('.env') and Path(name).name!='.env.example'],
        'actual_secret_value_in_tracked_source':leaks,'env_example_filled_variable_names':filled,
        'env_ignored':subprocess.run(['git','check-ignore','.env'],cwd=BASE_DIR,capture_output=True).returncode==0}
path=BASE_DIR/'data/processed/rag_security.json'
path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(1 if result['tracked_secret_files'] or leaks or filled or not result['env_ignored'] else 0)
