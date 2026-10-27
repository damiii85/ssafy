@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3.11 -c "import sys" >nul 2>&1
if errorlevel 1 (
  echo Python 3.11이 필요합니다. 설치 후 다시 실행해 주세요.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3.11 -m venv .venv
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -c "import streamlit, chromadb, langgraph, langchain_openai" >nul 2>&1
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto :failed
)
if not exist ".env" copy /y .env.example .env >nul
".venv\Scripts\python.exe" scripts\verify_package.py
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m streamlit run app.py
goto :eof
:failed
echo 실행 준비에 실패했습니다. 위 오류 메시지를 확인해 주세요.
pause
exit /b 1
