"""SPOT CHECK: 지역 정보 중심의 대화형 상권 대시보드."""
import base64
import copy
import json
from html import escape
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
from src.services.spot_catalog import BASE_DIR, load_spots, data_paths, get_spot
from src.services.pilot_report import load_spot_data
from src.services.chat_controller import answer_question
from src.services.pdf_evidence import report_data
from src.services.region_analytics import distribution_rows, pdf_visuals, public_report
from src.services.naver_map import render_map
from src.ui.analytics import bar_chart
from src.ui.styles import apply_styles, brand, page_title, apply_region_styles
from src.ui.chat_layout import apply_chat_layout
from src.ui.assistant_message import assistant_message, apply_answer_styles
from src.services.region_search import search_regions

st.set_page_config(page_title='SPOT CHECK · 데이터로 읽는 상권', page_icon=':material/location_on:', layout='wide', initial_sidebar_state='collapsed')
apply_styles()
spots = load_spots()
st.session_state.setdefault('ui_stage', 'home')
st.session_state.setdefault('active_spot', 'daegu_downtown')
states = st.session_state.setdefault('spot_sessions', {})
archives = st.session_state.setdefault('conversation_archive', [])
valid_ids = {s['id'] for s in spots}
for obsolete in set(states) - valid_ids:
    del states[obsolete]
if st.session_state['active_spot'] not in valid_ids:
    st.session_state['active_spot'] = spots[0]['id']
if st.session_state['ui_stage'] == 'location':
    st.session_state['ui_stage'] = 'chat'
# 이전 후보·주소 응답이 새 화면에 다시 나타나지 않도록 세션을 전환한다.
if st.session_state.get('dashboard_version') != 15:
    for saved in states.values():
        saved['messages'], saved['reports'], saved['request'] = [], [], {}
        saved.pop('location', None)
        saved.pop('title', None)
        saved.pop('updated_at', None)
    archives.clear()
    st.session_state['dashboard_version'] = 15
spot_id = st.session_state['active_spot']
spot = next(s for s in spots if s['id'] == spot_id)
state = states.setdefault(spot_id, {'messages': [], 'request': {}, 'reports': []})

@st.cache_data(ttl=300, max_entries=8)
def cached_data(region_id, csv_mtime, metadata_mtime):
    return load_spot_data(region_id)

@st.cache_data(max_entries=2)
def hero_image():
    return base64.b64encode((BASE_DIR / 'assets/hero_city.png').read_bytes()).decode('ascii')

def navigate(stage):
    st.session_state['ui_stage'] = stage
    selection_screen.empty()
    st.rerun()

def choose_spot(region_id):
    st.session_state['active_spot'] = region_id
    navigate('chat')

def source_content():
    st.markdown('**점포 현황** · 소상공인시장진흥공단 상가정보 API 수집본')
    st.caption('지역별 수집 범위 내 등록 정보입니다. 주소를 입력하면 해당 주소의 등록 좌표에서 직선 거리로 계산합니다. 주소가 없으면 지역 기준점을 사용하며 도심 통합상권 전체는 세 수집 원의 합집합입니다.')
    st.markdown('**지역 통계·특성** · 사용자 제공 상권보고서.pdf (개정판)')
    st.caption('PDF 지정 경계의 통계입니다. API 집계와 공간·기준시점이 다릅니다. 임대료·업종별 매출은 미확인입니다.')


def render_answer(message, key):
    if message.get('role') == 'assistant':
        assistant_message(message, key)
    else:
        st.markdown(message['content'])
        if message.get('time'):
            st.caption(message['time'])

with st.container(key='global-header'):
    left, right = st.columns([1.2, 1], vertical_alignment='center')
    with left:
        brand()
    with right:
        links = st.columns(3)
        with links[0].popover('서비스 소개', width='stretch'):
            st.write('대구 다섯 지역의 상가 정보와 보고서를 함께 살펴보는 상권 분석 서비스입니다.')
        with links[1].popover('이용 가이드', width='stretch'):
            st.write('지역을 고르고 업종이나 통계를 질문하세요. 주소와 반경을 함께 입력하면 해당 주소 기준으로 계산합니다. 특정 점포·주소의 추천이나 순위는 제공하지 않습니다.')
        with links[2].popover('데이터 출처', width='stretch'):
            source_content()

