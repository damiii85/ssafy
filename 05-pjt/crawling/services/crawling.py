import json
import re
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (TimeoutException,StaleElementReferenceException,)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / 'data'

MAIN_URL = 'https://www.tossinvest.com/'



# ------------------------------------------------------------
# 이전 실습에서 만든 함수 (수정 없이 그대로 사용)
# ------------------------------------------------------------
def crawl_comments(company_name, limit=20):
    company_name = company_name.strip()

    if not company_name:
        raise ValueError('회사명을 입력해주세요.')

    driver = get_driver()

    try:
        open_main(driver)
        search_company(driver, company_name)

        actual_company_name = get_actual_company_name(driver)
        stock_snapshot = get_stock_snapshot(driver)
        
        stock_code = get_stock_code(driver)
        open_community(driver, stock_code)
        comments = collect_comments(
            driver, limit=limit, max_scroll=100
        )
    finally:
        driver.quit()

    return {
        'company': actual_company_name,
        'stock_code': stock_code,
        'stock_snapshot': stock_snapshot,
        'collected_at': datetime.now().isoformat(timespec='seconds'),
        'count': len(comments),
        'comments': comments,
    }

def get_driver():
    """옵션을 적용한 크롬 브라우저를 실행해 돌려준다 (02_dynamic_page 와 같은 함수)"""
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return webdriver.Chrome(options=chrome_options)


def open_main(driver):
    """토스증권 메인 페이지에 접속하고, 화면이 그려질 때까지 기다린다"""
    driver.get(MAIN_URL)

    # 왼쪽 메뉴(#ts-lnb)는 자바스크립트가 화면을 그린 뒤에 나타나는 요소
    # 최대 10초 동안 반복 확인 -> 나타나는 순간 바로 다음 줄로 진행
    # 10초가 지나도 없으면 TimeoutException 발생
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '#ts-lnb'))
    )
    print('[접속] 토스증권 메인 페이지 로딩 완료')


POPUP_CLOSE_XPATH = (
    "//button[@aria-label='\uB2EB\uAE30' or @aria-label='Close' or @aria-label='close' "
    "or @title='\uB2EB\uAE30' or normalize-space(.)='\uB2EB\uAE30']"
    # Only click Confirm inside the specific informational tour in the screenshot.
    " | //*[normalize-space(.)='\uC885\uBAA9\uC744 \uB20C\uB7EC\uC11C \uB2E4\uB978 \uC885\uBAA9\uC73C\uB85C \uC774\uB3D9\uD558\uAE30']"
    "/ancestor::*[.//button[normalize-space(.)='\uD655\uC778']][1]"
    "//button[normalize-space(.)='\uD655\uC778']"
)


def close_popups(driver, wait_seconds=0):
    """Close explicit dismiss controls and the known stock-navigation tour."""
    deadline = time.monotonic() + max(0, wait_seconds)
    closed = 0
    while True:
        for button in driver.find_elements(By.XPATH, POPUP_CLOSE_XPATH):
            try:
                if not button.is_displayed() or not button.is_enabled():
                    continue
                try:
                    button.click()
                except ElementClickInterceptedException:
                    driver.execute_script('arguments[0].click();', button)
                closed += 1
            except StaleElementReferenceException:
                continue
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(0.2, remaining))
    if closed:
        print(f'[Popup] closed {closed}')
    return closed


def search_company(driver, company_name):
    """'/' 단축키로 검색창을 열고 회사명을 검색한다"""
    close_popups(driver, wait_seconds=1)

    # 단축키는 페이지 전체(body)에 포커스가 있어야 동작
    driver.execute_script('document.activeElement.blur(); document.body.focus();')
    ActionChains(driver).send_keys('/').perform()

    # 검색 모달 안의 입력창이 나타날 때까지 대기
    search_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.XPATH, "//input[@placeholder='검색어를 입력해주세요']")
        )
    )
    search_input.send_keys(company_name)
    search_input.send_keys(Keys.ENTER)
    print(f'[검색] {company_name}')

def parse_company_title(title):
    """Support the live price | company title and the older title format."""
    title = title.strip()
    if '|' in title:
        name = title.rsplit('|', 1)[1].strip()
        if name and name != '\uD1A0\uC2A4\uC99D\uAD8C':
            return name
    suffix = ' - \uD1A0\uC2A4\uC99D\uAD8C'
    if title.endswith(suffix):
        parts = title[:-len(suffix)].split(' - ')
        return parts[-1].strip()
    return None


