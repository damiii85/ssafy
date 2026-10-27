"""특정 위치 추천 없이 지역 단위 업종·문서 정보를 답하는 채팅 처리."""

import re

from src.services import pilot_report as pilot
from src.services.distance_scope import requested_radius, scoped_stores


def _briefing(spot_id, question, state, stores, metadata, categories, location=None):
    from src.services.industry_briefing import industry_briefing
    try:
        frame, meta = scoped_stores(spot_id, stores, metadata, question, state, location)
    except ValueError as error:
        return str(error), None
    return industry_briefing(spot_id, frame, meta, categories)


def local_request(question, stores, previous):
    """Resolve explicit catalogue labels without making basic counts depend on an API."""
    compact = re.sub(r"\s+", "", question)
    catalogue = pilot.category_catalog(stores)
    aliases = {"여성옷가게": "여성 의류 소매업", "여성의류": "여성 의류 소매업",
               "남성의류": "남성 의류 소매업", "네일샵": "네일숍",
               "커피숍": "카페", "커피전문점": "카페", "커피집": "카페", "카패": "카페",
               "헤어샵": "미용실", "헤어숍": "미용실", "네일아트": "네일숍",
               "스터디카페": "독서실/스터디 카페"}
    names = [name for name in catalogue["small"] if re.sub(r"\s+", "", name) in compact]
    names += [name for alias, name in aliases.items() if alias in compact and name in catalogue["small"]]
    # A study cafe is a separate official category, rather than a regular cafe.
    if "독서실/스터디 카페" in names:
        names = [name for name in names if name != "카페"]
    categories = [{"level": "small", "name": name} for name in dict.fromkeys(names)]
    if not categories and "음식점" in compact and "음식" in catalogue["large"]:
        categories = [{"level": "large", "name": "음식"}]
    if not categories:
        categories = [{"level": level, "name": name}
                      for level in ("middle", "large") for name in catalogue[level]
                      if len(name) >= 2 and re.sub(r"\s+", "", name) in compact]
    if not categories and any(term in compact for term in ("옷가게", "의류매장", "의류")):
        categories = [{"level": "small", "name": name} for name in catalogue['small']
                      if "의류" in name and name.endswith("소매업")]
    if not categories:
        return None
    return {"address": "", "intent": "spot_overview", "categories": categories, "clarification": ""}


def _structured_answer(spot_id, question, state, stores, metadata, radius, location=None):
    previous = dict(state.get("request", {}))
    previous['address'] = ''
    previous['intent'] = 'spot_overview'
    request = local_request(question, stores, previous)
    if request is None:
        try:
            request = pilot.parse_request(question, stores, previous)
        except ValueError:
            raise
        except Exception:
            return "질문에서 분석할 업종이나 확인할 정보를 특정하지 못해 답을 알 수 없습니다. 카페·여성 의류·미용실처럼 업종을 말씀해 주시거나, 유동인구·교통·지역 특징을 질문해 주세요.", None
    request = dict(request, address='', intent='spot_overview')
    state["request"] = request
    if not request["categories"]:
        return request.get("clarification") or "어떤 업종을 생각하고 계신가요? 업종을 조금 더 구체적으로 알려주세요.", None
    text, report = _briefing(spot_id, question, state, stores, metadata, request['categories'], location)
    if any(term in question for term in ('어디', '추천', '주소', '후보')):
        text = '특정 주소나 후보 순위 대신, 선택 지역 전체의 업종 현황을 안내해 드릴게요.\n\n' + text
    return text, report


def answer_question(spot_id, question, state, stores, metadata, radius, location=None, progress=None):
    from src.rag.pipeline import ACTIVE, run
    if ACTIVE.get():
        return _legacy_answer_question(spot_id,question,state,stores,metadata,radius,location)
    state.pop('rag_last',None)
    return run(spot_id,question,state,stores,metadata,radius,location,_legacy_answer_question,progress)