selection_screen = st.empty()
stage = st.session_state['ui_stage']
# Stage-scoped visibility prevents stale blocks from appearing during a rerun.
hidden_screen = '.st-key-region-page,.st-key-hero,.st-key-home-features' if stage == 'chat' else '.st-key-workspace'
st.html(f'<style>{hidden_screen}{{display:none!important}}</style>')
if stage == 'home':
    with selection_screen.container():
        st.html('<style>.st-key-hero{background-image:linear-gradient(90deg,rgba(255,255,255,.3),transparent 65%),url("data:image/png;base64,' + hero_image() + '");}</style>')
        with st.container(key='hero'):
            st.html('<div class="eyebrow">DATA FOR YOUR NEXT CHAPTER</div>')
            st.html('<h1>좋은 시작은,<br>상권을 아는 것부터.</h1>')
            st.markdown('대구의 상권을 데이터로 읽어보세요.\n\n궁금한 업종부터 지역의 특성까지,\n\n**SPOT CHECK가 함께 살펴봅니다.**')
            if st.button('분석 시작하기', icon=':material/arrow_forward:', type='primary', key='start'):
                navigate('region')
            st.caption('대구 도심 통합상권 · 수성못 · 삼덕동 · 동대구역 · 칠곡3지구')
        with st.container(horizontal=True, key='home-features'):
            for number, title, text in [('01', '지역을 고르세요', '대구의 다섯 상권에서 관심 지역을 선택하세요.'), ('02', '편하게 질문하세요', '궁금한 업종과 통계를 대화로 이야기해 주세요.'), ('03', '숫자를 한눈에', '확인된 통계와 출처를 그래프로 살펴보세요.')]:
                st.html(f'<div class="feature"><small>{number}</small><h3>{title}</h3><p>{text}</p></div>')
        st.stop()

try:
    csv_path, meta_path = data_paths(spot_id)
    stores, metadata = cached_data(spot_id, csv_path.stat().st_mtime_ns, meta_path.stat().st_mtime_ns)
except (ValueError, OSError):
    stores, metadata = None, {}

if stage == 'region':
    with selection_screen.container():
        apply_region_styles()
        with st.container(key='region-page'):
            st.html('<div class="region-title"><small>SPOT CHECK</small><h1>어떤 지역이 궁금하신가요?</h1><p>지역을 선택하면 바로 채팅으로 이어집니다.</p></div>')
            keyword = st.text_input('지역 검색', placeholder='도심 통합상권 / 수성못 / 삼덕동 / 동대구역 / 칠곡3지구 등 지역을 검색해보세요.', icon=':material/search:', key='region-search')
            matches = search_regions(keyword, spots)
            filtered = [match['spot'] for match in matches]
            with st.container(key='region-grid'):
                for item in filtered:
                    with st.container(key='spot-card-' + item['id'], border=True):
                        if st.button(item['name'], key='select_' + item['id'], width='stretch'):
                            match=next(match for match in matches if match['spot']['id']==item['id'])
                            if match['categories']:
                                names=' · '.join(category['name'] for category in match['categories'])
                                st.session_state['pending_search_question']=f'{item["name"]}에서 {names} 업종을 분석해줘'
                            choose_spot(item['id'])
                        components = '<div class="region-components">동성로 · 대구역 · 반월당</div>' if item.get('components') else ''
                        match=next(match for match in matches if match['spot']['id']==item['id'])
                        if match['count'] is not None:
                            components=f'<div class="region-components">조건 일치 업종 · API 수집본 {match["count"]:,}곳</div>'
                        pin = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2.5"/></svg>'
                        st.html(f'<div class="region-card-content"><div class="region-card-top"><span class="region-pin" aria-hidden="true">{pin}</span><div class="region-card-label"><small>DAEGU · {escape(item["district"])}</small><strong>{escape(item["name"])}</strong></div><span class="region-arrow" aria-hidden="true">→</span></div>{components}<div class="region-tags"><span>상가 현황</span><span>지역 특성</span><span>교통</span></div></div>')
            if not filtered:
                st.info('현재 지원하는 다섯 지역에서 선택해 주세요.')
            if st.button('처음으로', icon=':material/arrow_back:', key='region-home'):
                navigate('home')
        st.stop()

# Clear selection cards before emitting any chat elements.
selection_screen.empty()

workspace = st.container(key='workspace')
with workspace.container(key='workspace-controls'):
    workspace_view = st.segmented_control('화면 보기', ['채팅', '분석', '대화 목록'], default='채팅',
                                          key='workspace_view', label_visibility='collapsed', required=True)