def parse_stock_snapshot(title):
    """Use the source's signed daily rate, never infer it from comment sentiment."""
    prefix = title.split('|', 1)[0].strip()
    price = re.search(r'([0-9][0-9,]*(?:\.[0-9]+)?)\s*원', prefix)
    rate = re.search(r'([+−-]?[0-9]+(?:\.[0-9]+)?)\s*%', prefix)
    value = float(rate.group(1).replace('−', '-')) if rate else None
    # A nonzero unsigned rate does not unambiguously indicate direction.
    if rate and value != 0 and rate.group(1)[0] not in '+−-':
        value = None
    direction = ('unknown' if value is None else
                 'up' if value > 0 else 'down' if value < 0 else 'flat')
    return {'status': 'available' if value is not None else 'unavailable',
            'price': float(price.group(1).replace(',', '')) if price else None,
            'currency': 'KRW', 'change_percent': value, 'direction': direction,
            'basis': 'previous_close', 'source': '토스증권',
            'observed_at': datetime.now().astimezone().isoformat(timespec='seconds')}


def get_stock_snapshot(driver):
    snapshot = parse_stock_snapshot(driver.title)
    snapshot['source_url'] = driver.current_url
    return snapshot


def get_actual_company_name(driver):
    """Read the matched stock name without waiting for an obsolete title."""
    WebDriverWait(driver, 15).until(EC.url_contains('/order'))
    close_popups(driver, wait_seconds=1.2)
    name = WebDriverWait(driver, 10).until(
        lambda current: parse_company_title(current.title)
    )
    print(f'[Company] {name}')
    return name


def get_stock_code(driver):
    """검색 후 이동한 종목 페이지 주소에서 종목 코드를 꺼낸다"""
    # 검색이 끝나면 .../stocks/종목코드/order 로 이동 -> 주소가 바뀔 때까지 대기
    WebDriverWait(driver, 15).until(EC.url_contains('/order'))

    # 예) https://www.tossinvest.com/stocks/A005930/order
    #     split('/') -> [..., 'stocks', 'A005930', 'order']
    #     'stocks' 바로 다음 칸이 종목 코드
    parts = driver.current_url.split('/')
    stock_code = parts[parts.index('stocks') + 1]
    print(f'[종목 코드] {stock_code} ({driver.current_url})')
    return stock_code


def open_community(driver, stock_code):
    """Click the stock's community navigation tab, then verify its route."""
    community_url = f'https://www.tossinvest.com/stocks/{stock_code}/community'
    locator = (By.XPATH,
        "//button[@role='tab' and normalize-space(.)='\uCEE4\uBBA4\uB2C8\uD2F0']"
        " | //a[contains(@href, '/stocks/" + stock_code + "/community')]"
    )

    def click_tab(current):
        close_popups(current)
        for tab in current.find_elements(*locator):
            try:
                if tab.is_displayed() and tab.is_enabled():
                    current.execute_script('arguments[0].scrollIntoView({block: "center"});', tab)
                    tab.click()
                    return True
            except (StaleElementReferenceException, ElementClickInterceptedException):
                continue
        return False

    try:
        WebDriverWait(driver, 5, poll_frequency=0.2).until(click_tab)
        WebDriverWait(driver, 10).until(EC.url_contains(f'/stocks/{stock_code}/community'))
    except TimeoutException:
        print('[Community] tab navigation timed out; opening the community URL.')
        driver.get(community_url)
        WebDriverWait(driver, 10).until(EC.url_contains(f'/stocks/{stock_code}/community'))
    close_popups(driver, wait_seconds=1)
    print('[Community] navigation complete; waiting for comments.')