def _legacy_answer_question(spot_id, question, state, stores, metadata, radius, location=None):
    """입력한 주소를 먼저 해석하고 후속 질문에서도 그 기준점을 유지한다."""
    from src.services.address_scope import resolve_address, ROAD, LOT
    compact=re.sub(r'\s+','',question)
    if any(word in compact for word in ('시스템프롬프트','프롬프트전문','API키값','환경변수값')):
        return '내부 프롬프트나 비밀 설정값은 제공하지 않습니다. 상권·업종·자료에 관해 질문해 주세요.',None
    if re.search(r'(?<![가-힣])(?:서울|부산|인천|광주|대전|울산|세종|제주|경산)(?:광역시|특별시|시)?(?=$|\s|에서|의|지역|에)',question) and not (ROAD.search(question) or LOT.search(question)):
        return '현재 지원하는 대구 다섯 상권의 자료만 확인할 수 있습니다. 지원하지 않는 지역의 수치는 알 수 없습니다.',None
    reset = any(term in question for term in ('전체 범위', '전체범위', '지역 전체', '통합상권 전체', '지역 기준점', '상권 기준점'))
    if reset:
        state.pop('address_location', None)
        state.pop('distance_scope', None)
    try:
        resolved = resolve_address(question, spot_id, stores)
    except ValueError as error:
        # 잘못된 새 주소 뒤의 질문도 이전 주소로 조용히 계산하지 않는다.
        state['address_location'] = {'unresolved': True}
        return str(error), None
    if resolved:
        state['address_location'] = resolved
        location = resolved
    elif location is None:
        location = state.get('address_location')
    if location and location.get('unresolved'):
        return '앞서 입력한 주소의 좌표를 확인하지 못했습니다. 정확한 주소를 다시 입력하거나 상권 기준점을 지정해 주세요.', None
    original_spot = spot_id
    if location:
        spot_id = location.get('region_id', spot_id)
        if spot_id != original_spot:
            try:
                stores, metadata = pilot.load_spot_data(spot_id)
            except (ValueError, OSError):
                return '해당 주소 지역의 API 수집본을 불러올 수 없어 계산할 수 없습니다.', None
        try:
            explicit_radius = requested_radius(question)
        except ValueError as error:
            return str(error), None
        # 주소만 바꾸면 직전 반경을 유지하고, 첫 주소 분석은 기존 기본 반경을 사용.
        if explicit_radius is None and (resolved or not state.get('distance_scope')):
            effective_radius = state.get('distance_scope', {}).get('radius_m', min(radius, 200))
            question += f' {effective_radius:g}m 이내'
        else:
            effective_radius = explicit_radius or state['distance_scope']['radius_m']
        state['distance_scope'] = {'spot_id': spot_id, 'radius_m': effective_radius}
    text, report = _answer_question(spot_id, question, state, stores, metadata, radius, location)
    if report and location:
        report['parent_id'] = original_spot
    return text, report