apply_chat_layout(workspace_view)
apply_answer_styles()
grid = workspace.container(key='workspace-grid')
history, conversation, details = grid.columns([16, 54, 30], gap='medium')
with history, st.container(key='conversation-nav'):
    with st.container(key='history-header'):
        if st.button('새 대화하기', icon=':material/add:', type='primary', width='stretch', key='new_chat'):
            if state['messages']:
                archives.insert(0, {'spot_id': spot_id, 'state': copy.deepcopy(state)})
                del archives[12:]
            states[spot_id] = {'messages': [], 'request': {}, 'reports': []}
            navigate('region')
        st.caption('최근 대화')
    with st.container(height=200, border=False, key='history-list'):
        threads = [(s, states.get(s['id'], {})) for s in spots if states.get(s['id'], {}).get('messages')]
        if not threads and not archives:
            st.caption('대화를 시작하면 여기에 표시돼요.')
        for item, saved in threads:
            if st.button(saved.get('title', item['name'] + ' 상권 살펴보기'), icon=':material/chat_bubble_outline:', key='thread_' + item['id'], width='stretch', type='primary' if item['id'] == spot_id else 'secondary'):
                choose_spot(item['id'])
            st.caption(saved.get('updated_at', '현재 세션'))
        for index, archived in enumerate(archives[:6]):
            if st.button(archived['state'].get('title', '이전 대화'), key=f'archive_{index}', width='stretch'):
                current = copy.deepcopy(states.get(archived['spot_id'], {}))
                states[archived['spot_id']] = copy.deepcopy(archived['state'])
                if current.get('messages'):
                    archives[index] = {'spot_id': archived['spot_id'], 'state': current}
                else:
                    archives.pop(index)
                choose_spot(archived['spot_id'])
    with st.container(key='history-footer'):
        st.html('<div class="nav-note"><small>데이터로 찾는, 더 나은 시작</small><strong>당신의 다음 시작을<br>SPOT CHECK와 함께.</strong><span>확인된 숫자와 근거로<br>지역을 이해하세요.</span></div>')

with conversation, st.container(key='conversation-panel', border=True):
    chat_header = st.container(key='chat-heading')
    heading, selector = chat_header.columns([1.2, 1])
    with heading:
        st.markdown(f'**{spot["name"]} 상권 이야기**')
        st.caption(state.get('title', '지역을 이해하는 대화'))
    with selector:
        def change_region():
            st.session_state['active_spot'] = st.session_state['chat_spot_selector']
        st.selectbox('분석 지역', [s['id'] for s in spots], index=[s['id'] for s in spots].index(spot_id), format_func=lambda value: next(s['name'] for s in spots if s['id'] == value), key='chat_spot_selector', on_change=change_region, label_visibility='collapsed')
    feed = st.container(height=565, border=False, key='chat-feed', autoscroll=True)
    with feed:
        with st.chat_message('assistant', avatar=':material/smart_toy:'):
            st.markdown('안녕하세요! **SPOT CHECK**입니다.')
            st.write(f'{spot["name"]}의 상가 데이터와 보고서를 함께 살펴볼게요. 어떤 업종을 생각하고 계신가요?')
            st.caption('예: 카페를 하고 싶어요 · 유동인구는 몇 명이야? · 지역 특징이 궁금해요')
        for index, message in enumerate(state['messages']):
            with st.chat_message(message['role'], avatar=':material/smart_toy:' if message['role'] == 'assistant' else ':material/person:'):
                render_answer(message, f'{spot_id}-message-{index}')
    composer = st.container(key='chat-composer')
    prompt = None
    with composer.container(horizontal=True, wrap=False, key='quick-prompts'):
        for industry in ['카페', '여성 의류', '미용실', '음식점', '편의점', '네일숍']:
            if st.button(industry, key='quick_' + industry):
                prompt = f'{spot["name"]}에서 {industry}를 하고 싶어요'
        if st.button('유동인구', key='quick_population'):
            prompt = f'{spot["name"]}의 유동인구는 몇 명이야?'
    question = composer.chat_input('궁금한 내용을 자유롭게 질문해 주세요.', max_chars=3000) or prompt or st.session_state.pop('pending_search_question','')
    if question:
        now = datetime.now(ZoneInfo('Asia/Seoul'))
        state['messages'].append({'role': 'user', 'content': question, 'time': now.strftime('%H:%M')})
        with feed.chat_message('user', avatar=':material/person:'):
            render_answer(state['messages'][-1], f'{spot_id}-message-{len(state["messages"])-1}')
        with feed.chat_message('assistant', avatar=':material/smart_toy:'):
            loading = st.empty()
            with loading.status('데이터 검색 중', expanded=False) as answer_status:
                try:
                    answer, report = answer_question(spot_id, question, state, stores, metadata, 1000,
                        progress=lambda label: answer_status.update(label=label))
                    report = public_report(report)
                    if report:
                        report['created_at'] = now.strftime('%Y.%m.%d %H:%M')
                        state['reports'].append(report)
                    visual = report or pdf_visuals(spot_id, question, answer)
                    answer_status.update(label='분석 완료',state='complete')
                except Exception:
                    answer = '자료에서 답을 확인하지 못했습니다. 지역·업종·반경과 연결 설정을 확인한 뒤 다시 질문해 주세요. 알 수 없는 내용은 추측하지 않습니다.'
                    visual = None
                    answer_status.update(label='답변을 확인할 수 없습니다. 잠시 후 다시 질문해 주세요.',state='error')
            rag=state.get('rag_last',{})
            state['messages'].append({'role': 'assistant', 'content': answer, 'visual': visual, 'time': now.strftime('%H:%M'),
                                      'citations':rag.get('citations',[]),'rag_status':rag.get('statuses',[])})
            loading.empty()
            render_answer(state['messages'][-1], f'{spot_id}-message-{len(state["messages"])-1}')
        if 'title' not in state:
            names = ', '.join(c['name'] for c in state.get('request', {}).get('categories', []))
            state['title'] = spot['name'] + ' · ' + (names + ' 현황' if names else '지역 통계')
        state['updated_at'] = now.strftime('%Y.%m.%d %H:%M')
        st.rerun()
    composer.caption('주소와 반경을 입력하면 해당 주소 기준으로 계산합니다. 특정 점포·주소의 추천이나 입지 순위는 제공하지 않습니다.')

