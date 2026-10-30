"""
전처리 ① LLM으로 부적절한 댓글 제거하기

학습 목표
  1. LLM 에게 "판단"만 맡기고, 제거는 코드가 직접 한다
  2. LLM 응답을 그대로 믿지 않고 형식·값을 검증한 뒤 사용한다
  3. 여러 항목을 번호로 지울 때 뒤에서부터 지워야 하는 이유를 이해한다
  4. 판단 기준에 따라 LLM 의 결과가 달라지는 것을 비교하고, 사용할 기준은 사람이 정한다

전체 흐름
  수집(comments_raw.json) => [부적절 제거] => 정제 => 증강

입력 : data/comments_raw.json (없으면 data/comments_sample.json)
출력 : data/comments_filtered.json

준비 : .env.example 을 복사해 .env 로 이름을 바꾸고 GMS_KEY 를 입력

진행 방법
  - 미리 준비된 함수(이전 실습 함수, 동작 과정 시각화)는 완성되어 있습니다. 읽어 보기만 하세요
  - [STEP 1]부터 순서대로 코드 블록을 선택하고 Ctrl + / 로 주석을 해제합니다
  - 함수 정의 STEP 은 해제해도 출력이 없습니다. 마지막 STEP(실행)까지 해제해야 동작합니다
  - LLM 응답은 실행할 때마다 조금씩 달라질 수 있습니다
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / 'data'

# .env 파일의 값(GMS_KEY, GMS_BASE_URL, MODEL)을 환경 변수로 불러옴
load_dotenv(BASE_DIR.parent.parent / '.env')


# ------------------------------------------------------------
# 이전 실습에서 만든 함수 (수정 없이 그대로 사용)
# ------------------------------------------------------------


def load_json(file_path):
    """JSON 파일을 읽어 파이썬 객체(딕셔너리·리스트)로 돌려준다"""
    with open(file_path, encoding='utf-8') as f:
        return json.load(f)


def save_json(data, file_path):
    """data 를 JSON 파일로 저장한다"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'[저장] {file_path.name}')


# ------------------------------------------------------------
# 동작 과정 시각화 (완성 코드, 수정 없이 그대로 사용)
# ------------------------------------------------------------


def show_criteria_comparison(comments, results):
    """기준별로 어떤 댓글이 제거되었는지 표로 나란히 출력한다 (O = 제거)"""
    names = list(results)
    removed_sets = {name: set(results[name][1]) for name in names}

    print('\n[기준 비교] O = 제거됨')
    print('  ' + ' | '.join(f'{name:^6}' for name in names) + ' | 댓글')
    for comment in comments:
        marks = ['O' if comment in removed_sets[name] else '-' for name in names]
        if 'O' in marks:  # 어느 기준에서든 제거된 댓글만 출력
            text = comment.replace('\n', ' ')[:40]
            print('  ' + ' | '.join(f'{m:^6}' for m in marks) + ' | ' + text)
    for name in names:
        print(f'  {name} : {len(results[name][1])}개 제거')


# ------------------------------------------------------------
# [STEP 1] 수집 결과 불러오기
# ------------------------------------------------------------
# 03_toss_comments/05_collect_comments.py 가 저장한 파일을 읽어서 시작합니다
#   => 전처리를 여러 번 다시 실행해도 토스증권에 다시 접속하지 않습니다
#
# 수집에 실패했거나(사이트 구조 변경 등) 파일이 없으면
#   data/comments_sample.json (미리 수집해 둔 20개)으로 대신 진행합니다
#
# raw_path.exists() : 그 경로에 파일이 실제로 있으면 True

def load_raw_comments():
    """수집 결과(comments_raw.json)를 읽는다. 없으면 샘플 데이터를 대신 사용"""
    raw_path = DATA_DIR / 'comments_raw.json'
    if not raw_path.exists():
        print('[안내] comments_raw.json 이 없어 comments_sample.json 으로 진행합니다.')
        raw_path = DATA_DIR / 'comments_sample.json'
    return load_json(raw_path)


