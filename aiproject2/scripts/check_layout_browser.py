"""실제 브라우저에서 패널 높이·독립 스크롤·입력·반응형 전환 검증."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://localhost:8502')
args=parser.parse_args()
out=Path('data/processed/ui_preview');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    page=browser.new_page(viewport={'width':1550,'height':900})
    page.goto(args.url)
    page.get_by_role('button',name='분석 시작하기').click()
    page.get_by_role('button',name='대구 도심 통합상권',exact=True).click()
    prompt=page.get_by_placeholder('궁금한 내용을 자유롭게 질문해 주세요.')
    prompt.wait_for()
    page.wait_for_timeout(1200)
    def rect(selector):
        return page.locator(selector).bounding_box()
    def fits():
        assert page.locator('[data-testid="stException"]').count()==0
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        r=rect('.st-key-chat-composer')
        assert r['y']+r['height']<=page.viewport_size['height']+1,r
    def panels():
        boxes=[rect('.st-key-'+k) for k in ['conversation-nav','conversation-panel','insights-panel']]
        assert max(b['y'] for b in boxes)-min(b['y'] for b in boxes)<2,boxes
        assert max(b['height'] for b in boxes)-min(b['height'] for b in boxes)<3,boxes
        fits()
    panels()
    page.screenshot(path=str(out/'16_desktop_empty.png'))
    page.get_by_role('button',name='카페',exact=True).click()
    page.get_by_text('627곳',exact=False).first.wait_for()
    for text,expected in [('100미터 이내 유사 업계는?','19곳'),('200m 이내는?','42곳'),('반월당의 유동인구는 몇 명이야?','18,012명/일')]:
        prompt.fill(text);prompt.press('Enter')
        page.get_by_text(expected,exact=False).filter(visible=True).last.wait_for(timeout=30000)
    page.wait_for_timeout(1200)
    panels()
    feed=page.locator('.st-key-chat-feed')
    assert feed.evaluate('e=>e.scrollHeight>e.clientHeight+100')
    before=rect('.st-key-chat-composer')
    right_before=rect('.st-key-insights-panel')
    feed.evaluate('e=>e.scrollTop=0')
    assert rect('.st-key-chat-composer')==before
    assert rect('.st-key-insights-panel')==right_before
    right=page.locator('.st-key-insights-panel')
    assert right.evaluate('e=>e.scrollHeight>e.clientHeight')
    right.evaluate('e=>e.scrollTop=e.scrollHeight')
    assert rect('.st-key-chat-composer')==before
    users=page.locator('[data-testid="stChatMessage"]:has([aria-label="Chat message from user"])')
    assert users.count()==4
    user=users.first.bounding_box();ai=page.locator('[data-testid="stChatMessage"]').first.bounding_box()
    assert user['x']>ai['x']+30,(user,ai)
    assert user['width']<feed.bounding_box()['width']*.85
    page.screenshot(path=str(out/'16_desktop_layout.png'))
    for width,height in [(1280,720),(1024,800),(390,844)]:
        page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(500)
        fits()
        if width==1024:
            page.locator('.st-key-workspace_view').get_by_text('대화 목록',exact=True).click()
            page.get_by_role('button',name='새 대화하기').wait_for(state='visible')
            assert right.is_visible()
            page.locator('.st-key-workspace_view').get_by_text('채팅',exact=True).click()
            prompt.wait_for(state='visible')
        if width<900:
            assert page.locator('.st-key-conversation-panel').is_visible()
            assert not right.is_visible()
            page.locator('.st-key-workspace_view').get_by_text('분석',exact=True).click()
            right.wait_for(state='visible')
            assert not page.locator('.st-key-conversation-panel').is_visible()
            page.screenshot(path=str(out/'16_mobile_analysis.png'))
            page.locator('.st-key-workspace_view').get_by_text('대화 목록',exact=True).click()
            page.get_by_role('button',name='새 대화하기').wait_for(state='visible')
            page.locator('.st-key-workspace_view').get_by_text('채팅',exact=True).click()
            prompt.wait_for(state='visible')
            assert users.count()==4
            prompt.fill('긴 질문입니다. '*150)
            fits()
            prompt.fill('')
            page.screenshot(path=str(out/'16_mobile_chat.png'))
            page.locator('.st-key-workspace_view').get_by_text('대화 목록',exact=True).click()
            page.get_by_role('button',name='새 대화하기').click()
            page.get_by_role('button',name='대구 도심 통합상권',exact=True).click()
            # 지역 선택 후에는 모바일 기본 화면이 채팅으로 돌아간다.
            page.locator('.st-key-workspace_view').get_by_text('대화 목록',exact=True).click()
            page.locator('.st-key-archive_0 button').click()
            # 복원 rerun이 완료되기 전에 탭 전환 이벤트로 중단하지 않는다.
            expect(users).to_have_count(4,timeout=10000)
            page.locator('.st-key-workspace_view').get_by_text('채팅',exact=True).click()
            prompt.wait_for(state='visible')
            expect(users).to_have_count(4,timeout=10000)
    browser.close()
print('Desktop/medium/mobile layout, independent scroll, fixed composer, message alignment and preserved conversation passed.')
