"""지역 카드 정렬·검색·전체 클릭·반응형·주소 기준 채팅 실제 브라우저 검증."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://localhost:8502')
args = parser.parse_args()
out = Path('data/processed/ui_preview')
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', headless=True)
    page = browser.new_page(viewport={'width':1440,'height':900})
    page.goto(args.url)
    page.get_by_role('button',name='분석 시작하기',exact=True).click()
    search = page.get_by_role('textbox', name='지역 검색')
    search.wait_for()
    cards = page.locator('.st-key-region-grid [class*="st-key-spot-card-"]')
    expect(cards).to_have_count(5)
    for width,height,columns,label in [(1440,900,3,'desktop'),(820,1050,2,'tablet'),(390,844,1,'mobile')]:
        page.set_viewport_size({'width':width,'height':height})
        page.wait_for_timeout(300)
        boxes = [card.bounding_box() for card in cards.all()]
        assert len({round(b['width']) for b in boxes})==1,boxes
        assert len({round(b['height']) for b in boxes})==1,boxes
        assert abs(boxes[0]['y']-boxes[columns-1]['y'])<2
        assert boxes[columns]['y']>boxes[0]['y']+boxes[0]['height']
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert 52<=search.locator('..').bounding_box()['height']<=56
        if columns==3:
            assert page.get_by_role('button',name='처음으로',exact=True).bounding_box()['y']<height
        page.screenshot(path=str(out/f'17_region_{label}.png'),full_page=True)
    search.fill('반월당');search.press('Enter')
    expect(cards).to_have_count(1)
    expect(page.get_by_role('button',name='대구 도심 통합상권',exact=True)).to_be_visible()
    search.fill('없는 지역');search.press('Enter')
    expect(cards).to_have_count(0)
    expect(page.get_by_text('현재 지원하는 다섯 지역에서 선택해 주세요.')).to_be_visible()
    search.fill('');search.press('Enter')
    expect(cards).to_have_count(5)
    # 버튼 문구가 아닌 카드 모서리도 선택 가능해야 한다.
    cards.first.click(position={'x':8,'y':8})
    prompt=page.get_by_placeholder('궁금한 내용을 자유롭게 질문해 주세요.')
    prompt.wait_for()
    prompt.fill('대구광역시 중구 중앙대로 412-21 100m 카페');prompt.press('Enter')
    expect(page.locator('.st-key-chat-feed')).to_contain_text('중앙대로 412-21',timeout=30000)
    expect(page.locator('.st-key-chat-feed')).to_contain_text('주소별 등록 좌표',timeout=30000)
    prompt.fill('50m 이내는?');prompt.press('Enter')
    expect(page.locator('.st-key-chat-feed')).to_contain_text('직선 반경 50m',timeout=30000)
    assert page.locator('[data-testid="stException"]').count()==0
    page.set_viewport_size({'width':1440,'height':900})
    page.wait_for_timeout(500)
    page.screenshot(path=str(out/'17_address_chat.png'))
    page.get_by_role('button',name='새 대화하기',exact=True).click()
    page.get_by_role('button',name='처음으로',exact=True).click()
    expect(page.get_by_role('button',name='분석 시작하기',exact=True)).to_be_visible()
    page.get_by_role('button',name='서비스 소개',exact=True).click()
    expect(page.get_by_text('대구 다섯 지역의 상가 정보와 보고서를 함께 살펴보는 상권 분석 서비스입니다.')).to_be_visible()
    browser.close()
print('Region grid, responsive cards, search, whole-card navigation, address radius followup and home/header passed.')
