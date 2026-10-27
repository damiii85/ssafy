"""Verify chat feedback against the local tests/fixtures/chat_feedback_app.py server."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

out = Path('data/processed/ui_preview')
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', headless=True)
    page = browser.new_page(viewport={'width': 1550, 'height': 1040})
    page.goto('http://localhost:8502')
    page.get_by_role('button', name='분석 시작하기').click()
    page.get_by_role('button', name='수성못', exact=True).click()
    feed = page.locator('.st-key-chat-feed')
    prompt = page.get_by_placeholder('궁금한 내용을 자유롭게 질문해 주세요.')
    prompt.fill('내 메시지가 먼저 보여야 합니다')
    focused = page.locator('[data-testid="stChatInput"]')
    assert focused.evaluate('e=>getComputedStyle(e).borderTopWidth') == '0px'
    assert focused.evaluate('e=>getComputedStyle(e).boxShadow') == 'none'
    assert focused.evaluate('e=>[...e.children].every(x=>getComputedStyle(x).borderTopWidth==="0px" && getComputedStyle(x).outlineStyle==="none")')
    prompt.press('Enter')
    user = feed.locator('[data-testid="stChatMessage"]').filter(has_text='내 메시지가 먼저 보여야 합니다')
    loading = feed.locator('[data-testid="stChatMessage"]').filter(has_text='답변을 준비하고 있어요')
    expect(user).to_be_visible(timeout=4000)
    expect(loading).to_be_visible(timeout=4000)
    expect(feed.get_by_text('화면 확인용 답변입니다.', exact=True)).to_have_count(0)
    ub, lb = user.bounding_box(), loading.bounding_box()
    assert ub['x'] > lb['x'], (ub, lb)
    assert ub['y'] + ub['height'] <= lb['y'], (ub, lb)
    page.screenshot(path=str(out / 'chat_user_and_loading.png'))
    expect(feed.get_by_text('화면 확인용 답변입니다.', exact=True).first).to_be_visible(timeout=20000)
    expect(feed.get_by_text('답변을 준비하고 있어요', exact=True)).to_have_count(0)
    expect(user).to_have_count(1)
    expect(feed.locator('[data-testid="stChatMessage"]')).to_have_count(3)
    page.screenshot(path=str(out / 'chat_answer_complete.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    expect(prompt).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    browser.close()
print('Verified: user visible before answer, right/left alignment, loading replaced, no duplicate, focus border removed, mobile width')
