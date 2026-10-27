"""Local delayed response for checking the pending chat UI without API calls."""
import os
import runpy
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
os.environ['SPOTCHECK_RAG_OFFLINE'] = '1'
import src.services.chat_controller as controller


def delayed_answer(*args, progress=None, **kwargs):
    if progress:
        progress('답변을 준비하고 있어요')
    time.sleep(6)
    return '화면 확인용 답변입니다.', None


controller.answer_question = delayed_answer
runpy.run_path(str(BASE / 'app.py'), run_name='__main__')