# ------------------------------------------------------------
# [STEP 2] LLM 호출 함수
# ------------------------------------------------------------
# 관통 02 에서 사용한 GMS 호출과 같은 방식입니다
#
# .env 파일 (코드에 비밀 키를 직접 적지 않기 위해 따로 보관)
#   GMS_KEY      : GMS 접속 키
#   GMS_BASE_URL : GMS 주소 (OpenAI 형식의 요청을 받아 주는 주소)
#   MODEL        : 사용할 모델 이름
#   => 파일 위쪽의 load_dotenv(...) 가 .env 를 읽어 os.getenv('이름') 으로 꺼낼 수 있게 합니다
#
# client.responses.create(model=..., input=prompt)
#   - OpenAI 의 Responses API 로 요청을 보냅니다
#   - input : LLM 에게 보낼 내용 (여기서는 우리가 만든 프롬프트 문자열)
#
# response.output_text
#   - 응답 객체 안에는 텍스트 외에도 여러 정보(모델 이름, 사용량 등)가 들어 있습니다
#   - output_text 는 그중 "LLM 이 쓴 글자"만 하나의 문자열로 모아 둔 값입니다

def run_llm(prompt):
    """prompt 를 LLM 에 보내고 응답 텍스트를 돌려준다"""
    required = ('GMS_KEY', 'GMS_BASE_URL', 'MODEL')
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise ValueError('Missing environment variables: ' + ', '.join(missing))

    client = OpenAI(api_key=os.getenv('GMS_KEY'), base_url=os.getenv('GMS_BASE_URL'))

    response = client.responses.create(
        model=os.getenv('MODEL'),
        input=prompt,
    )
    return response.output_text


# ------------------------------------------------------------
# [STEP 3] LLM 응답에서 JSON 배열 꺼내기
# ------------------------------------------------------------
# LLM 응답은 "글자(문자열)"입니다. '[0, 2, 5]' 도 아직 리스트가 아니라 글자입니다
#   json.loads('[0, 2, 5]') => [0, 2, 5]  (진짜 파이썬 리스트)
#
# LLM 응답을 그대로 믿으면 안 되는 이유
#   - "배열만 반환해" 라고 지시해도 ```json [0, 2] ``` 처럼 코드블럭으로 감싸 오기도 합니다
#   - 설명 문장을 붙이거나, 형식이 깨진 응답을 보낼 수도 있습니다
#   => 코드블럭은 벗겨내고, 그래도 형식이 틀리면 프로그램을 멈추지 않고 None 을 돌려줍니다
#
# try / except json.JSONDecodeError
#   - json.loads 가 JSON 이 아닌 글자를 받으면 JSONDecodeError 를 냅니다
#   - except 로 받아서 "실패했다"는 안내만 출력하고 None 을 돌려줍니다
#
# text.strip('`').removeprefix('json')
#   - 양 끝의 ` 문자를 모두 지우고, 앞에 붙은 'json' 글자를 떼어냅니다
#   - '```json\n[0, 2]\n```' => '\n[0, 2]\n' => strip() => '[0, 2]'
#
# isinstance(data, list) : data 가 리스트인지 확인 (숫자 하나나 딕셔너리가 올 수도 있으므로)

def parse_json_array(response):
    """LLM 응답에서 JSON 배열을 꺼낸다. 형식이 틀리면 None"""
    if not isinstance(response, str):
        return None
    text = response.strip()

    if text.startswith('```'):
        text = text.strip('`').removeprefix('json').strip()

    try:
        data = json.loads(text)  # '[0, 2, 5]' -> [0, 2, 5]
    except json.JSONDecodeError:
        print('[파싱 실패] 응답이 JSON 형식이 아닙니다:', response[:100])
        return None

    if not isinstance(data, list):
        print('[파싱 실패] 응답이 리스트가 아닙니다:', response[:100])
        return None
    return data


# ------------------------------------------------------------
# [STEP 4] 판단 기준을 담아 프롬프트 만들기
# ------------------------------------------------------------
# 왜 LLM 에게 맡길까?
#   - 욕설·비방은 표현이 너무 다양해서 "금칙어 목록" 같은 규칙으로는 다 걸러낼 수 없습니다
#   - 그래서 "판단"은 LLM 에게 맡기고, "제거"는 코드가 직접 합니다
#
# 판단 기준(CRITERIA)을 2가지로 준비한 이유
#   - "부적절하다"의 기준은 사람마다, 서비스마다 다릅니다
#   - 기준을 프롬프트에 글자로 적어 주면, 같은 댓글이라도 기준에 따라 LLM 의 판단이 달라집니다
#     'basic'  : 누가 봐도 문제가 되는 표현 위주
#     'strict' : 조롱, 비꼬기, 선동까지 포함
#   - 어떤 기준이 "맞는지"는 LLM 이 아니라 데이터를 쓰는 사람이 정합니다
#
# 왜 "번호만" 받을까?
#   - 댓글 내용을 다시 돌려받으면 LLM 이 글자를 살짝 바꿔 보낼 수 있습니다
#   - 번호만 받으면 원본 댓글은 그대로 두고, 코드가 원본에서 정확히 골라낼 수 있습니다
#
# enumerate(comments) : (0, 댓글1), (1, 댓글2) ... 처럼 번호와 값을 함께 꺼냅니다
# '\n'.join(...)      : 여러 줄을 줄바꿈으로 이어 붙여 문자열 하나로 만듭니다
#
# 프롬프트에 응답 형식을 "예시와 함께" 정확히 적는 것이 핵심입니다
#   [0, 2, 5] 또는 []  => 코드가 json.loads 로 바로 리스트로 바꿀 수 있는 형식

