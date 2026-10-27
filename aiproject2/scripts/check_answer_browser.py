"""실제 답변 카드·PDF·클립보드·반응형 스크롤 검증."""
import argparse
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright, expect
from bs4 import BeautifulSoup
from markdown_it import MarkdownIt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.services.pilot_report import load_spot_data

parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://localhost:8502')
args=parser.parse_args()
out=Path('data/processed/ui_preview');out.mkdir(parents=True,exist_ok=True)
stores, metadata=load_spot_data('suseongmot')
question='카페를 하고 싶어'
report={'competitor_count':int((stores.indsSclsNm=='카페').sum())}
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    context=browser.new_context(viewport={'width':1550,'height':1040},permissions=['clipboard-read','clipboard-write'],accept_downloads=True)
    page=context.new_page();page.goto(args.url)
    page.get_by_role('button',name='분석 시작하기').click()
    page.get_by_role('button',name='수성못',exact=True).click()
    prompt=page.get_by_placeholder('궁금한 내용을 자유롭게 질문해 주세요.')
    prompt.fill(question);prompt.press('Enter')
    card=page.locator('[class*="st-key-answer-card-"]')
    expect(card).to_have_count(1,timeout=30000)
    expect(card).to_contain_text('수성못 상권 요약')
    expect(card).to_contain_text(f"{report['competitor_count']:,}곳")
    expect(card).to_contain_text('참고 자료')
    expect(card.locator('.vega-embed')).to_have_count(1)
    avatars=page.locator('.st-key-chat-feed [data-testid^="stChatMessageAvatar"]')
    assert avatars.count() >= 2
    assert avatars.evaluate_all('els=>els.every(e=>getComputedStyle(e).display==="none")')
    basic=card.inner_text()
    for internal in ('pdf_statistics','pdf_chapter','stores_footfall_sales_residents','2026-06','2026-07'):
        assert internal not in basic, basic
    details=card.locator('details').filter(has=page.locator('summary',has_text='상세 근거 및 분석 기준'))
    assert not details.evaluate('e=>e.open')
    details.locator('summary').click()
    assert details.evaluate('e=>e.open')
    expect(details).to_contain_text('2026-06')
    expect(details).to_contain_text('2026-07')
    expect(details).to_contain_text('PDF 페이지:')
    expect(details).to_contain_text('창업 판단 전에 확인할 점')
    original_displayed=details.locator('[data-testid="stMarkdownContainer"]').last.inner_text()
    details.locator('summary').press('Enter')
    page.wait_for_function('e=>!e.open',arg=details.element_handle())
    page.get_by_role('button',name='답변 복사',exact=True).click()
    expect(page.get_by_role('status').filter(has_text='복사했습니다')).to_be_visible()
    copied=page.evaluate('navigator.clipboard.readText()')
    copied_displayed=BeautifulSoup(MarkdownIt().render(copied),'html.parser').get_text()
    assert ' '.join(copied_displayed.split())==' '.join(original_displayed.split())
    details.locator('summary').click()
    with page.expect_download() as download:
        card.get_by_role('button',name='PDF 다운로드').click()
    assert download.value.suggested_filename=='상권보고서.pdf'
    assert Path(download.value.path()).read_bytes().startswith(b'%PDF')
    page.screenshot(path=str(out/'25_answer_references.png'))
    if details.evaluate('e=>e.open'):
        details.locator('summary').click()
    page.wait_for_function('e=>!e.open',arg=details.element_handle())
    feed=page.locator('.st-key-chat-feed')
    feed.evaluate('(e)=>{const card=e.querySelector("[class*=st-key-answer-card-]");e.scrollTop+=card.getBoundingClientRect().top-e.getBoundingClientRect().top-12}')
    page.screenshot(path=str(out/'25_answer_desktop.png'))
    for width,height in [(1200,800),(390,844)]:
        page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(400)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert feed.evaluate('e=>e.scrollWidth<=e.clientWidth+1')
        composer=page.locator('.st-key-chat-composer').bounding_box()
        assert composer['y']+composer['height']<=height+1
        if width==390:
            feed.evaluate('(e)=>{const card=e.querySelector("[class*=st-key-answer-card-]");e.scrollTop+=card.getBoundingClientRect().top-e.getBoundingClientRect().top-8}')
            page.screenshot(path=str(out/'25_answer_mobile.png'))
    prompt.fill('100m 이내 카페는?');prompt.press('Enter')
    expect(card).to_have_count(2,timeout=30000)
    expect(card.last).to_contain_text('직선 반경 100m')
    prompt.fill('수성못의 유동인구는?');prompt.press('Enter')
    expect(card).to_have_count(3,timeout=30000)
    expect(card.last).to_contain_text('유동인구 분석')
    feed.evaluate('e=>e.scrollTop=e.scrollHeight')
    page.screenshot(path=str(out/'25_answer_pdf_metric.png'))
    assert page.locator('[data-testid="stException"]').count()==0
    browser.close()
print('Summary/legend, source dates, accessible accordion, exact answer copy, real PDF download, responsive overflow and PDF followup passed.')
