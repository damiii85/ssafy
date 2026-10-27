"""사용자 주소를 API 수집본의 등록 좌표와 연결한다. 비슷한 주소를 추측하지 않는다."""
import re

from src.services.pilot_report import coordinates_for_address, load_spot_data
from src.services.spot_catalog import load_spots

ROAD = re.compile(r'([가-힣A-Za-z0-9·.]+(?:대로|로|길)(?:\s*\d+(?:번)?길)?)\s*(\d+(?:-\d+)?)(?![\d-]|길|번길|\s*(?:m\b|미터|km\b))', re.I)
LOT = re.compile(r'([가-힣0-9]+[동가])\s+(\d+(?:-\d+)?)(?![\d]|\s*(?:m\b|미터|km\b))', re.I)


def resolve_address(question, spot_id, stores):
    """주소가 없으면 None, 확인 불가/여러 주소면 오류, 한 주소면 좌표 반환."""
    matches = list(ROAD.finditer(question)) or list(LOT.finditer(question))
    if not matches:
        without_radius = re.sub(r'\d+(?:\.\d+)?\s*(?:km|m\b|킬로미터|미터)', '', question, flags=re.I)
        if re.search(r'(?:주소[는:가]?\s*|[가-힣]+(?:대로|로|길)\s*)\d', without_radius):
            raise ValueError('주소의 도로명과 건물번호를 확인해 주세요. 예: 대구광역시 중구 동성로 25. 확인되지 않은 주소를 상권 기준점으로 대체하지 않습니다.')
        return None
    tokens = {re.sub(r'\s+', '', m.group()) for m in matches}
    if len(tokens) != 1:
        raise ValueError('한 번에 주소 한 개와 분석 반경을 말씀해 주세요.')
    token = tokens.pop()
    # 주소에 명시된 시·구까지 일치해야 한다. 같은 도로명의 다른 도시를 선택하지 않는다.
    if re.search(r'서울|부산|인천|광주|대전|울산|세종|경기도|경상|전라|충청|강원|제주|경산시', question):
        raise ValueError('해당 주소는 현재 대구 다섯 상권의 API 수집 범위에서 확인할 수 없습니다.')
    districts = re.findall(r'([가-힣]+구)(?=\s)', question)
    matches_by_address = {}
    frames = [(spot_id, stores)]
    for spot in load_spots():
        if spot['id'] != spot_id:
            try:
                frame, _ = load_spot_data(spot['id'])
                frames.append((spot['id'], frame))
            except (ValueError, OSError):
                continue
    for region_id, frame in frames:
        if frame is None:
            continue
        for column in ('rdnmAdr', 'lnoAdr'):
            if column not in frame:
                continue
            for address in frame[column].dropna().unique():
                if re.sub(r'\s+', '', address).endswith(token) and all(d in address for d in districts):
                    rows = frame.loc[frame[column] == address].copy()
                    rows['rdnmAdr'] = address
                    matches_by_address.setdefault(address, (region_id, rows))
    if len(matches_by_address) != 1:
        reason = '같은 도로명·건물번호의 주소가 여러 개입니다. 시·구를 포함해 입력해 주세요.' if matches_by_address else '해당 주소의 등록 좌표를 API 수집본에서 확인할 수 없어 계산할 수 없습니다. 도로명·건물번호 또는 지번을 확인해 주세요.'
        raise ValueError(reason + ' 상권 기준점으로 임의 대체하지 않습니다.')
    address, (region_id, rows) = next(iter(matches_by_address.items()))
    lat, lon = coordinates_for_address(address, rows)
    return {'latitude': lat, 'longitude': lon, 'address': address, 'region_id': region_id,
            'source': '상가정보 API 수집본의 주소별 등록 좌표'}