def _answer_question(spot_id, question, state, stores, metadata, radius, location=None):
    from src.services.pdf_evidence import pdf_answer
    from src.services.pdf_evidence import question_regions, spot_for_region

    # 명시된 다른 지역의 질문에는 그 지역 수집본을 사용한다.
    explicit_regions = question_regions('', question)
    regions = explicit_regions or question_regions(spot_id, question)
    if len(regions) == 1 and not location:
        requested_spot = (spot_for_region(regions[0]) if explicit_regions else state.get('last_region', spot_id)) or spot_id
        if requested_spot != spot_id:
            try:
                other_stores, other_meta = pilot.load_spot_data(requested_spot)
            except ValueError:
                other_stores, other_meta = None, {}
            context = state.setdefault('region_contexts', {}).setdefault(requested_spot, {'request': dict(state.get('request', {}))})
            result = answer_question(requested_spot, question, context, other_stores, other_meta, radius)
            state['last_region'] = requested_spot
            state['request'] = dict(context.get('request', {}))
            return result
        if explicit_regions:
            state['last_region'] = spot_id

    if stores is None or stores.empty:
        return pdf_answer(spot_id, question) + "\n\n선택 지역의 API 상가 수집본이 없어 반경 내 점포 수·경쟁 점포·후보지는 알 수 없습니다.", None
    try:
        distance = requested_radius(question)
    except ValueError as error:
        return str(error), None
    document_question = any(word in question for word in (
        "PDF", "pdf", "보고서", "교통", "지하철", "버스", "랜드마크", "관광", "특징",
        "유동인구", "매출", "소득", "소비", "주거", "직장인구", "임대료", "성공", "수익",
        "지역 특징", "얼마", "몇명", "몇 명", "업소", "세대", "유동인", "거주인구"))
    previous = dict(state.get("request", {}))
    previous['address'] = ''
    previous['intent'] = 'spot_overview'
    # 업종이 명시된 혼합 질문은 기존 집계를 보존하고 PDF 근거를 덧붙인다.
    request = local_request(question, stores, previous)
    if distance is not None:
        if any(term in question for term in ('유동인', '매출', '소득', '소비', '주거인구', '직장인구')):
            return f'요청한 {distance:g}m 범위의 해당 통계는 알 수 없습니다. PDF 통계는 지정 상권 경계의 값이므로 거리 비율로 나누거나 해당 반경 값으로 대체하지 않습니다.', None
        if request is None and previous.get('categories'):
            request = dict(previous, address='', intent='spot_overview')
        if request is None and any(term in question for term in ('상가', '점포', '업소')) and not any(term in question for term in ('유사', '동종')):
            request = {'address': '', 'intent': 'spot_overview', 'categories': [{'level':'large','name':name} for name in pilot.category_catalog(stores)['large']]}
        if request is None:
            if location:
                return '어떤 업종의 유사·동종 점포를 계산할까요? 예: 카페. 기준은 입력한 주소의 등록 좌표이며 지정한 반경을 유지합니다.', None
            return '어떤 업종의 유사·동종 점포를 계산할까요? 예: 카페 100m 이내. 기준은 선택 지역의 공개 수집 기준점이며 현재 사용자 위치가 아닙니다.', None
        state['request'] = request
        return _briefing(spot_id, question, state, stores, metadata, request['categories'], location)
    if len(regions) > 1 and request and not document_question:
        from src.services.industry_briefing import industry_briefing
        sections = []
        for region in regions:
            region_id = spot_for_region(region)
            try:
                frame, meta = pilot.load_spot_data(region_id)
                text, _ = _briefing(region_id, question, {}, frame, meta, request['categories'])
                sections.append(text)
            except ValueError:
                sections.append(f"{region}의 해당 업종 수집본은 확인할 수 없습니다.")
        return '\n\n'.join(sections) + '\n\n지역별 반경은 서로 겹칠 수 있어 점포 수를 합산하거나 이 수치만으로 입지 순위를 정하지 않습니다.', None
    # 숫자·교통 질문을 이전 업종 분석으로 덮지 않는다.
    if document_question:
        if request and any(term in re.sub(r'\s+', '', question) for term in ('하고싶', '창업', '열고싶')):
            api_text, report = _structured_answer(spot_id, question, state, stores, metadata, radius, location)
            return api_text + '\n\n' + pdf_answer(spot_id, question), report
        evidence = pdf_answer(spot_id, question)
        if state.get('distance_scope'):
            evidence = f"앞서 지정한 {state['distance_scope']['radius_m']:g}m 범위의 PDF 통계는 없습니다. 아래는 별도 상권 경계의 보고서 자료입니다.\n\n" + evidence
        return evidence, None
    if request is None and previous.get('categories') and any(term in question for term in ('추천', '어디', '후보', '위치', '경쟁', '현황', '유사', '동종', '몇 개', '몇개', '전체 범위', '전체범위')):
        request = dict(previous)
        request['intent'] = 'spot_overview'
        request['address'] = ''
        state['request'] = request
        # 분류가 명시되지 않은 후속 질문에는 검증된 이전 업종만 사용.
        return _briefing(spot_id, question, state, stores, metadata, request['categories'], location)
    if request is not None:
        return _structured_answer(spot_id, question, state, stores, metadata, radius, location)
    if any(term in question for term in ('특징', '상권', 'PDF', 'pdf', '보고서', '시설', '소개', '비교')):
        return pdf_answer(spot_id, question), None
    return _structured_answer(spot_id, question, state, stores, metadata, radius, location)
