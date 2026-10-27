"""현재 지역 선택 화면의 자연어 조건 검색. 개별 점포나 입지 순위를 추천하지 않는다."""
import re
from functools import lru_cache

from src.services.spot_catalog import load_spots, data_paths
from src.services.pilot_report import load_spot_data, CATEGORY_FIELDS


@lru_cache(maxsize=16)
def _data(region_id,modified):
    return load_spot_data(region_id)[0]


def search_regions(query,spots=None):
    from src.services.chat_controller import local_request
    spots=spots or load_spots()
    compact=re.sub(r'\s+','',query)
    if not compact:
        return [{'spot':s,'categories':[],'count':None} for s in spots]
    if any(city in compact for city in ('서울','부산','인천','광주','대전','울산','세종','제주','경산')):
        return []
    explicit=[s for s in spots if any(name.replace(' ','') in compact for name in [s['name'],*[c['name'] for c in s.get('components',[])]])]
    if '도심통합상권' in compact:
        explicit=[s for s in spots if s['id']=='daegu_downtown']
    candidates=explicit or [s for s in spots if compact in s['name'].replace(' ','') or compact in s['district']]
    # 업종 조건이 있으면 지역을 명시하지 않은 경우에도 다섯 지역의 실제 분류를 검색.
    districts=[s for s in spots if s['district'] in compact]
    pool=explicit or districts or spots
    frames={}
    fallback=None
    for spot in spots:
        path,_=data_paths(spot['id'])
        if path.exists():
            frames[spot['id']]=_data(spot['id'],path.stat().st_mtime_ns)
            fallback=fallback or local_request(query,frames[spot['id']],{})
    matches=[]
    industry=False
    threshold=re.search(r'(\d+)\s*(?:곳|개|점)?\s*(이상|초과|이하|미만)',query)
    for spot in pool:
        if spot['id'] not in frames:
            continue
        frame=frames[spot['id']]
        request=local_request(query,frame,{}) or fallback
        if request:
            industry=True
            mask=frame.bizesId.isna() # 실제 유효 행은 False에서 시작
            for category in request['categories']:
                mask |= frame[CATEGORY_FIELDS[category['level']]]==category['name']
            count=int(mask.sum())
            if threshold:
                value,operator=int(threshold[1]),threshold[2]
                if not {'이상':count>=value,'초과':count>value,'이하':count<=value,'미만':count<value}[operator]:
                    continue
            matches.append({'spot':spot,'categories':request['categories'],'count':count})
    if industry:
        if any(word in compact for word in ('많은','많이','최다')):
            matches.sort(key=lambda item:item['count'],reverse=True)
        return matches
    return [{'spot':s,'categories':[],'count':None} for s in candidates]
