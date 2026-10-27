"""지역 대시보드의 실제 Edge 데스크톱/모바일 검증."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--url',default='http://localhost:8501')
args = parser.parse_args()
output = Path('data/processed/ui_preview')
output.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    page = browser.new_page(viewport={'width':1550,'height':1040},device_scale_factor=1)
    page.goto(args.url,wait_until='networkidle')
    page.get_by_role('button',name='분석 시작하기',exact=True).wait_for()
    page.screenshot(path=str(output/'15_home.png'),full_page=True)
    assert page.locator('.st-key-hero').evaluate("e=>getComputedStyle(e).backgroundImage.includes('data:image/png;base64,')")
    page.get_by_role('button',name='분석 시작하기',exact=True).click()
    page.get_by_role('button',name='대구 도심 통합상권',exact=True).click()
    prompt = page.get_by_placeholder('궁금한 내용을 자유롭게 질문해 주세요.')
    prompt.wait_for()
    page.screenshot(path=str(output/'15_dashboard_empty.png'),full_page=True)
    page.get_by_role('button',name='카페',exact=True).click()
    page.get_by_text('627곳',exact=False).first.wait_for(timeout=30000)
    page.locator('.vega-embed').first.wait_for(timeout=30000)
    page.wait_for_timeout(1500)
    page.screenshot(path=str(output/'15_downtown_union.png'),full_page=True)
    assert page.get_by_role('button',name='위치 수정',exact=True).count()==0
    prompt.fill('100미터 이내 유사 업계는?')
    prompt.press('Enter')
    page.get_by_text('19곳',exact=True).first.wait_for(timeout=30000)
    page.screenshot(path=str(output/'15_radius_100m.png'),full_page=True)
    assert page.get_by_text('입지 탐색 후보',exact=False).count()==0
    prompt.fill('200m 이내는?')
    prompt.press('Enter')
    page.get_by_text('42곳',exact=True).first.wait_for(timeout=30000)
    page.screenshot(path=str(output/'15_radius_200m.png'),full_page=True)
    prompt.fill('반월당의 유동인구는 몇 명이야?')
    prompt.press('Enter')
    page.get_by_text('18,012명/일',exact=False).filter(visible=True).last.wait_for(timeout=30000)
    page.screenshot(path=str(output/'15_subregion_pdf.png'),full_page=True)
    assert page.locator('[data-testid="stException"]').count()==0
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'),'Desktop horizontal overflow'
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_timeout(900)
    page.screenshot(path=str(output/'15_mobile_dashboard.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'),'Mobile horizontal overflow'
    page.goto(args.url,wait_until='networkidle')
    page.get_by_role('button',name='분석 시작하기',exact=True).wait_for()
    page.screenshot(path=str(output/'15_mobile_home.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'),'Mobile home overflow'
    print('Revised regions, deduplicated downtown, requested 100m/200m counts, new PDF and responsive layouts passed.')
    browser.close()