with details, st.container(key='insights-panel', border=True):
    latest = next((r for r in reversed(state['reports']) if r.get('parent_id', r.get('region_id')) == spot_id), None)
    st.markdown(f'**:material/map: {spot["name"]} 지역 지도**')
    map_spot = get_spot(latest['region_id']) if latest else spot
    if latest and latest.get('scope_latitude') is not None:
        map_spot = dict(map_spot, latitude=latest['scope_latitude'], longitude=latest['scope_longitude'])
    map_radius = latest['radius_m'] if latest else 1000
    union_scope = latest.get('scope_kind') == 'union' if latest else bool(spot.get('components'))
    points = [{'lat':c['latitude'],'lon':c['longitude'],'label':c['name']} for c in spot.get('components', [])] if union_scope else []
    if map_spot['latitude'] is not None:
        render_map(map_spot['latitude'], map_spot['longitude'], markers=points, radius=map_radius, show_markers=False, height=265)
    scope_label = latest['scope_description'] if latest else spot.get('scope_note', f"지역 수집 기준점 반경 {map_radius:g}m")
    st.caption(scope_label + ' · PDF 상권 경계와 다릅니다.')
    st.markdown('**:material/analytics: 주요 통계**')
    try:
        pdf = report_data(spot['name'])
    except (OSError, ValueError, IndexError):
        pdf = None
    a, b = st.columns(2)
    with a:
        st.metric('API 집계 범위 상가', f"{latest['total_stores']:,}곳" if latest else f'{len(stores):,}곳' if stores is not None else '미수집')
        st.caption(', '.join(metadata.get('source_date_range', [metadata.get('collected_at_utc', '')[:10]])) + ' 원본 수집')
        footfall = pdf['metrics'].get('유동인구') if pdf else None
        st.metric('PDF 일평균 유동인구', f"{footfall:,}명" if footfall is not None else '세부 구역별' if pdf else '확인 불가')
        st.caption('PDF 지정 경계 · 2026.07 기준')
    with b:
        st.metric('선택 업종 점포', f"{latest['competitor_count']:,}곳" if latest else '업종 선택 전')
        st.caption('API 수집 범위 기준')
        st.metric('임대료', '자료 없음')
        st.caption('추정값을 표시하지 않습니다.')
    if pdf:
        st.caption('PDF 출처: 상권보고서.pdf 2쪽 표, 1·10쪽 기준연월. 도심 세 구역의 수치는 합산하지 않습니다. 원천 갱신 기준이며 조회 기간은 별도 확인이 필요합니다.')
    st.divider()
    st.markdown('**:material/bar_chart: 지역 업종 구성**')
    if stores is not None:
        distribution = latest['all_distribution'] if latest else {str(k): int(v) for k, v in stores.indsLclsNm.value_counts().items()}
        bar_chart(distribution_rows(distribution), '업종', '점포 수', f'distribution-{spot_id}', 190)
        st.caption(f"출처: 상가정보 API · {', '.join(metadata.get('source_date_range', [metadata.get('collected_at_utc', '')[:10]]))} · 위 집계 범위의 업종 구성")
    if latest:
        st.markdown('**선택 업종의 구성**')
        bar_chart(distribution_rows(latest['distribution']), '업종', '점포 수', f'selected-distribution-{spot_id}', 140)
        st.caption('API의 실제 소분류 기준입니다. 프랜차이즈·개인 매장 여부는 이 자료에서 확인되지 않습니다.')
        st.download_button('지역 통계 다운로드', json.dumps(latest, ensure_ascii=False, indent=2), file_name=f'{spot_id}_regional_statistics.json', mime='application/json', key='download_stats')
    else:
        st.info('업종을 말씀해 주시면 점포 수와 비중을 함께 보여드려요.')