CRITERIA = {
    'basic': '욕설, 혐오, 비방, 선정성, 과도한 비난',
    'strict': (
        '욕설, 혐오, 비방, 선정성, 과도한 비난, 조롱·비꼬기, '
        '다른 투자자를 깎아내리는 표현, 근거 없는 단정이나 매수·매도를 부추기는 선동'
    ),
}

def build_filter_prompt(comments, criteria):
    """댓글에 번호를 붙이고, 기준에 해당하는 댓글의 "번호만" 돌려 달라는 프롬프트를 만든다"""
    numbered = '\n'.join(f'{i}. {c}' for i, c in enumerate(comments))

    return f"""다음 댓글 목록에서 아래 기준에 해당하는 부적절한 댓글의 번호만 골라줘.
기준 : {criteria}
응답은 반드시 [0, 2, 5] 또는 [] 형식의 배열만 보내고, 설명이나 코드블럭은 쓰지 마.

댓글 목록:
{numbered}"""


# ------------------------------------------------------------
# [STEP 5] 응답 검증 후 뒤에서부터 제거하기
# ------------------------------------------------------------
# LLM 응답 검증 : 형식이 맞아도 "값"까지 믿으면 안 됩니다
#   - [3, 3, 25, "a", 2.5] 처럼 중복, 범위 밖 번호, 숫자가 아닌 값이 올 수 있습니다
#   - type(n) is int          : 정수만 (True/False, 2.5, "a" 제외)
#   - 0 <= n < len(comments)  : 실제 있는 댓글 번호만
#   - {...} (집합)             : 중복 제거,  sorted(...) : 작은 번호부터 정렬
#
# 응답을 해석할 수 없을 때 (None)
#   - 아무것도 지우지 않고 그대로 돌려줍니다
#   - "잘못 지우는 것"보다 "못 지우는 것"이 안전하기 때문입니다
#
# 뒤에서부터 지우기 : comments = [A, B, C, D], 지울 번호 [1, 2] (B, C)
#   - 앞에서부터 : pop(1) => [A, C, D] => pop(2) => [A, C]   (B, D 가 지워짐! 틀림)
#   - 뒤에서부터 : pop(2) => [A, B, D] => pop(1) => [A, D]   (B, C 가 지워짐, 정답)
#
# kept = list(comments)
#   - 전달받은 원본 리스트를 직접 지우지 않고, 복사본에서 지웁니다
#   - 원본이 그대로 남아야 다음 STEP 에서 "다른 기준"으로 다시 판단할 수 있습니다

def filter_inappropriate(comments, criteria):
    """LLM 이 고른 번호의 댓글을 제거하고 (남은 댓글, 제거된 댓글)을 돌려준다"""
    if not comments:
        return [], []

    response = run_llm(build_filter_prompt(comments, criteria))
    print('  [LLM 응답]', response)

    numbers = parse_json_array(response)
    if numbers is None:
        raise ValueError('Invalid filter response: expected a JSON array.')

    if any(type(n) is not int or not 0 <= n < len(comments) for n in numbers):
        raise ValueError('Invalid filter response: comment index out of range or not an integer.')

    to_remove = sorted(set(numbers))

    kept = list(comments)  # 원본은 그대로 두고 복사본에서 제거
    removed = []
    for i in reversed(to_remove):
        removed.append(kept.pop(i))
    removed.reverse()  # 원래 순서대로 보기 좋게

    return kept, removed


# ------------------------------------------------------------
# [STEP 6] 같은 댓글을 기준 2가지로 판단하기
# ------------------------------------------------------------
# 같은 댓글을 'basic' 기준과 'strict' 기준으로 각각 한 번씩 판단합니다
#   - for name, criteria in CRITERIA.items() : 딕셔너리의 (키, 값)을 하나씩 꺼냄
#   - 결과는 {'basic': (남은 댓글, 제거된 댓글), 'strict': (...)} 형태
#
# filter_inappropriate 가 원본(comments)을 바꾸지 않기 때문에
# 같은 원본으로 두 번 판단할 수 있습니다 (STEP 5 의 kept = list(comments) 덕분)
#
# LLM 을 2번 호출하므로 실행 시간이 조금 더 걸립니다