def save_json(data, file_path):
    """data 를 JSON 파일로 저장한다 (02_dynamic_page 와 같은 함수)"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'[저장] {file_path.name}')


# ------------------------------------------------------------
# [STEP 1] 안 깨지는 선택자로 보이는 댓글 읽기
# ------------------------------------------------------------
# 안 깨지는 선택자 고르기
#   개발자 도구에서 댓글을 클릭하면 이런 모양이 보입니다
#     <span class="tc3tm85" style="--fold-after-lines: 3">삼전 가즈아</span>
#
#   | 선택자 후보                          | 문제                                          |
#   | span.tc3tm85                         | 클래스 이름은 사이트를 새로 배포할 때마다 자동으로 바뀜 |
#   | span[style*='--fold-after-lines']    | "본문을 N줄까지만 보여주고 접기"라는 역할 => 본문에만 있음 |
#
#   => 화면에 보이는 "모양(클래스)"이 아니라 요소의 "역할(속성)"을 기준으로 골라야
#      디자인이 바뀌어도 코드가 잘 깨지지 않습니다
#
# [속성*='값'] : 속성 값에 '값'이 "포함"된 요소 (CSS 속성 선택자, 부록 참고)
#
# read_visible_comments(driver, comments)
#   - 화면에 보이는 댓글을 읽어 comments 리스트에 "추가"합니다
#   - 스크롤하면 이미 읽은 댓글도 다시 보이므로, 이미 있는 댓글은 건너뜁니다 (not in)
#   - 리스트는 함수 안에서 append 하면 바깥의 리스트도 함께 바뀝니다 (return 불필요)

COMMENT_SELECTOR = "span[style*='--fold-after-lines']"

def read_visible_comments(driver, comments):
    """지금 화면에 보이는 댓글을 comments 리스트에 추가한다 (중복 제외)"""
    close_popups(driver)
    for span in driver.find_elements(By.CSS_SELECTOR, COMMENT_SELECTOR):
        text = span.text.strip()
        if text and text not in comments:
            comments.append(text)


# ------------------------------------------------------------
# [STEP 2] 내부 스크롤 영역 찾기
# ------------------------------------------------------------
# 왜 필요할까?
#   - 댓글은 처음에 일부만 보이고, 아래로 스크롤해야 다음 댓글이 불러와집니다
#   - 그런데 이 페이지의 댓글 목록은 "페이지 전체"가 아니라,
#     화면 안의 "작은 스크롤 상자" 안에서 스크롤됩니다
#   - 그래서 페이지 전체를 스크롤하는 방법(window.scrollTo)으로는 새 댓글이 나오지 않습니다
#   => 이 스크롤 상자를 직접 찾아서 스크롤해야 합니다
#
# div[data-id^='base-ui-'][data-id$='-viewport']
#   - [속성^='값'] : 값으로 "시작"      => data-id 가 'base-ui-' 로 시작
#   - [속성$='값'] : 값으로 "끝남"      => data-id 가 '-viewport' 로 끝남
#   - 두 조건을 붙여 쓰면 AND           => 둘 다 만족하는 div
#   - 가운데 숫자(base-ui-r1-viewport 의 r1)는 바뀔 수 있어서 앞뒤만 고정했습니다
#
# 못 찾으면 None 을 돌려줍니다 => 스크롤 없이 화면에 보이는 댓글만 수집합니다

def find_scroll_container(driver):
    """댓글 본문을 감싸는 스크롤 가능한 부모 요소를 찾는다."""
    return driver.execute_script("""
        const comment = document.querySelector(
            "span[style*='--fold-after-lines']"
        );

        if (!comment) return null;

        let element = comment.parentElement;

        while (element) {
            const style = getComputedStyle(element);
            const canScroll = /auto|scroll|overlay/.test(style.overflowY);
            const hasOverflow =
                element.scrollHeight > element.clientHeight + 1;

            if (canScroll && hasOverflow) {
                return element;
            }

            element = element.parentElement;
        }

        return document.scrollingElement;
    """)

# ------------------------------------------------------------
# [STEP 3] 스크롤하며 댓글 모으기
# ------------------------------------------------------------
# 동작 순서
#   ① 첫 댓글이 나타날 때까지 기다린다 (못 찾으면 빈 리스트 반환)
#   ② 스크롤 상자를 찾는다
#   ③ 반복: 보이는 댓글 읽기 => 그만둘지 확인 => 스크롤 => 1.5초 대기
#
# 반복을 멈추는 조건 3가지 (무한 반복 방지)
#   - 목표 개수(limit) 만큼 모았을 때
#   - 스크롤 상자를 못 찾았을 때 (스크롤 불가)
#   - 스크롤했는데 댓글 개수가 5번 연속 그대로일 때 (더 불러올 댓글이 없음)
#   - 그리고 for 문 자체가 최대 max_scroll 번까지만 돕니다
#
# prev_count / stagnant_rounds
#   - prev_count      : 직전 반복에서의 댓글 개수 (처음에는 비교 대상이 없어 -1)
#   - stagnant_rounds : "개수가 그대로"였던 횟수. 늘어나면 0으로 초기화
#
# scroll_container.click() => send_keys(Keys.END)
#   - 스크롤 상자를 클릭해 포커스를 준 뒤, 키보드 End 키로 상자의 맨 아래로 이동합니다
#   - 맨 아래에 닿으면 사이트가 다음 댓글을 불러옵니다
#   - time.sleep(1.5) : 새 댓글을 불러오는 데 걸리는 시간 (여기서는 기다릴 "요소"가 없어 sleep 사용)
#
# comments[:limit] : 마지막 스크롤에서 limit 보다 많이 모일 수 있어 정확히 잘라서 돌려줍니다

def collect_comments(driver, limit=20, max_scroll=30):
    """스크롤을 반복하며 댓글을 최대 limit 개까지 모아 돌려준다"""
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, COMMENT_SELECTOR))
        )
    except TimeoutException:
        print('[수집] 댓글을 찾지 못했습니다. 선택자가 바뀌었는지 확인하세요.')
        return []

    scroll_container = find_scroll_container(driver)
    comments = []
    prev_count = -1  # 직전 반복의 댓글 개수
    stagnant_rounds = 0  # 댓글 개수가 그대로인 횟수

    for scroll in range(max_scroll):
        try:
            read_visible_comments(driver, comments)
        except StaleElementReferenceException:
            continue
        print(f'[수집] 스크롤 {scroll + 1}회 -> 누적 {len(comments)}개')

        if len(comments) >= limit or scroll_container is None:
            break

        if len(comments) == prev_count:
            stagnant_rounds += 1
            if stagnant_rounds >= 5:
                break
        else:
            stagnant_rounds = 0
        prev_count = len(comments)

        for attempt in range(3):
            try:
                scroll_container = find_scroll_container(driver)

                if scroll_container is None:
                    print('[수집 중단] 댓글 스크롤 영역을 찾지 못했습니다.')
                    return comments[:limit]

                before, after, height, viewport = driver.execute_script("""
                    const element = arguments[0];
                    const before = element.scrollTop;

                    element.scrollTop += element.clientHeight * 0.8;

                    return [
                        before,
                        element.scrollTop,
                        element.scrollHeight,
                        element.clientHeight
                    ];
                """, scroll_container)

                print(
                    f'[스크롤] 위치 {before:.0f} → {after:.0f} '
                    f'/ 전체 높이 {height}, 화면 높이 {viewport}'
                )
                break

            except StaleElementReferenceException:
                if attempt == 2:
                    print('[수집 중단] 스크롤 요소가 계속 변경됩니다.')
                    return comments[:limit]

                time.sleep(0.5)

        # Read on each poll: handle both appended lists and virtualized lists.
        count_before_wait = len(comments)

        def new_comments_loaded(current_driver):
            try:
                read_visible_comments(current_driver, comments)
            except StaleElementReferenceException:
                return False
            return len(comments) > count_before_wait

        try:
            WebDriverWait(driver, 5, poll_frequency=0.2).until(new_comments_loaded)
        except TimeoutException:
            pass
    return comments[:limit]


# ------------------------------------------------------------
# [STEP 4] 실행하고 파일로 저장하기
# ------------------------------------------------------------
# 수집이 끝나면 브라우저는 필요 없으므로 finally 에서 바로 종료하고,
# 그다음 파일 저장과 출력을 합니다
#
# 저장 형식 : 댓글만이 아니라 "언제, 어느 회사"의 댓글인지 함께 저장합니다
#   - 커뮤니티 댓글은 실시간으로 바뀝니다. 지금 수집한 20개는 1시간 뒤와 다릅니다
#   - collected_at 이 있으면 나중에 "이 결과가 언제 데이터였는지" 알 수 있습니다
#   - datetime.now().isoformat(timespec='seconds') => '2026-10-22T10:30:00' 형태
#
# 확인 포인트t
#   - 스크롤 몇 회 만에 20개가 모였나요?
#   - data/comments_raw.json 을 열어 보세요. 수집한 댓글에 어떤 "정리가 필요한" 부분이 보이나요?
#     (특수문자, 이모티콘, 너무 짧은 글, 부적절한 표현 등 => 다음 전처리 단계의 대상)
if __name__ == '__main__':
    company_name = input('검색할 회사명을 입력하세요: ')
    result = crawl_comments(company_name, limit=20 )
    save_json(result, DATA_DIR / 'comments_raw.json')
    print(result)



