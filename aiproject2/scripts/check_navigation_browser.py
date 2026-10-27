"""Check that selection cards never remain visible behind the chat screen."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', headless=True)
    page = browser.new_page(viewport={'width': 1400, 'height': 960})
    page.goto('http://localhost:8501')
    page.locator('.st-key-start button').click()
    expect(page.locator('[class*="st-key-spot-card-"]')).to_have_count(5)
    page.evaluate('''() => {
        window.mixedFrames = 0;
        const visible = e => e.getBoundingClientRect().height > 0 && getComputedStyle(e).visibility !== 'hidden';
        const check = () => {
            const chat = document.querySelector('.st-key-conversation-panel');
            const cards = [...document.querySelectorAll('[class*="st-key-spot-card-"]')];
            if (chat && visible(chat) && cards.some(visible)) window.mixedFrames++;
            window.navigationCheck = requestAnimationFrame(check);
        };
        check();
    }''')
    for region in ['suseongmot', 'samdeok', 'daegu_downtown']:
        page.locator('.st-key-select_' + region + ' button').click()
        expect(page.get_by_placeholder('궁금한 내용을 자유롭게 질문해 주세요.')).to_be_visible()
        expect(page.locator('[class*="st-key-spot-card-"]')).to_have_count(0)
        expect(page.locator('[data-testid="stException"]')).to_have_count(0)
        page.wait_for_timeout(300)
        assert page.evaluate('window.mixedFrames') == 0
        page.locator('.st-key-new_chat button').click()
        expect(page.locator('[class*="st-key-spot-card-"]')).to_have_count(5)
    page.locator('.st-key-select_chilgok3 button').click()
    expect(page.locator('.st-key-chat-feed')).to_be_visible()
    page.set_viewport_size({'width': 390, 'height': 844})
    expect(page.get_by_placeholder('궁금한 내용을 자유롭게 질문해 주세요.')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    out=Path('data/processed/ui_preview'); out.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(out/'clean_navigation_mobile.png'))
    print('Verified: repeated region/chat transitions, no mixed frames, mobile input visible')
    browser.close()