def compare_criteria(comments):
    """같은 댓글을 기준별로 판단해 {기준 이름: (남은 댓글, 제거된 댓글)} 로 돌려준다"""
    results = {}
    for name, criteria in CRITERIA.items():
        print(f'\n[부적절 필터] {name} 기준으로 판별 중... (입력 {len(comments)}개)')
        print(f'  기준 : {criteria}')
        results[name] = filter_inappropriate(comments, criteria)
    return results


# ------------------------------------------------------------
# [STEP 7] 비교하고 사람이 기준 고르기
# ------------------------------------------------------------
# 사람이 확인하고 결정하는 단계 (Human-in-the-loop)
#   - LLM 은 "판단"을 하지만, 어떤 기준으로 걸러낼지는 데이터를 쓰는 사람이 "결정"합니다
#   - 두 기준의 결과를 표로 비교한 뒤, selected 에 사용할 기준 이름을 적습니다
#   - "AI 가 판단 => 사람이 확인·결정"이 AI 를 데이터 처리에 쓸 때의 기본 구조입니다
#
# 저장할 때 'criteria'(사용한 기준)와 'removed'(제거된 댓글)도 함께 남깁니다
#   - 나중에 "왜 이 댓글이 빠졌는지" 다른 사람이 확인할 수 있게 하기 위해서입니다
#
# 확인 포인트
#   - 'basic' 과 'strict' 는 각각 몇 개를 제거했나요?
#   - 'strict' 에서만 제거된 댓글을 읽어 보세요. 정말 지워야 할 댓글인가요?
#   - 같은 코드를 한 번 더 실행해 보세요. 매번 같은 댓글이 제거되나요?
#   - selected 를 'basic' 으로 바꾸면 다음 단계(정제)로 넘어가는 댓글 수가 어떻게 달라지나요?

def process_comments(raw, criteria_name='strict'):
    """Apply local cleaning before the LLM while preserving crawler output."""
    if __package__:
        from .clean import prepare_comments
    else:
        from clean import prepare_comments
    from time import perf_counter

    if criteria_name not in CRITERIA:
        raise ValueError('Unknown filter criteria.')
    started = perf_counter()
    prepared, thresholds = prepare_comments(raw['comments'])
    local_seconds = perf_counter() - started
    started = perf_counter()
    kept, removed = filter_inappropriate(prepared, CRITERIA[criteria_name])
    filter_seconds = perf_counter() - started
    return {
        'company': raw['company'],
        'stock_code': raw.get('stock_code'),
        'collected_at': raw['collected_at'],
        'criteria': CRITERIA[criteria_name],
        'raw_comments': list(raw['comments']),
        'prepared_comments': prepared,
        'comments': kept,
        'count': len(kept),
        'removed': removed,
        'iqr_thresholds': thresholds,
        'length_limits': {'min': 5, 'max': 76},
        'timings_seconds': {'local_clean': round(local_seconds, 3),
                            'llm_filter': round(filter_seconds, 3)},
    }


if __name__ == '__main__':
    import argparse
    from time import perf_counter

    parser = argparse.ArgumentParser()
    parser.add_argument('--reuse-raw', action='store_true',
                        help='Development only: reuse saved crawler output.')
    args = parser.parse_args()
    started = perf_counter()
    if args.reuse_raw:
        raw_path = DATA_DIR / 'comments_raw.json'
        if not raw_path.exists():
            raise SystemExit('No saved crawler output. Run without --reuse-raw first.')
        raw = load_json(raw_path)
    else:
        if __package__:
            from .crawling import crawl_comments
        else:
            from crawling import crawl_comments
        company_name = input('Company name: ').strip()
        if not company_name:
            raise SystemExit('Please enter a company name.')
        raw = crawl_comments(company_name, limit=20)
        save_json(raw, DATA_DIR / 'comments_raw.json')
    crawl_seconds = perf_counter() - started

    result = process_comments(raw)
    result['timings_seconds']['crawl_or_load'] = round(crawl_seconds, 3)
    save_json(result, DATA_DIR / 'comments_filtered.json')
    # Already cleaned before the LLM, so the next augmentation can run directly.
    save_json(result, DATA_DIR / 'comments_clean.json')
    print(f"[Counts] raw={len(raw['comments'])}, prepared={len(result['prepared_comments'])}, kept={result['count']}")
    print('[Seconds]', result['timings_seconds'])
